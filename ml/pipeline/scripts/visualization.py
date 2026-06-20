"""Annotated media helpers."""

from __future__ import annotations

from pathlib import Path

import cv2

from scripts.config import PipelineConfig
from scripts.schemas import DetectionRecord, FrameRecord, InputMetadata, TrackRecord


COLORS = {
    "detected_brand": (30, 180, 60),
    "other": (150, 150, 150),
    "unknown": (0, 210, 255),
    "manual_review": (0, 140, 255),
    "not_classified": (40, 40, 220),
}


def write_annotated_media(
    output_dir: Path,
    frames: list[FrameRecord],
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

    writer = create_annotated_video_writer(output_dir / "video" / "annotated_video.mp4", frames, metadata)
    try:
        for frame in frames:
            annotated = frame.image.copy()
            for detection in detections_by_frame.get(frame.frame_index, []):
                track = tracks_by_id.get(detection.track_id or -1)
                if not config.draw_rejected and track and track.final_status == "not_classified":
                    continue
                draw_detection(annotated, detection, track)

            if annotated_dir is not None:
                frame_path = annotated_dir / f"frame_{frame.frame_index:06d}.jpg"
                cv2.imwrite(str(frame_path), annotated)
            if writer is not None:
                writer.write(annotated)
    finally:
        if writer is not None:
            writer.release()


def draw_detection(
    image,
    detection: DetectionRecord,
    track: TrackRecord | None,
) -> None:
    status = track.final_status if track else detection.final_status
    color = COLORS.get(status, (255, 255, 255))
    x1, y1, x2, y2 = (int(round(value)) for value in detection.bbox_xyxy)
    cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)

    lines = label_lines(detection, track)
    y = max(18, y1 - 6)
    for index, line in enumerate(lines):
        text_y = y + index * 18
        cv2.putText(
            image,
            line,
            (x1, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
            cv2.LINE_AA,
        )


def label_lines(detection: DetectionRecord, track: TrackRecord | None) -> list[str]:
    if track and track.final_status == "detected_brand":
        first = f"Brand: {track.final_brand.upper()}"
    else:
        status = track.final_status if track else detection.final_status
        first = f"Status: {status}"

    track_id = track.track_id if track else detection.track_id
    final_conf = track.final_brand_conf if track else detection.brand_conf
    return [
        first,
        f"Det:{detection.det_conf:.2f} Cls:{final_conf:.2f} CropQ:{detection.crop_quality_score:.2f}",
        f"Area:{detection.area_ratio * 100:.2f}% VideoVis:{detection.video_visibility_score:.2f} Track:{track_id}",
    ]


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
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (first.width, first.height),
    )
    if not writer.isOpened():
        raise RuntimeError(f"Could not create annotated video: {path}")
    return writer
