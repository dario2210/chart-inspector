from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def row_snapshot(row: pd.Series) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for key, value in row.to_dict().items():
        if isinstance(value, pd.Timestamp):
            data[key] = value.isoformat()
        elif pd.isna(value):
            data[key] = None
        elif hasattr(value, "item"):
            data[key] = value.item()
        else:
            data[key] = value
    return data


def build_annotation(
    *,
    source_file: str,
    result_file: str | None,
    symbol: str,
    timeframe: str,
    label: str,
    comment: str,
    row: pd.Series,
    price: float,
    indicator_params: dict[str, Any],
) -> dict[str, Any]:
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_file": source_file,
        "result_file": result_file,
        "symbol": symbol,
        "timeframe": timeframe,
        "time": pd.Timestamp(row["time"]).isoformat(),
        "label": label,
        "comment": comment,
        "price": float(price),
        "indicator_params": indicator_params,
        "row_data": row_snapshot(row),
    }


def save_annotations(
    annotations_dir: Path,
    source_file: str,
    annotations: list[dict[str, Any]],
) -> tuple[Path, Path]:
    annotations_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    source_stem = Path(source_file).stem if source_file else "annotations"
    json_path = annotations_dir / f"{source_stem}_annotations_{stamp}.json"
    csv_path = annotations_dir / f"{source_stem}_annotations_{stamp}.csv"
    payload = {
        "source_file": source_file,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "annotations": annotations,
    }
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    flat_rows = []
    for item in annotations:
        flat = {k: v for k, v in item.items() if k != "row_data"}
        for key, value in item.get("row_data", {}).items():
            flat[f"row_{key}"] = value
        flat_rows.append(flat)
    pd.DataFrame(flat_rows).to_csv(csv_path, index=False)
    return json_path, csv_path
