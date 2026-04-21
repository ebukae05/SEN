# SEN — Sensor Engine Network

Real-time turbofan engine health monitoring system powered by a 4-agent AI pipeline, CNN-LSTM deep learning, and Gemini AI.

---

## What It Does

SEN ingests NASA CMAPSS sensor data from up to 260 turbofan engines across 4 datasets (FD001–FD004), predicts Remaining Useful Life (RUL) using per-dataset CNN-LSTM models, runs a multi-agent diagnostic pipeline, and delivers maintenance recommendations with generated PDF reports — all surfaced through a REST API and a Next.js dashboard with a live dataset selector.

---

## Architecture

```
Raw Sensor Data (NASA CMAPSS FD001–FD004)
        |
        v
+-------------------------------------------------+
|           4-Agent Sequential Pipeline            |
|                                                  |
|  DataEngineerAgent -> MonitorAgent               |
|      -> DiagnosticAgent -> MaintenanceAdvisor    |
+-------------------------------------------------+
        |
        v
  PDF Report + Maintenance Recommendation
        |
        +-- FastAPI REST Layer  (port 8000)
        +-- Next.js Dashboard   (port 3000)
```

### CNN-LSTM Model

```
Input (30 cycles x 14 or 16 sensors)
-> Conv1D(64, kernel=3, ReLU)
-> Conv1D(64, kernel=3, ReLU)
-> MaxPooling1D(2)
-> LSTM(50, return_sequences=True)
-> Dropout(0.3)
-> LSTM(50)
-> Dropout(0.3)
-> Dense(1) -> Predicted RUL
```

One model trained per dataset. Feature count varies: 14 sensors for FD001/FD003 (1 operating condition), 16 sensors for FD002/FD004 (6 operating conditions).

### Agent Pipeline

| Agent | Role | Tools |
|-------|------|-------|
| DataEngineerAgent | Ingest, clean, label sensor data | load_dataset, clean_data, generate_rul_labels, visualize_trends |
| MonitorAgent | Stream data, predict RUL, flag alerts | stream_sensors, predict_rul, check_thresholds |
| DiagnosticAgent | Root cause analysis, fleet comparison | compare_to_fleet, sensor_trends, degradation_rate |
| MaintenanceAdvisorAgent | Recommendations + PDF reports | time_to_critical, recommend_action, generate_report |

All tools accept a `dataset_id` parameter (FD001–FD004) so the entire pipeline is dataset-aware.

---

## Datasets

SEN supports all four NASA CMAPSS turbofan degradation simulation sub-datasets:

| Dataset | Engines | Operating Conditions | Fault Modes | Sensors Used |
|---------|---------|---------------------|-------------|--------------|
| FD001   | 100     | 1 (sea level)       | 1 — HPC degradation       | 14 |
| FD002   | 260     | 6                   | 1 — HPC degradation       | 16 |
| FD003   | 100     | 1 (sea level)       | 2 — HPC + fan degradation | 14 |
| FD004   | 249     | 6                   | 2 — HPC + fan degradation | 16 |

Switch datasets from the dashboard dropdown or via the `?dataset=FD002` query parameter on any API endpoint.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Agent orchestration | CrewAI |
| LLM | Google Gemini 2.5 Flash Lite |
| Deep learning | PyTorch (CNN-LSTM) |
| REST API | FastAPI |
| Dashboard | Next.js 16, shadcn/ui, Tailwind CSS, Recharts |
| Data | Pandas, NumPy, scikit-learn, SciPy |
| Reports | ReportLab |
| Dataset | NASA CMAPSS FD001–FD004 |
| Deployment | Docker, Docker Compose |

---

## Project Structure

```
SEN/
├── config.yaml              # All configurable values
├── docker-compose.yml       # One-command deployment
├── Dockerfile.api           # Python API container
├── agents/                  # CrewAI agent definitions
├── crews/                   # Pipeline crew orchestration
├── tools/                   # Ingest, predict, diagnostic, advisor tools
├── models/                  # CNN-LSTM architecture + training script
├── api/                     # FastAPI endpoints
├── frontend/                # Next.js dashboard
│   ├── Dockerfile           # Frontend container
│   ├── app/                 # Next.js app router
│   ├── components/
│   │   ├── views/           # Fleet, Engine Detail, Agents, Recommendations, Home
│   │   └── ui/              # shadcn/ui component library
│   └── lib/                 # API client, engine utilities
├── data/raw/                # NASA CMAPSS FD001–FD004 raw files (12 files)
├── data/processed/          # Per-dataset clean CSVs and scalers
└── tests/                   # Phase verification tests
```

---

## Quick Start (Docker)

The fastest way to run SEN on any platform. Requires [Docker](https://docs.docker.com/get-docker/).

```bash
git clone https://github.com/ebukae05/SEN.git
cd SEN
```

Create a `.env` file with your Gemini API key:

```bash
echo "GOOGLE_API_KEY=your_key_here" > .env
```

Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

Build and run:

```bash
docker compose up --build
```

On first launch, the API container automatically processes the raw data and trains the CNN-LSTM model (~5 minutes). Subsequent starts are instant.

Open [http://localhost:3000](http://localhost:3000) for the dashboard, [http://localhost:8000/docs](http://localhost:8000/docs) for the API.

To stop:

```bash
docker compose down
```

---

## Manual Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### 1. Clone and set up the backend

```bash
git clone https://github.com/ebukae05/SEN.git
cd SEN
```

Create a virtual environment:

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Add your API key

Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_key_here
```

Get a free key at [aistudio.google.com](https://aistudio.google.com/app/apikey).

### 3. Prepare data and train models

Process and train for each dataset you want to use. FD001 is the default. Repeat for FD002, FD003, FD004 as needed.

```bash
python -c "
from tools.ingest_tools import load_dataset, clean_data, generate_rul_labels
import yaml, pathlib
dataset_id = 'FD001'  # change to FD002, FD003, or FD004
cfg = yaml.safe_load(open('config.yaml'))
df = load_dataset('train', dataset_id=dataset_id)
df = clean_data(df, dataset_id=dataset_id)
df = generate_rul_labels(df)
out = pathlib.Path(cfg['data']['processed_dir'])
out.mkdir(parents=True, exist_ok=True)
df.to_csv(out / f'train_{dataset_id}_clean.csv', index=False)
print(f'Saved {len(df)} rows for {dataset_id}')
"
```

Then train the model (~2-5 minutes per dataset):

```bash
python models/train.py --dataset FD001
python models/train.py --dataset FD002
python models/train.py --dataset FD003
python models/train.py --dataset FD004
```

### 4. Start the API

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Start the dashboard

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Dashboard: [http://localhost:3000](http://localhost:3000)

---

## Dashboard Views

- **Home** — System overview and quick status summary
- **Fleet Overview** — All engines in the selected dataset with RUL predictions colored by severity
- **Engine Detail** — RUL timeline, sensor trends, and deep AI analysis for any engine
- **Agents** — Activity log from the 4-agent pipeline
- **Recommendations** — Maintenance actions with confidence scores and contributing factors

A dataset selector dropdown at the top of the dashboard lets you switch between FD001–FD004 on the fly.

---

## API Endpoints

All data endpoints accept an optional `?dataset=FD001` query parameter (default: FD001).

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness check |
| GET | `/datasets` | List all available CMAPSS datasets with metadata |
| GET | `/engines` | List all engine IDs in the selected dataset |
| GET | `/engine/{id}/status` | RUL + severity for one engine |
| GET | `/engine/{id}/sensors` | Normalized sensor history (dynamic sensor count) |
| GET | `/fleet` | Health snapshot for all engines |
| POST | `/analyze` | Deep analysis: RUL prediction, diagnostics, Gemini recommendation, PDF report |
| POST | `/api/chat` | Chat with Gemini about engine data |

---

## Deep Analysis

Click "Run Deeper Analysis" on any engine detail page. The system:

1. Predicts RUL using the CNN-LSTM model
2. Checks alert thresholds
3. Compares the engine to fleet averages
4. Identifies the top 3 declining sensors
5. Calculates degradation rate vs fleet
6. Estimates time to critical failure
7. Generates a Gemini-powered maintenance recommendation
8. Produces a PDF report

Completes in ~10 seconds (single Gemini API call).

---

## Test Results

| Phase | Test | Result |
|-------|------|--------|
| 2 | Ingest tools | 5/5 |
| 4 | Stream + predict tools | 5/5 |
| 5 | Diagnostic + advisor tools | 4/4 |
| 6 | Full agent pipeline | 2/2 |
| 7 | FastAPI endpoints | 4/4 |
| 8 | Dashboard structure | 4/4 |

---

## Dataset

NASA CMAPSS — [Turbofan Engine Degradation Simulation Data Set](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)

- 4 sub-datasets (FD001–FD004), 100–260 engines each
- 21 sensor channels per dataset; 14 or 16 kept after dropping near-constant sensors
- 1–6 operating conditions, 1–2 fault modes (HPC degradation, fan degradation)
- RUL capped at 130 cycles (piecewise linear labeling)
