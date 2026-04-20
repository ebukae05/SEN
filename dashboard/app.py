"""
dashboard/app.py — Plotly Dash fleet monitoring dashboard for SEN.

Tabs:
    Fleet Overview  — Bar chart of predicted RUL for all 100 engines, coloured by severity.
    Engine Detail   — RUL timeline and sensor trends for a selected engine.
    AI Analysis     — Gemini-powered plain-English engine health analysis and recommendation.

Run with:
    python dashboard/app.py
"""

import logging
import os
import sys
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)

_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"

# ── Design tokens ─────────────────────────────────────────────────────────────
_BG        = "#060b18"
_BG_CARD   = "rgba(13,27,46,0.85)"
_BG_PANEL  = "#0d1b2e"
_BORDER    = "rgba(0,212,255,0.15)"
_ACCENT    = "#00d4ff"
_TEXT      = "#e8f4f8"
_TEXT_DIM  = "#7b9bb5"

_SEVERITY_COLOR = {
    "NORMAL":   "#00ff88",
    "CAUTION":  "#ffd60a",
    "WARNING":  "#ff8c00",
    "CRITICAL": "#ff2d55",
}


def _load_config() -> dict:
    with _CONFIG_PATH.open("r") as fh:
        return yaml.safe_load(fh)


def _clean_csv_path() -> Path:
    cfg = _load_config()
    return _PROJECT_ROOT / cfg["data"]["processed_dir"] / "train_clean.csv"


def _severity(rul: float, threshold: int) -> str:
    if rul < threshold * 0.40:
        return "CRITICAL"
    if rul < threshold * 0.70:
        return "WARNING"
    if rul < threshold:
        return "CAUTION"
    return "NORMAL"


# ── Fleet snapshot ────────────────────────────────────────────────────────────

def _compute_fleet_rul(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    threshold = cfg["monitor"]["rul_alert_threshold"]
    records   = []
    for eid in sorted(df["unit_id"].unique()):
        edf = df[df["unit_id"] == eid].sort_values("cycle")
        idx = int(len(edf) * 0.75)
        rul = float(edf.iloc[idx]["RUL"])
        sev = _severity(rul, threshold)
        records.append({"engine_id": int(eid), "predicted_rul": round(rul, 2), "severity": sev})
    return pd.DataFrame(records)


logger.info("Loading clean dataset...")
cfg           = _load_config()
_clean_df     = pd.read_csv(_clean_csv_path())
logger.info("Computing fleet snapshot...")
_fleet_df     = _compute_fleet_rul(_clean_df, cfg)
_keep_sensors = cfg["data"]["keep_sensors"]
logger.info("Fleet data ready — %d engines.", len(_fleet_df))


# ── Gemini analysis ───────────────────────────────────────────────────────────

def _gemini_engine_analysis(engine_id: int) -> str:
    from scipy.stats import linregress
    from tools.stream_tools import stream_sensors
    from tools.predict_tools import predict_rul

    edf       = _clean_df[_clean_df["unit_id"] == engine_id].sort_values("cycle")
    threshold = cfg["monitor"]["rul_alert_threshold"]
    seq_len   = cfg["model"]["sequence_length"]

    windows       = list(stream_sensors(_clean_df, engine_id=engine_id, window_size=seq_len))
    predicted_rul = predict_rul(windows[-1]) if windows else float(edf["RUL"].iloc[-1])
    severity      = _severity(predicted_rul, threshold)

    slopes = {}
    for s in _keep_sensors:
        if s in edf.columns:
            slope, *_ = linregress(edf["cycle"], edf[s])
            slopes[s] = slope
    top3     = sorted(slopes, key=lambda s: slopes[s])[:3]
    top3_str = ", ".join(f"{s} (slope {slopes[s]:.5f})" for s in top3)

    idx          = int(len(edf) * 0.75)
    engine_rul75 = float(edf.iloc[idx]["RUL"])
    fleet_avg    = _fleet_df["predicted_rul"].mean()
    total_cycles = int(edf["cycle"].max())

    prompt = f"""You are a turbofan engine maintenance expert analyzing NASA CMAPSS sensor data.

Engine {engine_id} diagnostics:
- Total cycles observed: {total_cycles}
- CNN-LSTM predicted RUL (current): {predicted_rul:.1f} cycles
- Alert severity: {severity}
- Top 3 fastest-declining sensors: {top3_str}
- RUL at 75% lifecycle mark: {engine_rul75} cycles
- Fleet average RUL at 75% mark: {fleet_avg:.1f} cycles
- Alert threshold: {threshold} cycles

Write a concise 4-6 sentence analysis for a maintenance technician covering:
1. How many cycles this engine likely has left and confidence level.
2. Which sensors are the main concern and what they indicate physically.
3. How this engine compares to the fleet.
4. A clear recommendation: replace immediately, schedule maintenance, or continue monitoring — with a specific cycle window if applicable.

Be direct and practical. No bullet points — write in plain paragraphs."""

    from google import genai
    client   = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text.strip()


# ── App ───────────────────────────────────────────────────────────────────────

app = dash.Dash(
    __name__,
    title="SEN — Engine Health Monitor",
    suppress_callback_exceptions=True,
)

_TAB_STYLE = {
    "fontFamily": "Inter, sans-serif",
    "fontSize": "0.85rem",
    "fontWeight": "500",
    "color": _TEXT_DIM,
    "backgroundColor": _BG_PANEL,
    "border": "none",
    "borderBottom": f"1px solid {_BORDER}",
    "padding": "12px 24px",
    "letterSpacing": "0.03em",
}
_TAB_SELECTED = {
    **_TAB_STYLE,
    "color": _ACCENT,
    "backgroundColor": "rgba(0,212,255,0.06)",
    "borderTop": f"2px solid {_ACCENT}",
    "borderBottom": "none",
}

app.layout = html.Div(
    style={"backgroundColor": _BG, "minHeight": "100vh", "padding": "28px 32px"},
    children=[

        # ── Header ────────────────────────────────────────────────────────────
        html.Div(
            style={"marginBottom": "28px"},
            children=[
                html.Div(
                    style={"display": "flex", "alignItems": "center", "gap": "14px", "marginBottom": "6px"},
                    children=[
                        html.Div(style={
                            "width": "10px", "height": "10px", "borderRadius": "50%",
                            "backgroundColor": _ACCENT,
                            "boxShadow": f"0 0 12px {_ACCENT}, 0 0 24px rgba(0,212,255,0.4)",
                        }),
                        html.H1("SEN", style={
                            "fontFamily": "Space Grotesk, sans-serif",
                            "fontSize": "1.6rem", "fontWeight": "700",
                            "background": f"linear-gradient(90deg, {_ACCENT}, #a78bfa)",
                            "WebkitBackgroundClip": "text",
                            "WebkitTextFillColor": "transparent",
                            "margin": 0,
                        }),
                        html.Span("Sensor Engine Network", style={
                            "color": _TEXT_DIM, "fontSize": "0.9rem",
                            "fontWeight": "400", "letterSpacing": "0.05em",
                        }),
                    ],
                ),
                html.P(
                    "Real-time turbofan health monitoring · NASA CMAPSS FD001 · CNN-LSTM + Gemini AI",
                    style={"color": _TEXT_DIM, "fontSize": "0.78rem", "letterSpacing": "0.04em"},
                ),
            ],
        ),

        # ── Summary cards ─────────────────────────────────────────────────────
        html.Div(id="summary-cards", style={"display": "flex", "gap": "12px", "marginBottom": "24px"}),

        # ── Tabs ──────────────────────────────────────────────────────────────
        dcc.Tabs(
            id="tabs",
            value="fleet",
            style={"borderBottom": f"1px solid {_BORDER}"},
            colors={"border": "transparent", "primary": _ACCENT, "background": _BG_PANEL},
            children=[
                dcc.Tab(label="Fleet Overview", value="fleet",
                        style=_TAB_STYLE, selected_style=_TAB_SELECTED),
                dcc.Tab(label="Engine Detail",  value="detail",
                        style=_TAB_STYLE, selected_style=_TAB_SELECTED),
                dcc.Tab(label="AI Analysis",    value="chatbot",
                        style=_TAB_STYLE, selected_style=_TAB_SELECTED),
            ],
        ),

        html.Div(id="tab-content", style={"marginTop": "20px"}),
    ],
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _glass_card(children, border_color=_BORDER, padding="16px 20px", extra_style=None):
    style = {
        "backgroundColor": _BG_CARD,
        "border": f"1px solid {border_color}",
        "borderRadius": "12px",
        "padding": padding,
        "backdropFilter": "blur(12px)",
        **(extra_style or {}),
    }
    return html.Div(style=style, children=children)


def _engine_dropdown(dropdown_id: str, value=None):
    engine_ids = sorted(_fleet_df["engine_id"].tolist())
    return dcc.Dropdown(
        id=dropdown_id,
        options=[{"label": f"Engine {e}", "value": e} for e in engine_ids],
        value=value or engine_ids[0],
        clearable=False,
        style={
            "width": "180px",
            "backgroundColor": _BG_PANEL,
            "color": _TEXT,
            "border": f"1px solid {_BORDER}",
            "borderRadius": "8px",
            "fontSize": "0.85rem",
        },
    )


def _chart_layout(title: str, xaxis_title: str, yaxis_title: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=13, color=_TEXT, family="Inter")),
        xaxis_title=xaxis_title,
        yaxis_title=yaxis_title,
        plot_bgcolor=_BG_PANEL,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=_TEXT_DIM, family="Inter", size=11),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor=_BORDER, showline=True),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", linecolor=_BORDER, showline=True),
        margin=dict(t=44, b=44, l=56, r=16),
        legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=_BORDER, borderwidth=1),
    )


# ── Callbacks ─────────────────────────────────────────────────────────────────

@app.callback(Output("summary-cards", "children"), Input("tabs", "value"))
def update_summary_cards(_):
    counts = _fleet_df["severity"].value_counts()
    cards  = []
    for label, color, key in [
        ("Total Engines", _ACCENT,      None),
        ("CRITICAL",      "#ff2d55",    "CRITICAL"),
        ("WARNING",       "#ff8c00",    "WARNING"),
        ("CAUTION",       "#ffd60a",    "CAUTION"),
        ("NORMAL",        "#00ff88",    "NORMAL"),
    ]:
        value = len(_fleet_df) if key is None else int(counts.get(key, 0))
        cards.append(html.Div(
            style={
                "backgroundColor": _BG_CARD,
                "border": f"1px solid {color}22",
                "borderRadius": "12px",
                "padding": "14px 22px",
                "textAlign": "center",
                "minWidth": "120px",
                "backdropFilter": "blur(12px)",
                "boxShadow": f"0 0 16px {color}18",
            },
            children=[
                html.Div(str(value), style={
                    "fontSize": "2rem", "fontWeight": "700",
                    "color": color, "fontFamily": "Space Grotesk, sans-serif",
                    "lineHeight": "1",
                }),
                html.Div(label, style={
                    "color": _TEXT_DIM, "fontSize": "0.72rem",
                    "letterSpacing": "0.08em", "marginTop": "4px",
                    "textTransform": "uppercase",
                }),
            ],
        ))
    return cards


@app.callback(Output("tab-content", "children"), Input("tabs", "value"))
def render_tab(tab: str):
    if tab == "fleet":   return _fleet_tab()
    if tab == "detail":  return _detail_tab()
    return _chatbot_tab()


# ── Fleet tab ─────────────────────────────────────────────────────────────────

def _fleet_tab():
    fig = go.Figure(go.Bar(
        x=_fleet_df["engine_id"],
        y=_fleet_df["predicted_rul"],
        marker=dict(
            color=[_SEVERITY_COLOR[s] for s in _fleet_df["severity"]],
            opacity=0.85,
            line=dict(width=0),
        ),
        hovertemplate="<b>Engine %{x}</b><br>RUL: %{y} cycles<extra></extra>",
    ))
    fig.update_layout(
        **_chart_layout("Predicted RUL — All 100 Engines", "Engine ID", "RUL (cycles)"),
        xaxis=dict(tickmode="linear", dtick=5,
                   gridcolor="rgba(255,255,255,0.05)", linecolor=_BORDER),
        bargap=0.2,
    )
    return _glass_card(dcc.Graph(figure=fig, style={"height": "480px"},
                                 config={"displayModeBar": False}))


# ── Detail tab ────────────────────────────────────────────────────────────────

def _detail_tab():
    return html.Div([
        html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "16px"},
            children=[
                html.Span("Engine", style={"color": _TEXT_DIM, "fontSize": "0.85rem"}),
                _engine_dropdown("engine-dropdown"),
            ],
        ),
        html.Div(id="engine-status-card", style={"marginBottom": "16px"}),
        _glass_card(dcc.Graph(id="rul-timeline", style={"height": "300px"},
                              config={"displayModeBar": False}),
                    extra_style={"marginBottom": "12px"}),
        _glass_card(dcc.Graph(id="sensor-trends", style={"height": "300px"},
                              config={"displayModeBar": False})),
    ])


@app.callback(
    Output("engine-status-card", "children"),
    Output("rul-timeline", "figure"),
    Output("sensor-trends", "figure"),
    Input("engine-dropdown", "value"),
)
def update_engine_detail(engine_id: int):
    from scipy.stats import linregress

    row   = _fleet_df[_fleet_df["engine_id"] == engine_id].iloc[0]
    edf   = _clean_df[_clean_df["unit_id"] == engine_id].sort_values("cycle")
    sev   = row["severity"]
    rul   = row["predicted_rul"]
    color = _SEVERITY_COLOR[sev]

    stat_card = _glass_card(
        border_color=f"{color}55",
        padding="14px 24px",
        extra_style={"display": "inline-flex", "gap": "36px",
                     "boxShadow": f"0 0 20px {color}22", "marginBottom": "16px"},
        children=[
            html.Div([
                html.Div("RUL at 75% lifecycle", style={"color": _TEXT_DIM, "fontSize": "0.72rem",
                                                         "textTransform": "uppercase", "letterSpacing": "0.06em"}),
                html.Div(f"{rul} cycles", style={"color": color, "fontSize": "1.5rem",
                                                  "fontWeight": "700", "fontFamily": "Space Grotesk, sans-serif"}),
            ]),
            html.Div([
                html.Div("Severity", style={"color": _TEXT_DIM, "fontSize": "0.72rem",
                                            "textTransform": "uppercase", "letterSpacing": "0.06em"}),
                html.Div(sev, style={"color": color, "fontSize": "1.5rem",
                                     "fontWeight": "700", "fontFamily": "Space Grotesk, sans-serif"}),
            ]),
            html.Div([
                html.Div("Total cycles", style={"color": _TEXT_DIM, "fontSize": "0.72rem",
                                                "textTransform": "uppercase", "letterSpacing": "0.06em"}),
                html.Div(str(len(edf)), style={"color": _TEXT, "fontSize": "1.5rem",
                                               "fontWeight": "700", "fontFamily": "Space Grotesk, sans-serif"}),
            ]),
        ],
    )

    rul_fig = go.Figure(go.Scatter(
        x=edf["cycle"], y=edf["RUL"], mode="lines",
        line=dict(color=_ACCENT, width=2),
        fill="tozeroy", fillcolor="rgba(0,212,255,0.06)",
        hovertemplate="Cycle %{x}<br>RUL: %{y}<extra></extra>",
    ))
    rul_fig.update_layout(**_chart_layout(f"Engine {engine_id} — RUL Timeline", "Cycle", "RUL (cycles)"))

    slopes = {}
    for s in _keep_sensors:
        if s in edf.columns:
            slope, *_ = linregress(edf["cycle"], edf[s])
            slopes[s] = slope
    top3    = sorted(slopes, key=lambda s: slopes[s])[:3]
    palette = ["#ff2d55", "#ffd60a", "#a78bfa"]

    sensor_fig = go.Figure()
    for sensor, clr in zip(top3, palette):
        sensor_fig.add_trace(go.Scatter(
            x=edf["cycle"], y=edf[sensor], mode="lines", name=sensor,
            line=dict(color=clr, width=2),
            hovertemplate=f"{sensor}: %{{y:.4f}}<extra></extra>",
        ))
    sensor_fig.update_layout(**_chart_layout(
        f"Engine {engine_id} — Top 3 Declining Sensors", "Cycle", "Normalised Value"))

    return stat_card, rul_fig, sensor_fig


# ── Chatbot tab ───────────────────────────────────────────────────────────────

def _chatbot_tab():
    return html.Div([
        html.Div(
            style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "20px"},
            children=[
                html.Span("Engine", style={"color": _TEXT_DIM, "fontSize": "0.85rem"}),
                _engine_dropdown("chat-engine-dropdown"),
                html.Button(
                    "Analyze Engine",
                    id="analyze-btn",
                    n_clicks=0,
                    style={
                        "background": f"linear-gradient(135deg, {_ACCENT}, #7c3aed)",
                        "color": "#fff", "border": "none",
                        "borderRadius": "8px", "padding": "9px 22px",
                        "cursor": "pointer", "fontWeight": "600",
                        "fontSize": "0.85rem", "fontFamily": "Inter, sans-serif",
                        "letterSpacing": "0.03em",
                        "boxShadow": f"0 0 16px rgba(0,212,255,0.3)",
                    },
                ),
            ],
        ),
        dcc.Loading(
            type="circle", color=_ACCENT,
            children=html.Div(id="chat-output"),
        ),
    ])


@app.callback(
    Output("chat-output", "children"),
    Input("analyze-btn", "n_clicks"),
    State("chat-engine-dropdown", "value"),
    prevent_initial_call=True,
)
def run_chat_analysis(n_clicks: int, engine_id: int):
    try:
        analysis = _gemini_engine_analysis(engine_id)
        row      = _fleet_df[_fleet_df["engine_id"] == engine_id].iloc[0]
        sev      = row["severity"]
        color    = _SEVERITY_COLOR[sev]

        return html.Div([
            # Engine badge row
            html.Div(
                style={
                    "display": "flex", "alignItems": "center", "gap": "10px",
                    "marginBottom": "12px",
                },
                children=[
                    html.Span(f"Engine {engine_id}", style={
                        "fontFamily": "Space Grotesk, sans-serif",
                        "fontSize": "1rem", "fontWeight": "600", "color": _TEXT,
                    }),
                    html.Span(sev, style={
                        "color": color, "fontSize": "0.72rem", "fontWeight": "600",
                        "border": f"1px solid {color}",
                        "borderRadius": "20px", "padding": "2px 10px",
                        "letterSpacing": "0.06em", "textTransform": "uppercase",
                        "boxShadow": f"0 0 8px {color}44",
                    }),
                    html.Span(f"{row['predicted_rul']} cycles remaining", style={
                        "color": _TEXT_DIM, "fontSize": "0.8rem",
                    }),
                ],
            ),
            # Analysis body
            _glass_card(
                border_color=f"{color}33",
                padding="20px 24px",
                extra_style={"boxShadow": f"0 0 24px {color}18"},
                children=html.P(analysis, style={
                    "color": _TEXT, "lineHeight": "1.8", "fontSize": "0.92rem",
                    "whiteSpace": "pre-wrap", "margin": 0,
                }),
            ),
        ])
    except Exception as exc:
        logger.exception("Chat analysis failed for engine %d", engine_id)
        return _glass_card(
            border_color="#ff2d5555",
            children=html.P(f"Analysis failed: {exc}",
                            style={"color": "#ff2d55", "margin": 0, "fontSize": "0.85rem"}),
        )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cfg_dash = _load_config()["dashboard"]
    app.run(
        host=cfg_dash["host"],
        port=cfg_dash["port"],
        debug=cfg_dash["debug"],
    )
