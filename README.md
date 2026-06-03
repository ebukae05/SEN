# SEN — Sensor Engine Network

**Universal rotating machinery predictive maintenance platform powered by a multi-agent AI pipeline.**

Predict Remaining Useful Life (RUL) for any rotating machine — turbofans,
compressors, pumps, turbines — using your own sensor data. A CNN-LSTM
forecasts time-to-failure; a three-agent CrewAI pipeline (Monitor →
Diagnostic → Maintenance Advisor) interprets the signal, ranks degrading
sensors, and produces a maintenance plan plus a PDF report.

**Live API:** [https://sen-production.up.railway.app/docs](https://sen-production.up.railway.app/docs)

---

## Key features

- **Bring your own sensor data** — CSV, JSON, or Excel upload with a guided
  schema mapping wizard. No column-name lock-in.
- **CDH layer** — spacecraft-style Command & Data Handling validates,
  prioritizes, and normalizes any input format into the internal contract.
- **Per-tenant CNN-LSTM fine-tuning** — train the model on uploaded data;
  inference automatically switches from heuristic to trained weights once
  fine-tuning completes.
- **Three-agent pipeline** — MonitorAgent (PyTorch inference) →
  DiagnosticAgent (fleet comparison, sensor trends, degradation rate) →
  MaintenanceAdvisorAgent (time-to-critical, Gemini-authored plan, PDF report).
- **Real-time fleet dashboard** — React + TypeScript + Tailwind frontend
  with sortable fleet table, engine drill-downs, live agent feed, and
  per-dataset training controls.
- **Alert dispatch** — severity transitions emit events to configured sinks
  (in-memory ring buffer, webhook, file).
- **REST API with API-key auth** — `X-API-Key` header required on every
  route. Swagger UI at `/docs`.

---

## Quick start (Docker, API only)

Requires [Docker](https://docs.docker.com/get-docker/), a free
[Gemini API key](https://aistudio.google.com/app/apikey), and any random
string for the API key.

```bash
git clone https://github.com/ebukae05/SEN.git
cd SEN
cat > .env <<EOF
GOOGLE_API_KEY=your_gemini_key_here
SEN_API_KEY=any_random_secret
EOF
docker compose up --build
```

API at [http://localhost:8000](http://localhost:8000) ·
Docs at [http://localhost:8000/docs](http://localhost:8000/docs).
First build bakes all four CMAPSS datasets and trained weights into the
image (~2 min).

### Frontend (separate process)

```bash
cd frontend
cp .env.example .env            # then fill in VITE_API_BASE + VITE_API_KEY
npm install
npm run dev
```

Dashboard at [http://localhost:5173](http://localhost:5173).

---

## Architecture

```
Raw sensor data (CSV / JSON / Excel)
        │
        ▼
   CDH Layer  (validate, prioritize, normalize)
        │
        ▼
   preprocess.py  (clean, scale, label — deterministic)
        │
        ▼
   CNN-LSTM  (per-dataset, fine-tunable per tenant)
        │
        ▼
   Monitor → Diagnostic → Maintenance Advisor   (CrewAI sequential)
        │
        ▼
   FastAPI  ──▶  React dashboard / JSON / PDF reports
```

### Model

```
Input (30 cycles × N sensors)
  → Conv1D(64,3,ReLU) → Conv1D(64,3,ReLU) → MaxPool(2)
  → LSTM(50, return_sequences=True) → Dropout(0.3)
  → LSTM(50)                       → Dropout(0.3)
  → Dense(1)  →  Predicted RUL
```

MSE loss · Adam (lr=1e-3) · 50 epochs · batch 32 · piecewise-linear RUL
labels capped at 130. Target RMSE ≈ 13–16 cycles on FD001.

---

## Stack

| Layer               | Tech                                                  |
|---------------------|-------------------------------------------------------|
| Agent orchestration | CrewAI (sequential, context chaining)                 |
| LLM                 | Google Gemini 2.5 Flash (langchain-google-genai)      |
| ML                  | PyTorch (CPU build)                                   |
| Backend             | FastAPI + Uvicorn                                     |
| Data                | Pandas, NumPy, scikit-learn, SciPy                    |
| Reports             | ReportLab (PDF)                                       |
| Frontend            | React 19 + TypeScript + Vite + Tailwind v4 + Recharts |
| Auth                | API-key (`X-API-Key`)                                 |
| Config / secrets    | YAML + python-dotenv                                  |
| Testing             | Pytest                                                |
| Container           | Docker + Docker Compose                               |
| Hosting             | Railway (API) · Vercel (frontend)                     |

---

## API surface

All routes require `X-API-Key: <SEN_API_KEY>`.

| Method | Endpoint                                                | Purpose                                  |
|--------|---------------------------------------------------------|------------------------------------------|
| GET    | `/health`                                               | Liveness                                 |
| GET    | `/engines?dataset=<id>`                                 | Engine IDs in a dataset                  |
| GET    | `/engine/{id}/status?dataset=<id>`                      | Latest RUL + severity for an engine      |
| POST   | `/analyze?dataset=<id>`                                 | Run full 3-agent crew on one engine      |
| POST   | `/ingest/upload`                                        | Upload raw sensor file (multipart)       |
| POST   | `/ingest/schema`                                        | Submit sensor schema → process dataset   |
| GET    | `/ingest/datasets`                                      | List uploaded datasets + training meta   |
| DELETE | `/ingest/dataset/{id}`                                  | Remove a custom dataset                  |
| POST   | `/ingest/dataset/{id}/train`                            | Kick off per-tenant CNN-LSTM fine-tune   |
| GET    | `/ingest/dataset/{id}/training`                         | Poll training status / RMSE              |
| POST   | `/ingest/stream/{dataset_id}`                           | Push a real-time sensor frame            |
| GET    | `/alerts/recent`                                        | Severity-transition event feed           |

See `/docs` for interactive Swagger UI.

---

## Manual setup (no Docker)

```bash
python -m venv venv
source venv/bin/activate              # Windows: venv\Scripts\activate
pip install -r requirements.txt

cat > .env <<EOF
GOOGLE_API_KEY=your_gemini_key_here
SEN_API_KEY=any_random_secret
EOF

python preprocess.py --all
python models/train.py --dataset FD001        # (and FD002 / FD003 / FD004)
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Testing

```bash
pytest                                # full suite
RUN_LIVE_CREW=1 pytest                # also runs live Gemini crew tests
```

Live crew tests are gated because they consume Gemini free-tier quota
(5 RPM, 20/day on gemini-2.5-flash).

---

## Repository

[github.com/ebukae05/SEN](https://github.com/ebukae05/SEN)
