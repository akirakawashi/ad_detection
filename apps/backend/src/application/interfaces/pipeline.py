from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, Protocol

from application.common.dto import PipelineArtifactDTO, PipelineRunDTO
from domain.entities import PipelineArtifactType, PipelineRunStage, PipelineRunStatus


class ObjectStat(Protocol):
    size: int


class ObjectStorage(Protocol):
    def ensure_bucket(self) -> None: ...

    def presigned_put(
        self,
        object_key: str,
        *,
        expires_seconds: int | None = None,
    ) -> str: ...

    def presigned_get(
        self,
        object_key: str,
        *,
        expires_seconds: int | None = None,
    ) -> str: ...

    def stat(self, object_key: str) -> ObjectStat: ...

    def download_file(self, object_key: str, destination: Path) -> None: ...

    def upload_file(
        self,
        source: Path,
        object_key: str,
        *,
        content_type: str | None = None,
    ) -> object: ...

    def put_stream(
        self,
        object_key: str,
        stream: BinaryIO,
        *,
        length: int,
        content_type: str,
    ) -> object: ...

    def read_bytes(self, object_key: str) -> bytes: ...

    def read_text(self, object_key: str) -> str: ...

    def put_bytes(
        self,
        object_key: str,
        value: bytes,
        *,
        content_type: str,
    ) -> object: ...


class PipelineRunRepository(Protocol):
    def create(
        self,
        *,
        run_id: str,
        source_name: str,
        source_object_key: str,
        content_type: str | None,
        size_bytes: int,
    ) -> PipelineRunDTO: ...

    def list_runs(
        self,
        *,
        page: int,
        page_size: int,
        status: PipelineRunStatus | str | None = None,
    ) -> tuple[list[PipelineRunDTO], int]: ...

    def get(
        self,
        run_id: str,
        *,
        with_artifacts: bool = True,
        with_events: bool = False,
    ) -> PipelineRunDTO | None: ...

    def mark_upload_complete(
        self,
        run_id: str,
        *,
        actual_size_bytes: int,
    ) -> PipelineRunDTO | None: ...

    def add_artifact(
        self,
        *,
        run_id: str,
        artifact_type: PipelineArtifactType,
        object_key: str,
        content_type: str,
        size_bytes: int,
    ) -> PipelineArtifactDTO: ...

    def claim_next(self, worker_id: str) -> PipelineRunDTO | None: ...

    def update_progress(
        self,
        run_id: str,
        *,
        stage: PipelineRunStage | str,
        progress: int,
        message: str | None,
        create_event: bool = False,
    ) -> None: ...

    def mark_completed(
        self,
        run_id: str,
        *,
        fps: float,
        frame_count: int,
        frame_stride: int,
        width: int,
        height: int,
    ) -> None: ...

    def mark_failed(
        self,
        run_id: str,
        *,
        error_code: str,
        error_message: str,
    ) -> None: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
