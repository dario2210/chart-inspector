from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, dash_table, dcc, html, no_update
from plotly.subplots import make_subplots

from chart_inspector.annotations import build_annotation, save_annotations
from chart_inspector.indicators import compute_wavetrend, indicator_columns
from chart_inspector.io import (
    DATA_EXTENSIONS,
    RESULT_EXTENSIONS,
    ensure_dirs,
    extract_params,
    extract_trades,
    list_files,
    load_candles,
    load_result,
)


APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("CHART_INSPECTOR_DATA_DIR", APP_DIR / "data"))
RESULTS_DIR = Path(os.getenv("CHART_INSPECTOR_RESULTS_DIR", APP_DIR / "results"))
ANNOTATIONS_DIR = Path(os.getenv("CHART_INSPECTOR_ANNOTATIONS_DIR", APP_DIR / "annotations"))

ensure_dirs(DATA_DIR, RESULTS_DIR, ANNOTATIONS_DIR)

LABEL_OPTIONS = [
    {"label": "Good long", "value": "good_long"},
    {"label": "Bad long", "value": "bad_long"},
    {"label": "Good short", "value": "good_short"},
    {"label": "Bad short", "value": "bad_short"},
    {"label": "Missed long", "value": "missed_long"},
    {"label": "Missed short", "value": "missed_short"},
    {"label": "Exit", "value": "exit"},
    {"label": "Observation", "value": "observation"},
]

COLORS = {
    "bg": "#08111d",
    "panel": "#101b2c",
    "panel2": "#16253a",
    "text": "#edf6ff",
    "muted": "#9fb0c7",
    "green": "#22d3aa",
    "red": "#ff5d73",
    "blue": "#69b7ff",
    "amber": "#ffb454",
}


def control(label: str, child) -> html.Div:
    return html.Div([
        html.Div(label, className="ci-label"),
        child,
    ], className="ci-field")


def number_input(id_: str, value, min_=1) -> dcc.Input:
    return dcc.Input(id=id_, type="number", value=value, min=min_, debounce=True, className="ci-input")


def empty_figure(message: str = "Load a candle file to start.") -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        height=760,
        annotations=[
            {
                "text": message,
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": 0.5,
                "showarrow": False,
                "font": {"color": COLORS["muted"], "size": 16},
            }
        ],
    )
    return fig


def infer_symbol_tf(source_file: str, result: dict) -> tuple[str, str]:
    symbol = str(result.get("symbol") or "").upper()
    timeframe = str(result.get("tf") or result.get("timeframe") or "")
    stem = Path(source_file or "").stem
    if not symbol and "_" in stem:
        symbol = stem.split("_")[0].upper()
    if not timeframe and "_" in stem:
        timeframe = stem.split("_")[-1]
    return symbol or "UNKNOWN", timeframe or "UNKNOWN"


def prepare_frame(data_file: str, result_file: str | None, wt_channel: int, wt_avg: int, wt_signal: int):
    if not data_file:
        return pd.DataFrame(), {}, pd.DataFrame()
    result = load_result(RESULTS_DIR / result_file) if result_file else {}
    df = load_candles(DATA_DIR / data_file)
    df = compute_wavetrend(df, wt_channel, wt_avg, wt_signal)
    trades = extract_trades(result)
    return df, result, trades


def nearest_row(df: pd.DataFrame, clicked_time) -> pd.Series | None:
    if df.empty or clicked_time is None:
        return None
    ts = pd.to_datetime(clicked_time, utc=True, errors="coerce")
    if pd.isna(ts):
        return None
    idx = (df["time"] - ts).abs().idxmin()
    return df.loc[idx]


def build_figure(
    df: pd.DataFrame,
    trades: pd.DataFrame,
    annotations: list[dict],
    indicator_cols: list[str],
) -> go.Figure:
    if df.empty:
        return empty_figure()
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.62, 0.38],
        vertical_spacing=0.04,
    )
    fig.add_trace(
        go.Candlestick(
            x=df["time"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing_line_color=COLORS["green"],
            decreasing_line_color=COLORS["red"],
        ),
        row=1,
        col=1,
    )
    for col in indicator_cols:
        if col in df.columns:
            fig.add_trace(
                go.Scattergl(x=df["time"], y=df[col], mode="lines", name=col),
                row=2,
                col=1,
            )

    if not trades.empty and {"entry_time", "entry_price", "side"}.issubset(trades.columns):
        for side, color, marker in [("long", COLORS["green"], "triangle-up"), ("short", COLORS["red"], "triangle-down")]:
            sub = trades[trades["side"].astype(str).str.lower() == side]
            if not sub.empty:
                fig.add_trace(
                    go.Scatter(
                        x=sub["entry_time"],
                        y=sub["entry_price"],
                        mode="markers",
                        name=f"{side} entries",
                        marker={"color": color, "symbol": marker, "size": 11},
                        text=[f"{side.upper()} #{i+1}" for i in range(len(sub))],
                    ),
                    row=1,
                    col=1,
                )

    if annotations:
        ann_df = pd.DataFrame(annotations)
        if not ann_df.empty:
            ann_df["time"] = pd.to_datetime(ann_df["time"], utc=True, errors="coerce")
            fig.add_trace(
                go.Scatter(
                    x=ann_df["time"],
                    y=ann_df["price"],
                    mode="markers+text",
                    name="Manual labels",
                    text=ann_df["label"],
                    textposition="top center",
                    marker={"color": COLORS["amber"], "symbol": "star", "size": 12},
                    customdata=ann_df.get("comment"),
                ),
                row=1,
                col=1,
            )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=COLORS["bg"],
        plot_bgcolor=COLORS["bg"],
        height=780,
        margin={"l": 40, "r": 20, "t": 20, "b": 40},
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        uirevision="chart-inspector",
        legend={"orientation": "h", "y": 1.02},
    )
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)")
    return fig


app = Dash(__name__, title="Chart Inspector", suppress_callback_exceptions=True)
server = app.server

app.index_string = """<!DOCTYPE html>
<html>
<head>
{%metas%}<title>{%title%}</title>{%favicon%}{%css%}
<style>
body{margin:0;background:#08111d;color:#edf6ff;font-family:Segoe UI,Arial,sans-serif}
.ci-shell{display:grid;grid-template-columns:330px 1fr;min-height:100vh}
.ci-sidebar{background:#0d1828;border-right:1px solid rgba(255,255,255,.12);padding:20px;box-sizing:border-box}
.ci-main{padding:20px;box-sizing:border-box}
.ci-title{font-size:22px;font-weight:800;margin-bottom:4px}
.ci-sub{color:#9fb0c7;font-size:12px;line-height:1.45;margin-bottom:18px}
.ci-label{font-size:11px;color:#9fb0c7;text-transform:uppercase;letter-spacing:.06em;margin-bottom:5px}
.ci-field{margin-bottom:12px}
.ci-input,.ci-textarea input{width:100%}
.ci-input{background:#16253a;border:1px solid rgba(255,255,255,.14);border-radius:10px;color:#edf6ff;padding:9px 10px;box-sizing:border-box}
.ci-button{width:100%;border:0;border-radius:12px;padding:11px 12px;font-weight:800;cursor:pointer;margin-top:6px}
.ci-button-primary{background:#69b7ff;color:#06111e}
.ci-button-save{background:#22d3aa;color:#06111e}
.ci-card{background:#101b2c;border:1px solid rgba(255,255,255,.12);border-radius:18px;padding:16px;margin-bottom:14px}
.ci-status{color:#ffb454;font-size:12px;line-height:1.4;margin-top:8px;min-height:18px}
</style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>"""


app.layout = html.Div([
    dcc.Store(id="store-annotations", data=[]),
    dcc.Store(id="store-selected-row", data=None),
    html.Div([
        html.Div([
            html.Div("Chart Inspector", className="ci-title"),
            html.Div("Universal manual annotation tool for candles, indicators and bot results.", className="ci-sub"),
            control("Candle file", dcc.Dropdown(id="data-file", options=list_files(DATA_DIR, DATA_EXTENSIONS), value=None, clearable=False)),
            control("Result file optional", dcc.Dropdown(id="result-file", options=list_files(RESULTS_DIR, RESULT_EXTENSIONS), value=None, clearable=True)),
            html.Button("Refresh files", id="refresh-files", n_clicks=0, className="ci-button ci-button-primary"),
            html.Hr(),
            control("WT channel", number_input("wt-channel", 10)),
            control("WT average", number_input("wt-avg", 21)),
            control("WT signal", number_input("wt-signal", 4)),
            control("Indicator lines", dcc.Dropdown(id="indicator-cols", options=[], value=["wt1", "wt2"], multi=True)),
            html.Hr(),
            control("Manual label", dcc.Dropdown(id="annotation-label", options=LABEL_OPTIONS, value="observation", clearable=False)),
            control("Comment", dcc.Textarea(id="annotation-comment", value="", className="ci-input", style={"height": "80px"})),
            html.Button("Add annotation from click", id="add-annotation", n_clicks=0, className="ci-button ci-button-primary"),
            html.Button("Save annotations", id="save-annotations", n_clicks=0, className="ci-button ci-button-save"),
            html.Div(id="status", className="ci-status"),
        ], className="ci-sidebar"),
        html.Div([
            html.Div(id="selection-info", className="ci-card"),
            dcc.Graph(id="chart", figure=empty_figure(), config={"scrollZoom": True, "displayModeBar": True}),
            html.Div([
                html.Div("Annotations", className="ci-label"),
                dash_table.DataTable(
                    id="annotations-table",
                    data=[],
                    columns=[
                        {"name": "time", "id": "time"},
                        {"name": "label", "id": "label"},
                        {"name": "price", "id": "price"},
                        {"name": "comment", "id": "comment"},
                    ],
                    page_size=10,
                    style_table={"overflowX": "auto"},
                    style_cell={"backgroundColor": COLORS["panel"], "color": COLORS["text"], "border": "1px solid rgba(255,255,255,.12)", "fontSize": "12px"},
                    style_header={"backgroundColor": COLORS["panel2"], "color": COLORS["muted"], "fontWeight": "700"},
                ),
            ], className="ci-card"),
        ], className="ci-main"),
    ], className="ci-shell"),
])


@app.callback(
    Output("data-file", "options"),
    Output("result-file", "options"),
    Input("refresh-files", "n_clicks"),
)
def refresh_files(_):
    return list_files(DATA_DIR, DATA_EXTENSIONS), list_files(RESULTS_DIR, RESULT_EXTENSIONS)


@app.callback(
    Output("wt-channel", "value"),
    Output("wt-avg", "value"),
    Output("wt-signal", "value"),
    Input("result-file", "value"),
    prevent_initial_call=True,
)
def load_params_from_result(result_file):
    if not result_file:
        return no_update, no_update, no_update
    params = extract_params(load_result(RESULTS_DIR / result_file))
    return (
        int(params.get("wt_channel_len", params.get("channel_len", 10))),
        int(params.get("wt_avg_len", params.get("avg_len", 21))),
        int(params.get("wt_signal_len", params.get("signal_len", 4))),
    )


@app.callback(
    Output("indicator-cols", "options"),
    Output("indicator-cols", "value"),
    Input("data-file", "value"),
    Input("result-file", "value"),
    Input("wt-channel", "value"),
    Input("wt-avg", "value"),
    Input("wt-signal", "value"),
)
def update_indicator_options(data_file, result_file, wt_channel, wt_avg, wt_signal):
    if not data_file:
        return [], []
    df, _, _ = prepare_frame(data_file, result_file, int(wt_channel or 10), int(wt_avg or 21), int(wt_signal or 4))
    cols = indicator_columns(df)
    options = [{"label": col, "value": col} for col in cols]
    defaults = [col for col in ["wt1", "wt2"] if col in cols]
    return options, defaults


@app.callback(
    Output("chart", "figure"),
    Input("data-file", "value"),
    Input("result-file", "value"),
    Input("wt-channel", "value"),
    Input("wt-avg", "value"),
    Input("wt-signal", "value"),
    Input("indicator-cols", "value"),
    Input("store-annotations", "data"),
)
def update_chart(data_file, result_file, wt_channel, wt_avg, wt_signal, indicator_cols, annotations):
    if not data_file:
        return empty_figure()
    try:
        df, _, trades = prepare_frame(data_file, result_file, int(wt_channel or 10), int(wt_avg or 21), int(wt_signal or 4))
        return build_figure(df, trades, annotations or [], indicator_cols or [])
    except Exception as exc:
        return empty_figure(str(exc))


@app.callback(
    Output("store-selected-row", "data"),
    Output("selection-info", "children"),
    Input("chart", "clickData"),
    State("data-file", "value"),
    State("result-file", "value"),
    State("wt-channel", "value"),
    State("wt-avg", "value"),
    State("wt-signal", "value"),
)
def select_row(click_data, data_file, result_file, wt_channel, wt_avg, wt_signal):
    if not click_data or not data_file:
        return None, "Click a candle or chart point to prepare an annotation."
    try:
        clicked_time = click_data["points"][0].get("x")
        df, result, _ = prepare_frame(data_file, result_file, int(wt_channel or 10), int(wt_avg or 21), int(wt_signal or 4))
        row = nearest_row(df, clicked_time)
        if row is None:
            return None, "Could not match click to a candle."
        symbol, timeframe = infer_symbol_tf(data_file, result)
        row_data = row.to_dict()
        payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "time": pd.Timestamp(row["time"]).isoformat(),
            "price": float(row["close"]),
            "row": {k: (v.isoformat() if isinstance(v, pd.Timestamp) else v) for k, v in row_data.items()},
        }
        return payload, [
            html.Div(f"Selected: {payload['time']} | {symbol} {timeframe}"),
            html.Div(f"Close: {payload['price']:.6f} | WT1: {row.get('wt1', float('nan')):.2f} | WT2: {row.get('wt2', float('nan')):.2f}", style={"color": COLORS["muted"]}),
        ]
    except Exception as exc:
        return None, f"Selection error: {exc}"


@app.callback(
    Output("store-annotations", "data"),
    Output("annotation-comment", "value"),
    Input("add-annotation", "n_clicks"),
    State("store-selected-row", "data"),
    State("store-annotations", "data"),
    State("data-file", "value"),
    State("result-file", "value"),
    State("annotation-label", "value"),
    State("annotation-comment", "value"),
    State("wt-channel", "value"),
    State("wt-avg", "value"),
    State("wt-signal", "value"),
    prevent_initial_call=True,
)
def add_annotation(_, selected, annotations, data_file, result_file, label, comment, wt_channel, wt_avg, wt_signal):
    if not selected or not data_file:
        return no_update, no_update
    df, result, _ = prepare_frame(data_file, result_file, int(wt_channel or 10), int(wt_avg or 21), int(wt_signal or 4))
    row = nearest_row(df, selected["time"])
    if row is None:
        return no_update, no_update
    symbol, timeframe = infer_symbol_tf(data_file, result)
    item = build_annotation(
        source_file=data_file,
        result_file=result_file,
        symbol=symbol,
        timeframe=timeframe,
        label=label or "observation",
        comment=comment or "",
        row=row,
        price=float(selected["price"]),
        indicator_params={
            "wavetrend": {
                "channel_len": int(wt_channel or 10),
                "avg_len": int(wt_avg or 21),
                "signal_len": int(wt_signal or 4),
            }
        },
    )
    return [*(annotations or []), item], ""


@app.callback(
    Output("annotations-table", "data"),
    Input("store-annotations", "data"),
)
def update_annotations_table(annotations):
    rows = []
    for item in annotations or []:
        rows.append({
            "time": item.get("time"),
            "label": item.get("label"),
            "price": round(float(item.get("price", 0.0)), 6),
            "comment": item.get("comment", ""),
        })
    return rows


@app.callback(
    Output("status", "children"),
    Input("save-annotations", "n_clicks"),
    State("store-annotations", "data"),
    State("data-file", "value"),
    prevent_initial_call=True,
)
def save_current_annotations(_, annotations, data_file):
    if not annotations:
        return "No annotations to save."
    json_path, csv_path = save_annotations(ANNOTATIONS_DIR, data_file or "annotations", annotations)
    return f"Saved: {json_path.name} and {csv_path.name}"


def main() -> None:
    host = os.getenv("CHART_INSPECTOR_HOST", "0.0.0.0")
    port = int(os.getenv("CHART_INSPECTOR_PORT", "8070"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
