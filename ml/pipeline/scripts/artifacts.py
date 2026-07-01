"""Typed public artifact payloads written by the pipeline."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from .domain import (
    BrandStatus,
    ClassificationInputStatus,
    CropQualityStatus,
    FinalStatus,
)
from .schemas import DetectionRecord, InputMetadata, TrackRecord


class ArtifactModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class InputMetadataJson(ArtifactModel):
    source_path: str
    input_type: str
    fps: float
    frame_count: int
    frame_stride: int
    delta_t_sec: float
    width: int
    height: int

    @classmethod
    def from_metadata(cls, metadata: InputMetadata) -> InputMetadataJson:
        return cls(
            source_path=str(metadata.source_path),
            input_type=metadata.input_type,
            fps=metadata.fps,
            frame_count=metadata.frame_count,
            frame_stride=metadata.frame_stride,
            delta_t_sec=metadata.delta_t_sec,
            width=metadata.width,
            height=metadata.height,
        )


class DetectionCsvRow(ArtifactModel):
    run_id: str
    source_path: str
    input_type: str
    frame_index: int
    timestamp_sec: float
    sample_delta_t_sec: float
    det_index: int
    track_id: int | None
    det_class: str
    det_conf: float
    bbox_x1: float
    bbox_y1: float
    bbox_x2: float
    bbox_y2: float
    bbox_width: float
    bbox_height: float
    bbox_aspect_ratio: float
    bbox_area: float
    area_ratio: float
    center_x: float
    center_y: float
    center_x_norm: float
    center_y_norm: float
    position_label: str
    position_weight: float
    object_id: int | None
    crop_path: str
    crop_width: int
    crop_height: int
    crop_quality_status: CropQualityStatus
    crop_quality_reason: str
    crop_quality_score: float
    classification_input_status: ClassificationInputStatus
    classification_attempted: bool
    brand_pred: str
    brand_conf: float
    top1_brand: str
    top1_score: float
    top2_brand: str
    top2_score: float
    top3_brand: str
    top3_score: float
    video_visibility_score: float
    video_visibility_weighted_seconds: float
    overall_score: float
    brand_status: BrandStatus
    final_status: FinalStatus
    business_brand: str
    business_visible: bool
    status_reason: str

    @classmethod
    def from_detection(cls, detection: DetectionRecord) -> DetectionCsvRow:
        return cls.model_validate(detection)

    def to_csv_row(self) -> dict[str, Any]:
        row = self.model_dump(mode="json")
        row["track_id"] = "" if self.track_id is None else self.track_id
        row["object_id"] = "" if self.object_id is None else self.object_id
        row["classification_attempted"] = int(self.classification_attempted)
        row["business_visible"] = int(self.business_visible)
        return row


class TrackCsvRow(ArtifactModel):
    run_id: str
    source_path: str
    track_id: int
    object_id: int
    first_frame_index: int
    last_frame_index: int
    first_timestamp_sec: float
    last_timestamp_sec: float
    visible_duration_sec: float
    detections_count: int
    classified_crops_count: int
    best_crop_path: str
    best_frame_index: int
    best_timestamp_sec: float
    mean_det_conf: float
    max_det_conf: float
    mean_crop_quality_score: float
    best_crop_quality_score: float
    max_area_ratio: float
    mean_area_ratio: float
    sum_area_ratio: float
    mean_position_weight: float
    mean_video_visibility_score: float
    sum_video_visibility_score: float
    video_visibility_weighted_seconds: float
    final_brand: str
    final_brand_conf: float
    final_status: FinalStatus
    business_brand: str
    business_visible: bool
    final_status_reason: str
    track_confirmed: bool
    track_final_score: float
    manual_review_required: bool

    @classmethod
    def from_track(cls, track: TrackRecord) -> TrackCsvRow:
        return cls.model_validate(track)

    def to_csv_row(self) -> dict[str, Any]:
        row = self.model_dump(mode="json")
        row["manual_review_required"] = int(self.manual_review_required)
        row["track_confirmed"] = int(self.track_confirmed)
        row["business_visible"] = int(self.business_visible)
        return row


DETECTION_CSV_FIELDS = list(DetectionCsvRow.model_fields)
TRACK_CSV_FIELDS = list(TrackCsvRow.model_fields)

BRAND_DETECTION_SUMMARY_FIELDS = [
    "brand",
    "detection_count",
    "mean_brand_conf",
    "max_brand_conf",
    "first_timestamp_sec",
    "last_timestamp_sec",
    "sum_video_visibility_score",
]

FRAME_SUMMARY_FIELDS = [
    "frame_index",
    "timestamp_sec",
    "detections_total",
    "mts_count",
    "plus7_count",
    "miranda_count",
    "other_count",
    "sum_video_visibility_score",
]

BRAND_TRACK_SUMMARY_FIELDS = [
    "brand",
    "object_count",
    "track_fragment_count",
    "mean_track_final_score",
    "mean_video_visibility_score",
    "sum_video_visibility_score",
    "video_visibility_weighted_seconds",
    "mean_final_brand_conf",
    "max_final_brand_conf",
    "first_timestamp_sec",
    "last_timestamp_sec",
]


class OverlayVideoPayload(ArtifactModel):
    source: str
    width: int
    height: int
    fps: float
    frame_count: int
    frame_stride: int


class OverlayDisplayPayload(ArtifactModel):
    max_cards_per_frame: int
    fields: list[str]


class OverlayObjectPayload(ArtifactModel):
    object_id: int | None
    track_id: int | None
    brand: str
    label: str
    color: str
    bbox: tuple[float, float, float, float]
    det_conf: float
    brand_conf: float
    area_ratio: float
    visibility_score: float
    overall_score: float
    card_priority: float


class OverlayFramePayload(ArtifactModel):
    frame_index: int
    timestamp_sec: float
    objects: list[OverlayObjectPayload]


class OverlayPayload(ArtifactModel):
    version: int
    video: OverlayVideoPayload
    display: OverlayDisplayPayload
    frames: list[OverlayFramePayload]
