from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from domain.entities import PipelineArtifactType, PipelineRunStage, PipelineRunStatus


class ApplicationDTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class UploadTargetDTO(ApplicationDTO):
    method: str
    url: str
    headers: dict[str, str]


class PipelineArtifactDTO(ApplicationDTO):
    id: str
    run_id: str
    artifact_type: PipelineArtifactType
    object_key: str
    content_type: str
    size_bytes: int
    created_at: datetime | None


class PipelineRunEventDTO(ApplicationDTO):
    id: str
    run_id: str
    stage: PipelineRunStage | str
    progress: int = Field(ge=0, le=100)
    message: str | None
    created_at: datetime | None


class PipelineRunDTO(ApplicationDTO):
    run_id: str
    source_name: str
    source_object_key: str
    source_content_type: str | None
    source_size_bytes: int
    status: PipelineRunStatus
    stage: PipelineRunStage | str
    progress: int = Field(ge=0, le=100)
    status_message: str | None
    error_code: str | None
    error_message: str | None
    fps: float | None
    frame_count: int | None
    frame_stride: int | None
    duration_sec: float | None
    width: int | None
    height: int | None
    created_at: datetime | None
    upload_completed_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    updated_at: datetime | None
    artifacts: list[PipelineArtifactDTO] = Field(default_factory=list)
    events: list[PipelineRunEventDTO] = Field(default_factory=list)


class CreateRunDTO(ApplicationDTO):
    run_id: str
    status: PipelineRunStatus
    upload: UploadTargetDTO


class PaginatedRunsDTO(ApplicationDTO):
    items: list[PipelineRunDTO]
    page: int
    page_size: int
    total: int


class ArtifactUrlDTO(ApplicationDTO):
    artifact_id: str
    url: str


class PlaybackDTO(ApplicationDTO):
    source_url: str | None
    annotated_url: str | None


class BrandSummaryDTO(ApplicationDTO):
    brand: str | None = None
    object_count: int = 0
    track_fragment_count: int | None = None
    mean_track_final_score: float | None = None
    mean_video_visibility_score: float | None = None
    sum_video_visibility_score: float | None = None
    video_visibility_weighted_seconds: float | None = None
    mean_final_brand_conf: float | None = None
    max_final_brand_conf: float | None = None
    first_timestamp_sec: float | None = None
    last_timestamp_sec: float | None = None


class RunSummaryTotalsDTO(ApplicationDTO):
    total_objects: int
    visibility_index: float


class RunSummaryDTO(ApplicationDTO):
    run: PipelineRunDTO
    totals: RunSummaryTotalsDTO
    brands: list[BrandSummaryDTO]


class RunObjectDTO(ApplicationDTO):
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
    final_status: str
    business_brand: str
    business_visible: bool
    final_status_reason: str
    track_confirmed: bool
    track_final_score: float
    manual_review_required: bool
    crop_url: str | None = None


class RunObjectsDTO(ApplicationDTO):
    run_id: str
    objects: list[RunObjectDTO]


class RunTimelinePointDTO(ApplicationDTO):
    bucket_start_sec: float
    business_brand: str | None
    detection_count: int
    visibility_score: float


class RunTimelineDTO(ApplicationDTO):
    run_id: str
    bucket_seconds: int
    points: list[RunTimelinePointDTO]


class OverlayVideoDTO(ApplicationDTO):
    source: str
    width: int
    height: int
    fps: float
    frame_count: int
    frame_stride: int


class OverlayDisplayDTO(ApplicationDTO):
    max_cards_per_frame: int
    fields: list[str]


class OverlayObjectDTO(ApplicationDTO):
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


class OverlayFrameDTO(ApplicationDTO):
    frame_index: int
    timestamp_sec: float
    objects: list[OverlayObjectDTO]


class OverlayPayloadDTO(ApplicationDTO):
    version: int
    video: OverlayVideoDTO
    display: OverlayDisplayDTO
    frames: list[OverlayFrameDTO]
