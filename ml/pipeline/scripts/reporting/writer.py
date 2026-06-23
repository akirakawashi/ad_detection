"""Top-level report artifact writer."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.reporting.charts import write_charts
from scripts.reporting.csv_io import write_dict_csv, write_input_meta
from scripts.reporting.html_report import write_html_report
from scripts.reporting.summaries import write_summaries
from scripts.schemas import DetectionRecord, InputMetadata, TrackRecord


def write_pipeline_outputs(
    output_dir: Path,
    metadata: InputMetadata,
    detections: list[DetectionRecord],
    tracks: list[TrackRecord],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_input_meta(output_dir / "input_meta.json", metadata)
    detections_csv = output_dir / "detections.csv"
    tracks_csv = output_dir / "tracks.csv"
    write_dict_csv(detections_csv, [detection.to_row() for detection in detections])
    write_dict_csv(tracks_csv, [track.to_row() for track in tracks])

    detections_df = pd.DataFrame([detection.to_row() for detection in detections])
    tracks_df = pd.DataFrame([track.to_row() for track in tracks])
    write_summaries(output_dir, detections_df, tracks_df)
    write_charts(output_dir / "charts", detections_df, tracks_df)
    write_html_report(output_dir / "report.html", metadata, detections_df, tracks_df)
