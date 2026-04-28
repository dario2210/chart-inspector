# Chart Inspector

Universal chart annotation tool for trading simulations.

The project is intentionally separate from BEE bots. Bots can export candles,
trades, parameters and results. Chart Inspector loads those files, lets the
user inspect the chart, add manual annotations and save them as a separate
analysis file.

## MVP features

- Load candle files from `data/` (`.csv` in the MVP).
- Optionally load a simulation result file from `results/` (`.json`).
- Use indicator parameters from the result file when present.
- Recalculate WaveTrend with editable parameters.
- Show candlesticks, WaveTrend, optional extra indicator columns, trades and
  manual annotations.
- Click the chart to select a candle and save a labeled annotation.
- Save annotations to `annotations/` as JSON and CSV.

## Supported result JSON

`Result file` is an optional `.json` exported by a bot or simulation.

Supported structures:

- direct result payload with keys such as `symbol`, `tf`, `params_used`,
  `trades`,
- saved BEE wrapper with `schema`, `saved_at`, `meta` and nested `result`.

## Expected candle columns

At minimum:

```text
time, open, high, low, close
```

Optional:

```text
volume, any indicator columns
```

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m chart_inspector.app
```

Open:

```text
http://127.0.0.1:8070
```

## Run with Docker

```bash
docker compose up -d --build
```

## Annotation file

Annotations are saved with the source file, selected label, comment, selected
price and full row snapshot, including indicator values.

This creates a reusable manual dataset that can later be compared with BEE4,
BEE5 or any other strategy.

Parquet support can be added later by installing `pyarrow`, but the first
container is intentionally CSV-first to keep deployment small and fast.

## Project context

See `PROJECT_CONTEXT.md` for the handoff from the original BEE4 discussion and
the recommended prompt for starting a separate Chart Inspector chat.
