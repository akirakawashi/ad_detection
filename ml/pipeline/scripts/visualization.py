"""Annotated media helpers."""

from __future__ import annotations

from pathlib import Path

import cv2

from scripts.config import PipelineConfig
from scripts.schemas import DetectionRecord, FrameRecord, InputMetadata, TrackRecord


COLORS = {
    "mts": (0, 0, 255),
    "plus7": (255, 180, 0),
    "miranda": (30, 180, 60),
    "other": (150, 150, 150),
}


def write_annotated_media(
    output_dir: Path,
    frames: list[FrameRecord] | None,
    detections: list[DetectionRecord],
    tracks: list[TrackRecord],
    metadata: InputMetadata,
    config: PipelineConfig,
) -> None:
    annotated_dir = None
    if config.save_annotated_frames:
        annotated_dir = output_dir / "frames" / "annotated"
        annotated_dir.mkdir(parents=True, exist_ok=True)

    detections_by_frame: dict[int, list[DetectionRecord]] = {}
    for detection in detections:
        detections_by_frame.setdefault(detection.frame_index, []).append(detection)
    tracks_by_id = {track.track_id: track for track in tracks}

    if metadata.input_type == "video" and frames is None:
        write_annotated_video_from_source(
            output_dir,
            detections_by_frame,
            tracks_by_id,
            metadata,
            config,
            annotated_dir,
        )
        return

    if frames is None:
        return

    writer = create_annotated_video_writer(output_dir / "video" / "annotated_video.mp4", frames, metadata)
    try:
        for frame in frames:
            annotated = frame.image.copy()
            for detection in detections_by_frame.get(frame.frame_index, []):
                if not detection.business_visible:
                    continue
                track = tracks_by_id.get(detection.track_id or -1)
                draw_detection(annotated, detection, track)

            if annotated_dir is not None:
                frame_path = annotated_dir / f"frame_{frame.frame_index:06d}.jpg"
                cv2.imwrite(str(frame_path), annotated)
            if writer is not None:
                writer.write(annotated)
    finally:
        if writer is not None:
            writer.release()


def write_annotated_video_from_source(
    output_dir: Path,
    detections_by_frame: dict[int, list[DetectionRecord]],
    tracks_by_id: dict[int, TrackRecord],
    metadata: InputMetadata,
    config: PipelineConfig,
    annotated_dir: Path | None,
) -> None:
    cap = cv2.VideoCapture(str(metadata.source_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {metadata.source_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or metadata.fps or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or metadata.width)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or metadata.height)

    output_video = output_dir / "video" / "annotated_video.mp4"
    output_video.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(output_video),
        video_writer_fourcc("mp4v"),
        fps,
        (width, height),
    )
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not create annotated video: {output_video}")

    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            annotated = frame.copy()
            frame_detections = detections_by_frame.get(frame_index, [])
            for detection in frame_detections:
                if not detection.business_visible:
                    continue
                track = tracks_by_id.get(detection.track_id or -1)
                draw_detection(annotated, detection, track)

            if annotated_dir is not None and frame_detections:
                frame_path = annotated_dir / f"frame_{frame_index:06d}.jpg"
                cv2.imwrite(str(frame_path), annotated)

            writer.write(annotated)
            frame_index += 1
    finally:
        cap.release()
        writer.release()


def draw_detection(
    image,
    detection: DetectionRecord,
    track: TrackRecord | None,
) -> None:
    brand = display_brand(detection, track)
    color = COLORS.get(brand, COLORS["other"])
    x1, y1, x2, y2 = (int(round(value)) for value in detection.bbox_xyxy)
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

    label = brand.upper()
    text_y = max(18, y1 - 6)
    cv2.putText(
        image,
        label,
        (x1, text_y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2,
        cv2.LINE_AA,
    )


def display_brand(detection: DetectionRecord, track: TrackRecord | None) -> str:
    if track:
        return track.business_brand or "other"
    return detection.business_brand or "other"


def create_annotated_video_writer(
    path: Path,
    frames: list[FrameRecord],
    metadata: InputMetadata,
):
    if metadata.input_type != "video" or not frames:
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    fps = max(1.0, metadata.fps / max(1, metadata.frame_stride))
    first = frames[0]
    writer = cv2.VideoWriter(
        str(path),
        video_writer_fourcc("mp4v"),
        fps,
        (first.width, first.height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create annotated video: {path}")
    return writer


def video_writer_fourcc(codec: str) -> int:
    return int(getattr(cv2, "VideoWriter_fourcc")(*codec))
