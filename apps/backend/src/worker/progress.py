from __future__ import annotations

from application.interfaces import PipelineRunRepository
from ml.pipeline.scripts.runner import PipelineProgressReporter


class DatabaseProgressReporter(PipelineProgressReporter):
    def __init__(
        self,
        repository: PipelineRunRepository,
        run_id: str,
    ) -> None:
        self._repository = repository
        self._run_id = run_id
        self._last_stage: str | None = None
        self._last_progress = -1

    def update(
        self,
        stage: str,
        progress: int,
        message: str | None = None,
    ) -> None:
        normalized = max(0, min(99, progress))
        create_event = (
            stage != self._last_stage or normalized - self._last_progress >= 10
        )
        self._repository.update_progress(
            self._run_id,
            stage=stage,
            progress=normalized,
            message=message,
            create_event=create_event,
        )
        self._repository.commit()
        self._last_stage = stage
        self._last_progress = normalized
