from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


DATA_EXTENSIONS = {".csv", ".parquet"}
RESULT_EXTENSIONS = {".json"}


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def list_files(directory: Path, extensions: set[str]) -> list[dict[str, str]]:
    if not directory.exists():
        return []
    options = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in extensions:
            options.append({"label": path.name, "value": path.name})
    return options


def normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {col: col.strip().lower() for col in out.columns}
    out = out.rename(columns=rename)
    if "open_time" in out.columns and "time" not in out.columns:
        out = out.rename(columns={"open_time": "time"})
    required = {"time", "open", "high", "low", "close"}
    missing = sorted(required - set(out.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")
    out["time"] = parse_time_series(out["time"])
    for col in ["open", "high", "low", "close", "volume"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["time", "open", "high", "low", "close"])
    return out.sort_values("time").reset_index(drop=True)


def parse_time_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        max_value = pd.to_numeric(series, errors="coerce").dropna().max()
        unit = "ms" if max_value and max_value > 10_000_000_000 else "s"
        return pd.to_datetime(series, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(series, utc=True, errors="coerce")


def load_candles(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return normalize_ohlcv_columns(pd.read_csv(path))
    if path.suffix.lower() == ".parquet":
        return normalize_ohlcv_columns(pd.read_parquet(path))
    raise ValueError(f"Unsupported data file: {path.name}")


def load_result(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def extract_params(result: dict[str, Any]) -> dict[str, Any]:
    for key in ("params_used", "best_params", "params", "indicator_params"):
        value = result.get(key)
        if isinstance(value, dict):
            return value
    return {}


def extract_trades(result: dict[str, Any]) -> pd.DataFrame:
    trades = result.get("trades", [])
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    for col in ["entry_time", "exit_time"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
    for col in ["entry_price", "exit_price", "pnl"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df
