"""CSV, chart, and HTML report helpers."""

from __future__ import annotations

import csv
import html
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

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


def write_input_meta(path: Path, metadata: InputMetadata) -> None:
    row = asdict(metadata)
    row["source_path"] = str(metadata.source_path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(row, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_dict_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summaries(output_dir: Path, detections_df: pd.DataFrame, tracks_df: pd.DataFrame) -> None:
    if detections_df.empty:
        write_dict_csv(output_dir / "brand_summary_by_detections.csv", [])
        write_dict_csv(output_dir / "frame_summary.csv", [])
    else:
        detection_summary = (
            detections_df.groupby(["business_brand"], dropna=False)
            .agg(
                detection_count=("det_index", "count"),
                mean_brand_conf=("brand_conf", "mean"),
                max_brand_conf=("brand_conf", "max"),
                first_timestamp_sec=("timestamp_sec", "min"),
                last_timestamp_sec=("timestamp_sec", "max"),
                sum_video_visibility_score=("video_visibility_score", "sum"),
            )
            .reset_index()
            .rename(columns={"business_brand": "brand"})
        )
        detection_summary.to_csv(output_dir / "brand_summary_by_detections.csv", index=False)

        frame_summary = (
            detections_df.groupby(["frame_index", "timestamp_sec"], dropna=False)
            .agg(
                detections_total=("det_index", "count"),
                mts_count=("business_brand", lambda s: int((s == "mts").sum())),
                plus7_count=("business_brand", lambda s: int((s == "plus7").sum())),
                miranda_count=("business_brand", lambda s: int((s == "miranda").sum())),
                other_count=("business_brand", lambda s: int((s == "other").sum())),
                sum_video_visibility_score=("video_visibility_score", "sum"),
            )
            .reset_index()
        )
        frame_summary.to_csv(output_dir / "frame_summary.csv", index=False)

    if tracks_df.empty:
        write_dict_csv(output_dir / "brand_summary_by_tracks.csv", [])
        return

    object_df = (
        tracks_df.groupby(["object_id", "business_brand"], dropna=False)
        .agg(
            track_fragment_count=("track_id", "count"),
            mean_track_final_score=("track_final_score", "mean"),
            mean_video_visibility_score=("mean_video_visibility_score", "mean"),
            sum_video_visibility_score=("sum_video_visibility_score", "sum"),
            video_visibility_weighted_seconds=("video_visibility_weighted_seconds", "sum"),
            mean_final_brand_conf=("final_brand_conf", "mean"),
            max_final_brand_conf=("final_brand_conf", "max"),
            first_timestamp_sec=("first_timestamp_sec", "min"),
            last_timestamp_sec=("last_timestamp_sec", "max"),
        )
        .reset_index()
    )
    track_summary = (
        object_df.groupby(["business_brand"], dropna=False)
        .agg(
            object_count=("object_id", "count"),
            track_fragment_count=("track_fragment_count", "sum"),
            mean_track_final_score=("mean_track_final_score", "mean"),
            mean_video_visibility_score=("mean_video_visibility_score", "mean"),
            sum_video_visibility_score=("sum_video_visibility_score", "sum"),
            video_visibility_weighted_seconds=("video_visibility_weighted_seconds", "sum"),
            mean_final_brand_conf=("mean_final_brand_conf", "mean"),
            max_final_brand_conf=("max_final_brand_conf", "max"),
            first_timestamp_sec=("first_timestamp_sec", "min"),
            last_timestamp_sec=("last_timestamp_sec", "max"),
        )
        .reset_index()
        .rename(columns={"business_brand": "brand"})
    )
    track_summary.to_csv(output_dir / "brand_summary_by_tracks.csv", index=False)


def write_charts(charts_dir: Path, detections_df: pd.DataFrame, tracks_df: pd.DataFrame) -> None:
    charts_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    try:
        import plotly.express as px
    except Exception as exc:  # noqa: BLE001 - charts are optional artifacts
        (charts_dir / "chart_failures.txt").write_text(
            f"plotly import failed: {exc}\n",
            encoding="utf-8",
        )
        return

    def save_chart(name: str, figure) -> None:
        try:
            figure.write_image(str(charts_dir / name))
        except Exception as exc:  # noqa: BLE001 - charts are optional artifacts
            fallback_name = f"{Path(name).stem}.html"
            figure.write_html(str(charts_dir / fallback_name), include_plotlyjs="cdn")
            failures.append(f"{name}: {exc}\nfallback: {fallback_name}")

    if not tracks_df.empty:
        object_brand = build_object_frame(tracks_df)
        save_chart(
            "tracks_by_brand.png",
            px.histogram(object_brand, x="brand", color="brand", title="Objects by brand"),
        )
        save_chart(
            "video_visibility_by_brand.png",
            px.bar(
                object_brand.groupby("brand", as_index=False)["video_visibility_weighted_seconds"].sum(),
                x="brand",
                y="video_visibility_weighted_seconds",
                title="Time-weighted video visibility by brand",
            ),
        )

    if not detections_df.empty:
        save_chart(
            "detections_by_brand.png",
            px.histogram(
                detections_df,
                x="business_brand",
                color="business_brand",
                title="Detections by brand",
            ),
        )
        save_chart(
            "confidence_distribution.png",
            px.histogram(detections_df, x="brand_conf", title="Brand confidence distribution"),
        )
        save_chart(
            "crop_quality_score_distribution.png",
            px.histogram(detections_df, x="crop_quality_score", title="Crop quality score distribution"),
        )
        timeline = (
            detections_df.groupby(["timestamp_sec", "business_brand"], as_index=False)[
                "video_visibility_score"
            ].sum()
        )
        save_chart(
            "video_visibility_timeline.png",
            px.line(
                timeline,
                x="timestamp_sec",
                y="video_visibility_score",
                color="business_brand",
                title="Video visibility timeline",
            ),
        )
        save_chart(
            "area_ratio_timeline.png",
            px.scatter(
                detections_df,
                x="timestamp_sec",
                y="area_ratio",
                color="business_brand",
                title="Area ratio timeline",
            ),
        )

    if failures:
        (charts_dir / "chart_failures.txt").write_text("\n".join(failures) + "\n", encoding="utf-8")


def build_object_frame(tracks_df: pd.DataFrame) -> pd.DataFrame:
    return (
        tracks_df.groupby(["object_id", "business_brand"], dropna=False)
        .agg(
            track_fragment_count=("track_id", "count"),
            video_visibility_weighted_seconds=("video_visibility_weighted_seconds", "sum"),
        )
        .reset_index()
        .rename(columns={"business_brand": "brand"})
    )


def write_html_report(
    path: Path,
    metadata: InputMetadata,
    detections_df: pd.DataFrame,
    tracks_df: pd.DataFrame,
) -> None:
    title = f"Ad visibility report: {metadata.source_path.name}"
    parts = [
        "<!doctype html>",
        "<html><head><meta charset='utf-8'>",
        f"<title>{html.escape(title)}</title>",
        "<style>body{font-family:Arial,sans-serif;max-width:1200px;margin:32px auto;line-height:1.4}"
        "table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #ddd;padding:6px}"
        "th{background:#f5f5f5}.gallery{display:flex;gap:12px;flex-wrap:wrap}.card{width:180px}"
        ".card img{max-width:180px;max-height:140px;object-fit:contain;border:1px solid #ddd}</style>",
        "</head><body>",
        f"<h1>{html.escape(title)}</h1>",
        "<h2>Input</h2>",
        table_from_rows(
            [
                {"field": "source", "value": str(metadata.source_path)},
                {"field": "input_type", "value": metadata.input_type},
                {"field": "fps", "value": f"{metadata.fps:.3f}"},
                {"field": "frame_count", "value": metadata.frame_count},
                {"field": "frame_stride", "value": metadata.frame_stride},
                {"field": "delta_t_sec", "value": f"{metadata.delta_t_sec:.3f}"},
            ]
        ),
    ]

    parts.append("<h2>Track/Object Summary</h2>")
    if tracks_df.empty:
        parts.append("<p>No tracks found.</p>")
    else:
        display_columns = [
            "object_id",
            "track_id",
            "business_brand",
            "first_timestamp_sec",
            "last_timestamp_sec",
            "visible_duration_sec",
            "detections_count",
            "final_brand_conf",
            "track_final_score",
            "video_visibility_weighted_seconds",
            "best_crop_path",
        ]
        parts.append(table_from_rows(tracks_df[display_columns].head(50).to_dict("records")))

    parts.append("<h2>Detection Summary</h2>")
    if detections_df.empty:
        parts.append("<p>No detections found.</p>")
    else:
        brand_counts = detections_df["business_brand"].value_counts().reset_index()
        brand_counts.columns = ["brand", "count"]
        parts.append(table_from_rows(brand_counts.to_dict("records")))

    parts.extend(["</body></html>"])
    path.write_text("\n".join(parts), encoding="utf-8")


def table_from_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<p>No rows.</p>"
    columns = list(rows[0].keys())
    html_rows = ["<table><thead><tr>"]
    html_rows.extend(f"<th>{html.escape(str(column))}</th>" for column in columns)
    html_rows.append("</tr></thead><tbody>")
    for row in rows:
        html_rows.append("<tr>")
        html_rows.extend(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns)
        html_rows.append("</tr>")
    html_rows.append("</tbody></table>")
    return "".join(html_rows)
