"""Low-level CSV and metadata writers."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ..artifacts import InputMetadataJson
from ..schemas import InputMetadata


def write_input_meta(path: Path, metadata: InputMetadata) -> None:
    row = InputMetadataJson(
        source_path=str(metadata.source_path),
        input_type=metadata.input_type,
        fps=metadata.fps,
        frame_count=metadata.frame_count,
        frame_stride=metadata.frame_stride,
        delta_t_sec=metadata.delta_t_sec,
        width=metadata.width,
        height=metadata.height,
    ).model_dump(mode="json")
    with path.open("w", encoding="utf-8") as handle:
        json.dump(row, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_dict_csv(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    fieldnames: list[str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    resolved_fieldnames = fieldnames or (list(rows[0].keys()) if rows else None)
    if resolved_fieldnames is None:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=resolved_fieldnames)
        writer.writeheader()
        if rows:
            writer.writerows(rows)
