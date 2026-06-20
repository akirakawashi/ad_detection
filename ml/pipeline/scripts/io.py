"""Input frame loading helpers."""

from __future__ import annotations

from pathlib import Path

import cv2

from scripts.schemas import FrameRecord, InputMetadata


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
VIDEO_EXTENSIONS = {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}


def detect_input_type(input_path: Path) -> str:
    suffix = input_path.suffix.casefold()
    if suffix in IMAGE_EXTENSIONS:
        return "image"
    if suffix in VIDEO_EXTENSIONS:
        return "video"
    raise ValueError(f"Unsupported input extension: {input_path.suffix}")


def load_frames(input_path: Path, frame_stride: int) -> tuple[InputMetadata, list[FrameRecord]]:
    if frame_stride < 1:
        raise ValueError("frame_stride must be >= 1")
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    input_type = detect_input_type(input_path)
    if input_type == "image":
        return _load_image(input_path, frame_stride)
    return _load_video(input_path, frame_stride)


def _load_image(input_path: Path, frame_stride: int) -> tuple[InputMetadata, list[FrameRecord]]:
    image = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {input_path}")

    height, width = image.shape[:2]
    metadata = InputMetadata(
        source_path=input_path,
        input_type="image",
        fps=1.0,
        frame_count=1,
        frame_stride=frame_stride,
        delta_t_sec=1.0,
        width=width,
        height=height,
    )
    frame = FrameRecord(
        frame_index=0,
        timestamp_sec=0.0,
        width=width,
        height=height,
        delta_t_sec=1.0,
        image=image,
    )
    return metadata, [frame]


def _load_video(input_path: Path, frame_stride: int) -> tuple[InputMetadata, list[FrameRecord]]:
    cap = cv2.VideoCapture(str(input_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {input_path}")

    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0:
        fps = 25.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    delta_t_sec = frame_stride / fps

    frames: list[FrameRecord] = []
    frame_index = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_index % frame_stride == 0:
                frames.append(
                    FrameRecord(
                        frame_index=frame_index,
                        timestamp_sec=frame_index / fps,
                        width=frame.shape[1],
                        height=frame.shape[0],
                        delta_t_sec=delta_t_sec,
                        image=frame.copy(),
                    )
                )
            frame_index += 1
    finally:
        cap.release()

    if not frames:
        raise RuntimeError(f"No frames were read from video: {input_path}")

    if width <= 0 or height <= 0:
        height, width = frames[0].image.shape[:2]
    if frame_count <= 0:
        frame_count = frame_index

    metadata = InputMetadata(
        source_path=input_path,
        input_type="video",
        fps=fps,
        frame_count=frame_count,
        frame_stride=frame_stride,
        delta_t_sec=delta_t_sec,
        width=width,
        height=height,
    )
    return metadata, frames
