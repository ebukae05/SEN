# SEN — Sensor Engine Network

Real-time predictive maintenance platform for rotating machinery. SEN ingests
time-series sensor data, predicts Remaining Useful Life (RUL) with a CNN-LSTM,
runs a CrewAI multi-agent diagnostic pipeline, and generates maintenance
recommendations plus PDF reports — all behind a FastAPI backend.

**Live API:** [`https://sen-production.up.railway.app`](https://sen-production.up.railway.app)
**Interactive docs:** [`/docs`](https://sen-production.up.railway.app/docs)

---

## What it does

1. Accepts raw sensor data in CSV, JSON, or Excel format through a CDH
   (Command & Data Handling) layer modeled on spacecraft data systems
2. Deterministic preprocessing — drops constant sensors, normalizes with
   MinMaxScaler, generates piecewise-linear RUL labels
3. Predicts RUL per engine using a per-dataset CNN-LSTM trained on NASA
   CMAPSS turbofan degradation data (FD001–FD004)
4. Three-agent CrewAI pipeline investigates flagged engines:
   - **MonitorAgent** — streams sensor windows, predicts RUL, raises alerts
   - **DiagnosticAgent** — compares to fleet, ranks declining sensors,
     measures degradation rate
   - **MaintenanceAdvisorAgent** — estimates time-to-critical, asks Gemini
     for a recommendation, generates a PDF report
5. Exposes everything over a REST API consumable from any frontend

Although the demo runs on aircraft turbofan data, the CDH layer's schema
adapter makes SEN sensor-agnostic — wind turbines, pumps, naval engines,
manufacturing equipment all fit the same pipeline with retraining.

---

## Architecture

```
Raw sensor data (CSV / JSON / Excel)
        |
        v
   CDH Layer  (validate, prioritize, normalize format)
        |
        v
   preprocess.py  (clean, scale, label — deterministic)
        |
        v
+-------------------------------------------------+
|       3-Agent Sequential CrewAI Pipeline         |
|                                                  |
|  MonitorAgent  ->  DiagnosticAgent  ->  Advisor  |
|     (PyTorch)        (SciPy/Pandas)    (Gemini)  |
+-------------------------------------------------+
        |
        v
   FastAPI  (Railway)
        |
        +--> JSON responses
        +--> PDF maintenance reports
        +--> Frontend dashboard (v0.dev / Next.js)
```

### CNN-LSTM model

```
Input (30 cycles x 14 sensors)
  -> Conv1D(64, kernel=3, ReLU)
  -> Conv1D(64, kernel=3, ReLU)
  -> MaxPooling1D(2)
  -> LSTM(50, return_sequences=True)
  -> Dropout(0.3)
  -> LSTM(50)
  -> Dropout(0.3)
  -> Dense(1) -> Predicted RUL
```

One model per dataset (FD001–FD004). MSE loss, Adam (lr=0.001), 50 epochs,
batch size 32, RUL capped at 130 cycles (piecewise linear labeling).

---

## Stack

| Layer              | Technology                                    |
|--------------------|-----------------------------------------------|
| Agent orchestration| CrewAI (sequential process, context chaining) |
| LLM                | Google Gemini 2.5 Flash (langchain-google-genai) |
| Deep learning      | PyTorch (CPU build for deploy)                |
| REST API           | FastAPI + Uvicorn                             |
| Data               | Pandas, NumPy, scikit-learn, SciPy            |
| Reports            | ReportLab (PDF)                               |
| Config / secrets   | YAML + python-dotenv                          |
| Testing            | Pytest                                        |
| Container          | Docker + Docker Compose                       |
| Hosting            | Railway                                       |
| Dataset            | NASA CMAPSS FD001–FD004                       |

---

## API

All endpoints live at `https://sen-production.up.railway.app`.

| Method | Endpoint                    | Description                                      |
|--------|-----------------------------|--------------------------------------------------|
| GET    | `/`                         | Service info + endpoint index                    |
| GET    | `/health`                   | Liveness probe                                   |
| GET    | `/engines`                  | List of engine IDs in the active dataset         |
| GET    | `/engine/{engine_id}/status`| Latest RUL prediction + severity + alert state   |
| POST   | `/analyze`                  | Run the full 3-agent crew on one engine          |

`POST /analyze` body:

```json
{ "engine_id": 1 }
```

`POST /analyze` response (truncated):

```json
{
  "engine_id": 1,
  "result": "MonitorAgent: engine 1 RUL = 4.24 cycles, CRITICAL...\nDiagnosticAgent: ..."
}
```

Expect ~30–60 seconds — it kicks off a sequential CrewAI pipeline with three
LLM calls. Interactive Swagger UI at [`/docs`](https://sen-production.up.railway.app/docs)
lets you try every endpoint from the browser.

---

## Datasets

NASA CMAPSS turbofan engine degradation simulation — 4 sub-datasets:

| Dataset | Engines | Operating conditions | Fault modes              |
|---------|---------|----------------------|--------------------------|
| FD001   | 100     | 1 (sea level)        | HPC degradation          |
| FD002   | 260     | 6                    | HPC degradation          |
| FD003   | 100     | 1 (sea level)        | HPC + fan degradation    |
| FD004   | 249     | 6                    | HPC + fan degradation    |

All four share the same 21 sensor columns. Constant sensors are detected
dynamically per dataset — 14 sensors are kept after dropping near-constants.

Source: [NASA Prognostics Center of Excellence](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)

---

## Project structure

```
SEN/
├── config.yaml              # All configurable values
├── Dockerfile               # Single-stage CPU image for Railway
├── docker-compose.yml       # Local one-command run
├── requirements.txt
├── preprocess.py            # Deterministic preprocessing
│
├── cdh/handler.py           # Command & Data Handling layer
├── tools/                   # Agent-callable Python functions
│   ├── stream_tools.py
│   ├── predict_tools.py
│   ├── diagnostic_tools.py
│   └── advisor_tools.py
├── agents/                  # CrewAI agent definitions
│   ├── monitor.py
│   ├── diagnostician.py
│   └── advisor.py
├── crews/maintenance_crew.py
├── models/
│   ├── cnn_lstm.py          # Model architecture
│   ├── train.py             # Training script
│   └── saved/               # Trained .pt weights (one per dataset)
├── api/main.py              # FastAPI app
│
├── data/raw/                # CMAPSS FD001–FD004 raw files
├── data/processed/          # Cleaned CSVs + scalers (generated)
├── outputs/reports/         # Generated PDF reports
└── tests/                   # Phase verification suite
```

---

## Quickstart (Docker)

Requires [Docker](https://docs.docker.com/get-docker/) and a free
[Gemini API key](https://aistudio.google.com/app/apikey).

```bash
git clone https://github.com/ebukae05/SEN.git
cd SEN
echo "GOOGLE_API_KEY=your_key_here" > .env
docker compose up --build
```

First build runs `preprocess.py --all` to bake all four processed datasets +
scalers into the image (~2 minutes). Subsequent starts are instant.

API: [http://localhost:8000](http://localhost:8000)
Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

Stop with `docker compose down`.

---

## Manual setup

```bash
python -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt
echo "GOOGLE_API_KEY=your_key_here" > .env

python preprocess.py --all            # generates data/processed/
python models/train.py --dataset FD001
python models/train.py --dataset FD002
python models/train.py --dataset FD003
python models/train.py --dataset FD004

uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Testing

```bash
pytest                                # ~40 tests across all phases
RUN_LIVE_CREW=1 pytest                # also runs the live Gemini crew tests
```

Live crew tests are gated behind `RUN_LIVE_CREW=1` because they consume the
Gemini free-tier quota (5 RPM, 20/day on gemini-2.5-flash).

| Phase | Coverage                            |
|-------|-------------------------------------|
| 2     | CDH layer — validation, schema adapter, prioritization |
| 3     | preprocess.py — dynamic sensor detection, normalization, RUL labels |
| 4     | CNN-LSTM — architecture + inference |
| 5     | Tools — stream, predict, diagnostic, advisor |
| 6     | Agents + Crew wiring                |
| 7     | FastAPI endpoints                   |

---

## Dashboard

The frontend dashboard is built separately in [v0.dev](https://v0.dev) — a
Next.js + Tailwind + shadcn/ui app that consumes the REST API. The deployed
backend has CORS open, so any frontend can hit it.

Dashboard URL: _(to be added once deployed)_

Panels:
- Fleet health summary — totals, severity counts, average RUL, active alerts
- Fleet overview grid — all engines color-coded by status, sortable by urgency
- Engine detail — RUL countdown, severity, deep analysis trigger
- Agent activity log — output from the 3-agent crew
- Maintenance recommendations — latest action items with severity badges

---

## Deployment

Production runs on [Railway](https://railway.app) — auto-deploys on push
to `main`. The Dockerfile uses a CPU-only PyTorch build to keep the image
under Railway's free-tier limit. The container honors Railway's dynamic
`$PORT` and falls back to `8000` locally.

---

## Repository

[github.com/ebukae05/SEN](https://github.com/ebukae05/SEN)
