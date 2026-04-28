from __future__ import annotations

import numpy as np
import pandas as pd


def compute_wavetrend(
    df: pd.DataFrame,
    channel_len: int = 10,
    avg_len: int = 21,
    signal_len: int = 4,
    prefix: str = "wt",
) -> pd.DataFrame:
    """Add WaveTrend columns to a copy of df."""
    out = df.copy()
    high = pd.to_numeric(out["high"], errors="coerce")
    low = pd.to_numeric(out["low"], errors="coerce")
    close = pd.to_numeric(out["close"], errors="coerce")
    ap = (high + low + close) / 3.0
    esa = ap.ewm(span=max(int(channel_len), 1), adjust=False).mean()
    d = (ap - esa).abs().ewm(span=max(int(channel_len), 1), adjust=False).mean()
    d = d.replace(0.0, np.nan)
    ci = (ap - esa) / (0.015 * d)
    wt1 = ci.ewm(span=max(int(avg_len), 1), adjust=False).mean()
    wt2 = wt1.rolling(max(int(signal_len), 1)).mean()
    out[f"{prefix}1"] = wt1
    out[f"{prefix}2"] = wt2
    out[f"{prefix}_delta"] = wt1 - wt2
    return out


def indicator_columns(df: pd.DataFrame) -> list[str]:
    base = {"time", "open", "high", "low", "close", "volume"}
    cols: list[str] = []
    for col in df.columns:
        if col.lower() in base:
            continue
        if pd.api.types.is_numeric_dtype(df[col]):
            cols.append(col)
    return cols
