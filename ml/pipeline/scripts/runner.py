"""Pipeline orchestration for a single local run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.aggregation import aggregate_tracks
from scripts.classification import classify_detections, load_classifier
from scripts.config import PipelineConfig
from scripts.crops import copy_crops_by_status, save_detection_crops
from scripts.detection import load_detector, run_detection
from scripts.html_viewer import write_html_overlay_viewer
from scripts.io import iter_frames, load_frames, load_metadata
from scripts.overrides import apply_brand_overrides
from scripts.quality import evaluate_crop_quality
from scripts.reports import write_pipeline_outputs
from scripts.schemas import DetectionRecord, FrameRecord, InputMetadata, TrackRecord
from scripts.track_groups import assign_object_groups, stabilize_object_brands
from scripts.tracking import assign_track_ids
from scripts.visualization import write_annotated_media


@dataclass(frozen=True)
class PipelineRunResult:
    output_dir: Path
    metadata: InputMetadata
    detections: list[DetectionRecord]
    tracks: list[TrackRecord]


def run_pipeline(config: PipelineConfig) -> PipelineRunResult:
    config.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"input: {config.input_path}")
    print(f"output: {config.output_dir}")
    print(f"detector: {config.detector_model_path}")
    print(f"classifier: {config.classifier_model_path}")

    detector = load_detector(config)
    metadata, frames, detections = run_detection_stage(detector, config)
    print(f"detections after gate: {len(detections)}")

    assign_track_ids(detections, config)
    preliminary_tracks = aggregate_tracks(detections, config)
    object_count = assign_object_groups(preliminary_tracks, detections, config)
    print(f"objects: {object_count}")

    if any(
        detection.crop_quality_status in {"passed", "borderline"}
        and detection.classification_input_status in {"accepted", "borderline"}
        for detection in detections
    ):
        classifier = load_classifier(config)
        classify_detections(classifier, detections, config)

    tracks = aggregate_tracks(detections, config)

    applied_overrides = apply_brand_overrides(
        tracks, detections, config.brand_overrides_path
    )
    if applied_overrides:
        print(f"brand overrides applied: {applied_overrides}")
    stabilized_tracks = stabilize_object_brands(tracks, detections, config)
    if stabilized_tracks:
        print(f"tracks stabilized by object brand: {stabilized_tracks}")

    tracks_by_id = {track.track_id: track for track in tracks}
    copy_crops_by_status(detections, tracks_by_id, config.output_dir / "crops")

    write_annotated_media(
        config.output_dir, frames, detections, tracks, metadata, config
    )
    write_html_overlay_viewer(config.output_dir, metadata, detections, tracks, config)
    write_pipeline_outputs(config.output_dir, metadata, detections, tracks)

    print(f"tracks: {len(tracks)}")
    if metadata.input_type == "video":
        print(f"viewer: {config.output_dir / 'viewer.html'}")
    print(f"report: {config.output_dir / 'report.html'}")

    return PipelineRunResult(
        output_dir=config.output_dir,
        metadata=metadata,
        detections=detections,
        tracks=tracks,
    )


def run_detection_stage(
    detector: Any,
    config: PipelineConfig,
) -> tuple[InputMetadata, list[FrameRecord] | None, list[DetectionRecord]]:
    metadata = load_metadata(config.input_path, config.frame_stride)
    if metadata.input_type == "video":
        detections = run_video_detection_stream(detector, metadata, config)
        return metadata, None, detections

    metadata, frames = load_frames(config.input_path, config.frame_stride)
    print(
        f"loaded frames: {len(frames)} ({metadata.input_type}, fps={metadata.fps:.3f})"
    )
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
    detector: Any,
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
        save_detection_crops(
            frame_detections, {frame.frame_index: frame}, crops_dir, config
        )
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
    print(
        f"processed sampled frames: {processed_frames} ({metadata.input_type}, fps={metadata.fps:.3f})"
    )
    return detections
