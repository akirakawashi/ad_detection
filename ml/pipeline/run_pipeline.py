#!/usr/bin/env python3
"""CLI entry point for the local ad visibility pipeline."""

from __future__ import annotations

import argparse
import os
import tempfile
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib"))

from scripts.aggregation import aggregate_tracks
from scripts.classification import classify_detections, load_classifier
from scripts.config import PipelineConfig, default_project_root, resolve_project_path
from scripts.crops import copy_crops_by_status, save_detection_crops
from scripts.detection import load_detector, run_detection
from scripts.io import iter_frames, load_frames, load_metadata
from scripts.quality import evaluate_crop_quality
from scripts.reports import write_pipeline_outputs
from scripts.schemas import DetectionRecord, FrameRecord, InputMetadata
from scripts.tracking import assign_track_ids
from scripts.visualization import write_annotated_media


def parse_args() -> argparse.Namespace:
    project_root = default_project_root()
    parser = argparse.ArgumentParser(description="Run local outdoor ad visibility pipeline.")
    parser.add_argument("--input", required=True, type=Path, help="Input image or video path.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output run directory. Defaults to outputs/pipeline/<run_id>.",
    )
    parser.add_argument("--run-id", default=None, help="Run id. Defaults to timestamp + input stem.")
    parser.add_argument(
        "--detector-model",
        type=Path,
        default=project_root / "models/detection/best.pt",
        help="YOLO detector .pt path.",
    )
    parser.add_argument(
        "--classifier-model",
        type=Path,
        default=project_root / "models/classification/best.pt",
        help="Brand classifier .pt path.",
    )
    parser.add_argument("--frame-stride", type=int, default=10)
    parser.add_argument("--device", default=None, help="Torch/Ultralytics device, e.g. cpu or 0.")
    parser.add_argument("--detector-conf-min", type=float, default=0.50)
    parser.add_argument("--detector-imgsz", type=int, default=960)
    parser.add_argument("--detector-iou", type=float, default=0.50)
    parser.add_argument("--min-detection-width", type=int, default=64)
    parser.add_argument("--min-detection-height", type=int, default=64)
    parser.add_argument("--min-detection-area-ratio", type=float, default=0.0015)
    parser.add_argument("--min-detection-aspect-ratio", type=float, default=0.25)
    parser.add_argument("--max-detection-aspect-ratio", type=float, default=8.0)
    parser.add_argument("--min-track-detections", type=int, default=2)
    parser.add_argument("--min-track-frame-span", type=int, default=10)
    parser.add_argument("--draw-rejected", action="store_true", help="Draw not_classified tracks.")
    parser.add_argument("--save-annotated-frames", action="store_true", help="Save annotated frame JPGs.")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> PipelineConfig:
    project_root = default_project_root()
    input_path = resolve_project_path(project_root, args.input)
    run_id = args.run_id or default_run_id(input_path)
    output_dir = (
        resolve_project_path(project_root, args.output_dir)
        if args.output_dir
        else project_root / "outputs/pipeline" / run_id
    )
    return PipelineConfig(
        project_root=project_root,
        input_path=input_path,
        output_dir=output_dir,
        detector_model_path=resolve_project_path(project_root, args.detector_model),
        classifier_model_path=resolve_project_path(project_root, args.classifier_model),
        run_id=run_id,
        frame_stride=args.frame_stride,
        detector_conf_min=args.detector_conf_min,
        detector_imgsz=args.detector_imgsz,
        detector_iou=args.detector_iou,
        min_detection_width=args.min_detection_width,
        min_detection_height=args.min_detection_height,
        min_detection_area_ratio=args.min_detection_area_ratio,
        min_detection_aspect_ratio=args.min_detection_aspect_ratio,
        max_detection_aspect_ratio=args.max_detection_aspect_ratio,
        min_track_detections=args.min_track_detections,
        min_track_frame_span=args.min_track_frame_span,
        device=args.device,
        draw_rejected=args.draw_rejected,
        save_annotated_frames=args.save_annotated_frames,
    )


def default_run_id(input_path: Path) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{input_path.stem}"


def main() -> int:
    args = parse_args()
    config = build_config(args)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"input: {config.input_path}")
    print(f"output: {config.output_dir}")
    print(f"detector: {config.detector_model_path}")
    print(f"classifier: {config.classifier_model_path}")

    detector = load_detector(config)
    metadata, frames, detections = run_detection_stage(detector, config)
    print(f"detections after gate: {len(detections)}")

    assign_track_ids(detections, config)

    if any(
        detection.crop_quality_status in {"passed", "borderline"}
        and detection.classification_input_status in {"accepted", "borderline"}
        for detection in detections
    ):
        classifier = load_classifier(config)
        classify_detections(classifier, detections, config)

    tracks = aggregate_tracks(detections, config)
    tracks_by_id = {track.track_id: track for track in tracks}
    copy_crops_by_status(detections, tracks_by_id, config.output_dir / "crops")

    write_annotated_media(config.output_dir, frames, detections, tracks, metadata, config)
    write_pipeline_outputs(config.output_dir, metadata, detections, tracks)

    print(f"tracks: {len(tracks)}")
    print(f"report: {config.output_dir / 'report.html'}")
    return 0


def run_detection_stage(
    detector,
    config: PipelineConfig,
) -> tuple[InputMetadata, list[FrameRecord] | None, list[DetectionRecord]]:
    metadata = load_metadata(config.input_path, config.frame_stride)
    if metadata.input_type == "video":
        detections = run_video_detection_stream(detector, metadata, config)
        return metadata, None, detections

    metadata, frames = load_frames(config.input_path, config.frame_stride)
    print(f"loaded frames: {len(frames)} ({metadata.input_type}, fps={metadata.fps:.3f})")
    detections = run_detection(detector, frames, metadata, config)
    save_detection_crops(
        detections,
        {frame.frame_index: frame for frame in frames},
        config.output_dir / "crops" / "all",
        config,
    )
    evaluate_crop_quality(detections, config)
    return metadata, frames, detections


def run_video_detection_stream(
    detector,
    metadata: InputMetadata,
    config: PipelineConfig,
) -> list[DetectionRecord]:
    detections: list[DetectionRecord] = []
    crops_dir = config.output_dir / "crops" / "all"
    processed_frames = 0

    print(
        f"streaming video frames: stride={metadata.frame_stride}, fps={metadata.fps:.3f}",
        flush=True,
    )
    for frame in iter_frames(config.input_path, config.frame_stride):
        frame_detections = run_detection(detector, [frame], metadata, config)
        save_detection_crops(frame_detections, {frame.frame_index: frame}, crops_dir, config)
        evaluate_crop_quality(frame_detections, config)
        detections.extend(frame_detections)

        processed_frames += 1
        if processed_frames % 100 == 0:
            print(
                f"processed sampled frames: {processed_frames}, detections after gate: {len(detections)}",
                flush=True,
            )

    if processed_frames == 0:
        raise RuntimeError(f"No frames were read from video: {config.input_path}")
    print(f"processed sampled frames: {processed_frames} ({metadata.input_type}, fps={metadata.fps:.3f})")
    return detections


if __name__ == "__main__":
    raise SystemExit(main())
