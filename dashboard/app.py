"""
dashboard/app.py — Plotly Dash fleet monitoring dashboard for SEN.

Tabs:
    Fleet Overview  — Bar chart of predicted RUL for all 100 engines, coloured by severity.
    Engine Detail   — RUL timeline and sensor trends for a selected engine.

Run with:
    python dashboard/app.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def _load_config() -> dict:
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _clean_csv_path() -> Path:
    cfg = _load_config()
    return _PROJECT_ROOT / cfg["data"]["processed_dir"] / "train_clean.csv"


# ── Severity helpers ──────────────────────────────────────────────────────────

_SEVERITY_COLOR = {
    "NORMAL":   "#2ecc71",
    "CAUTION":  "#f1c40f",
    "WARNING":  "#e67e22",
    "CRITICAL": "#e74c3c",
}


def _severity(rul: float, threshold: int) -> str:
    if rul < threshold * 0.40:
        return "CRITICAL"
    if rul < threshold * 0.70:
        return "WARNING"
    if rul < threshold:
        return "CAUTION"
    return "NORMAL"


# ── Fleet RUL computation (runs once at startup) ──────────────────────────────

def _compute_fleet_rul(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Predict the latest RUL for every engine using the CNN-LSTM model."""
    from tools.stream_tools import stream_sensors
    from tools.predict_tools import predict_rul

    seq_len   = cfg["model"]["sequence_length"]
    threshold = cfg["monitor"]["rul_alert_threshold"]
    records   = []

    for eid in sorted(df["unit_id"].unique()):
        windows = list(stream_sensors(df, engine_id=int(eid), window_size=seq_len))
        if not windows:
            continue
        rul = predict_rul(windows[-1])
        sev = _severity(rul, threshold)
        records.append({"engine_id": int(eid), "predicted_rul": round(rul, 2), "severity": sev})

    return pd.DataFrame(records)


logger.info("Loading clean dataset...")
cfg        = _load_config()
_clean_df  = pd.read_csv(_clean_csv_path())
logger.info("Computing fleet RUL predictions for %d engines...", _clean_df["unit_id"].nunique())
_fleet_df  = _compute_fleet_rul(_clean_df, cfg)
_keep_sensors = cfg["data"]["keep_sensors"]
logger.info("Fleet data ready.")


# ── App layout ────────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="SEN — Engine Health Monitor")

app.layout = html.Div(
    style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#1a1a2e", "minHeight": "100vh", "padding": "20px"},
    children=[
        # Header
        html.Div(
            style={"textAlign": "center", "marginBottom": "24px"},
            children=[
                html.H1("SEN — Sensor Engine Network", style={"color": "#e0e0e0", "margin": 0}),
                html.P("Real-time turbofan engine health monitoring", style={"color": "#888", "margin": "4px 0 0"}),
            ],
        ),

        # Summary cards
        html.Div(
            id="summary-cards",
            style={"display": "flex", "gap": "16px", "marginBottom": "24px", "justifyContent": "center"},
        ),

        # Tabs
        dcc.Tabs(
            id="tabs",
            value="fleet",
            colors={"border": "#444", "primary": "#e74c3c", "background": "#16213e"},
            children=[
                dcc.Tab(label="Fleet Overview", value="fleet",
                        style={"color": "#aaa", "backgroundColor": "#16213e"},
                        selected_style={"color": "#fff", "backgroundColor": "#0f3460"}),
                dcc.Tab(label="Engine Detail", value="detail",
                        style={"color": "#aaa", "backgroundColor": "#16213e"},
                        selected_style={"color": "#fff", "backgroundColor": "#0f3460"}),
            ],
        ),

        html.Div(id="tab-content", style={"marginTop": "16px"}),
    ],
)


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(Output("summary-cards", "children"), Input("tabs", "value"))
def update_summary_cards(_tab):
    counts = _fleet_df["severity"].value_counts()
    cards  = []
    for label, color, key in [
        ("Total Engines", "#3498db", None),
        ("CRITICAL",      "#e74c3c", "CRITICAL"),
        ("WARNING",       "#e67e22", "WARNING"),
        ("CAUTION",       "#f1c40f", "CAUTION"),
        ("NORMAL",        "#2ecc71", "NORMAL"),
    ]:
        value = len(_fleet_df) if key is None else int(counts.get(key, 0))
        cards.append(
            html.Div(
                style={
                    "backgroundColor": "#16213e", "border": f"2px solid {color}",
                    "borderRadius": "8px", "padding": "12px 24px", "textAlign": "center",
                    "minWidth": "120px",
                },
                children=[
                    html.Div(str(value), style={"fontSize": "2rem", "fontWeight": "bold", "color": color}),
                    html.Div(label, style={"color": "#aaa", "fontSize": "0.85rem"}),
                ],
            )
        )
    return cards


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab: str):
    if tab == "fleet":
        return _fleet_tab()
    return _detail_tab()


def _fleet_tab():
    fig = go.Figure(
        go.Bar(
            x=_fleet_df["engine_id"],
            y=_fleet_df["predicted_rul"],
            marker_color=[_SEVERITY_COLOR[s] for s in _fleet_df["severity"]],
            hovertemplate="Engine %{x}<br>RUL: %{y} cycles<extra></extra>",
        )
    )
    fig.update_layout(
        title="Predicted RUL — All Engines",
        xaxis_title="Engine ID",
        yaxis_title="Predicted RUL (cycles)",
        plot_bgcolor="#16213e",
        paper_bgcolor="#1a1a2e",
        font_color="#e0e0e0",
        xaxis=dict(tickmode="linear", dtick=5, gridcolor="#333"),
        yaxis=dict(gridcolor="#333"),
        margin=dict(t=50, b=50, l=60, r=20),
    )
    return dcc.Graph(figure=fig, style={"height": "500px"})


def _detail_tab():
    engine_ids = sorted(_fleet_df["engine_id"].tolist())
    return html.Div([
        html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "16px", "marginBottom": "16px"},
            children=[
                html.Label("Select Engine:", style={"color": "#e0e0e0", "fontWeight": "bold"}),
                dcc.Dropdown(
                    id="engine-dropdown",
                    options=[{"label": f"Engine {e}", "value": e} for e in engine_ids],
                    value=engine_ids[0],
                    style={"width": "200px", "color": "#000"},
                    clearable=False,
                ),
            ],
        ),
        html.Div(id="engine-status-card", style={"marginBottom": "16px"}),
        dcc.Graph(id="rul-timeline",  style={"marginBottom": "16px"}),
        dcc.Graph(id="sensor-trends"),
    ])


@app.callback(
    Output("engine-status-card", "children"),
    Output("rul-timeline", "figure"),
    Output("sensor-trends", "figure"),
    Input("engine-dropdown", "value"),
)
def update_engine_detail(engine_id: int):
    row  = _fleet_df[_fleet_df["engine_id"] == engine_id].iloc[0]
    edf  = _clean_df[_clean_df["unit_id"] == engine_id].sort_values("cycle")
    sev  = row["severity"]
    rul  = row["predicted_rul"]
    color = _SEVERITY_COLOR[sev]

    # Status card
    status_card = html.Div(
        style={
            "backgroundColor": "#16213e", "border": f"2px solid {color}",
            "borderRadius": "8px", "padding": "12px 20px",
            "display": "inline-flex", "gap": "32px",
        },
        children=[
            html.Div([
                html.Div("Predicted RUL", style={"color": "#888", "fontSize": "0.8rem"}),
                html.Div(f"{rul} cycles", style={"color": color, "fontSize": "1.4rem", "fontWeight": "bold"}),
            ]),
            html.Div([
                html.Div("Severity", style={"color": "#888", "fontSize": "0.8rem"}),
                html.Div(sev, style={"color": color, "fontSize": "1.4rem", "fontWeight": "bold"}),
            ]),
            html.Div([
                html.Div("Cycles in dataset", style={"color": "#888", "fontSize": "0.8rem"}),
                html.Div(str(len(edf)), style={"color": "#e0e0e0", "fontSize": "1.4rem", "fontWeight": "bold"}),
            ]),
        ],
    )

    # RUL timeline
    rul_fig = go.Figure(
        go.Scatter(
            x=edf["cycle"], y=edf["rul"],
            mode="lines", line=dict(color="#3498db", width=2),
            hovertemplate="Cycle %{x}<br>RUL: %{y}<extra></extra>",
        )
    )
    rul_fig.update_layout(
        title=f"Engine {engine_id} — RUL Timeline",
        xaxis_title="Cycle", yaxis_title="RUL (cycles)",
        plot_bgcolor="#16213e", paper_bgcolor="#1a1a2e", font_color="#e0e0e0",
        xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
        margin=dict(t=50, b=50, l=60, r=20),
    )

    # Sensor trends (top 3 declining by slope)
    from scipy.stats import linregress
    slopes = {}
    for s in _keep_sensors:
        if s in edf.columns:
            slope, *_ = linregress(edf["cycle"], edf[s])
            slopes[s] = slope
    top3 = sorted(slopes, key=lambda s: slopes[s])[:3]

    sensor_fig = go.Figure()
    palette = ["#e74c3c", "#f1c40f", "#3498db"]
    for sensor, clr in zip(top3, palette):
        sensor_fig.add_trace(go.Scatter(
            x=edf["cycle"], y=edf[sensor],
            mode="lines", name=sensor, line=dict(color=clr, width=2),
            hovertemplate=f"{sensor}: %{{y:.4f}}<extra></extra>",
        ))
    sensor_fig.update_layout(
        title=f"Engine {engine_id} — Top 3 Declining Sensors",
        xaxis_title="Cycle", yaxis_title="Normalised Value",
        plot_bgcolor="#16213e", paper_bgcolor="#1a1a2e", font_color="#e0e0e0",
        legend=dict(bgcolor="#16213e", bordercolor="#444"),
        xaxis=dict(gridcolor="#333"), yaxis=dict(gridcolor="#333"),
        margin=dict(t=50, b=50, l=60, r=20),
    )

    return status_card, rul_fig, sensor_fig


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cfg_dash = _load_config()["dashboard"]
    app.run(
        host=cfg_dash["host"],
        port=cfg_dash["port"],
        debug=cfg_dash["debug"],
    )
