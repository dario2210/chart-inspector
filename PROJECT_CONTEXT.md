# Chart Inspector Project Context

This file is a handoff summary extracted from the BEE4 discussion so the Chart
Inspector project can continue in a separate thread without mixing strategy
work with the inspector tool.

## Goal

Build a universal chart analysis and annotation tool that can be reused by
different bots, simulations and result files, not only BEE4.

The tool should:

- load candle files from CSV or Parquet,
- optionally load a bot/simulation result JSON,
- display price, indicators, trades and manual labels,
- allow the user to click on the chart and mark custom points,
- save those points as an independent annotations file,
- include candle values and indicator values in each saved annotation.

## Why It Exists

The BEE4 dashboard chart became too limited for fast visual analysis. It is
useful for summaries and WFO/backtest output, but less comfortable for quickly
moving around the chart, checking missed signals and manually marking examples.

Chart Inspector is meant to be a separate tool:

- BEE4/BEE5/etc. produce data and result files.
- Chart Inspector reads those files.
- Manual observations are saved separately.
- Later, those manual observations can be compared against strategy logic or
  used to design better filters.

## Architecture Decision

Chart Inspector is a separate project and container.

Suggested server path:

```text
/home/darek/apps/infra/chart-inspector
```

Suggested container:

```text
chart_inspector
```

Suggested local port:

```text
127.0.0.1:8070
```

GitHub repository:

```text
https://github.com/dario2210/chart-inspector.git
```

## Data Model

Expected candle file columns:

```text
time, open, high, low, close
```

Optional columns:

```text
volume, indicator columns
```

Simulation result files should ideally contain:

```json
{
  "project": "bee4",
  "symbol": "ETHUSDT",
  "tf": "1h",
  "data_file": "ethusdt_1h.csv",
  "params_used": {
    "wt_channel_len": 10,
    "wt_avg_len": 21,
    "wt_signal_len": 4,
    "wt_h4_filter_interval": "4h"
  },
  "trades": []
}
```

## Annotation File

Manual annotations should be saved separately from strategy results.

Each annotation should include:

- source file,
- optional result file,
- symbol,
- timeframe,
- timestamp,
- label,
- comment,
- selected price,
- indicator parameters,
- full row snapshot with OHLCV and indicator values.

Example:

```json
{
  "source_file": "ethusdt_1h.csv",
  "result_file": "bee4_backtest.json",
  "symbol": "ETHUSDT",
  "timeframe": "1h",
  "time": "2024-03-12T15:00:00+00:00",
  "label": "good_long",
  "comment": "manual setup worth testing",
  "price": 3520.5,
  "indicator_params": {
    "wavetrend": {
      "channel_len": 10,
      "avg_len": 21,
      "signal_len": 4
    }
  },
  "row_data": {
    "open": 3501.2,
    "high": 3540.0,
    "low": 3488.1,
    "close": 3520.5,
    "wt1": -48.2,
    "wt2": -52.7
  }
}
```

## Indicator Requirements

The inspector should allow indicator parameters to be changed in the UI.

For BEE4, default values should come from the result file when available:

- `wt_channel_len`,
- `wt_avg_len`,
- `wt_signal_len`.

The first MVP recalculates WaveTrend with editable parameters.

Later versions can add:

- higher timeframe WaveTrend,
- EMA filters,
- ATR,
- custom indicator presets,
- multiple panels,
- faster chart renderer if Dash/Plotly becomes too slow.

## Important BEE4 Follow-Up

BEE4 should consistently save simulation parameters in result files. It already
stores `params_used` / `best_params` in saved run JSON files, but exported trade
files may later need a richer metadata format so Chart Inspector can reproduce
the exact indicator setup.

## Current MVP Scope

Initial project skeleton includes:

- Docker container,
- Dash web app on port 8070,
- file selection from `data/` and `results/`,
- editable WaveTrend parameters,
- optional trade overlay from result JSON,
- manual point annotation,
- saving annotations to JSON and CSV in `annotations/`.

## Suggested Prompt For A New Chat

```text
We are starting a separate project called Chart Inspector.

Repo: https://github.com/dario2210/chart-inspector.git
Server path: /home/darek/apps/infra/chart-inspector
Container: chart_inspector
Port: 8070

Goal: build a universal chart inspection and manual annotation tool for trading
strategy results. It should load candle files and optional bot result JSON files,
show price/indicators/trades, allow manual labels on selected chart points, and
save annotations with OHLCV and indicator row values.

Please continue from PROJECT_CONTEXT.md and inspect the current codebase before
making changes.
```

