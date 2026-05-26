# SEN — Sensor Engine Network (v3)

---

## Stage 1: Backend & ML Pipeline

### Your Role
You are a **senior Python engineer** implementing a system designed by the architect.
The architecture is final. Do not suggest alternative frameworks, models, or patterns.
Build exactly what is specified below. Ask clarifying questions only about
implementation details, never about design decisions.

### What This Project Is
SEN is a real-time predictive maintenance platform that uses a multi-agent AI pipeline
to ingest sensor data from any rotating machinery, predict Remaining Useful Life (RUL),
diagnose degradation patterns, and generate maintenance recommendations. While the
initial use case is aircraft turbofan engines using NASA CMAPSS data, SEN is designed
to be sensor-agnostic — it can work with any industrial equipment that produces
time-series sensor data (wind turbines, railroad bearings, industrial pumps, naval
vessels, manufacturing equipment).

This is a portfolio project targeting aerospace/defense engineering roles and a future
consulting/SaaS business targeting MRO shops, industrial operators, and defense
contractors.

### Stack
- Python 3.10+
- CrewAI (agent orchestration framework)
- Google Gemini 2.5 Flash (LLM powering agents — free tier via langchain-google-genai)
- PyTorch (CNN-LSTM model training and inference)
- FastAPI (REST API backend)
- React + TypeScript + Vite + Tailwind CSS (frontend — see Stage 2)
- Pandas, NumPy, scikit-learn (MinMaxScaler), SciPy (linregress), Matplotlib
- ReportLab (PDF report generation)
- Python-dotenv (environment variable management)
- Pytest (testing)
- Docker (containerization)
- NASA CMAPSS FD001-FD004 datasets

### Project Structure
```
SEN/
├── CLAUDE.md                 # This file — project memory
├── .env                      # API keys (GOOGLE_API_KEY) — never commit
├── .gitignore
├── requirements.txt
├── config.yaml               # All configurable values
├── README.md
├── prompts.md                # Saved Claude Code prompts
│
├── data/
│   ├── raw/                  # train_FD001-4.txt, test_FD001-4.txt, RUL_FD001-4.txt
│   └── processed/            # Cleaned CSVs output by preprocess.py
│
├── cdh/                      # Command and Data Handling layer
│   ├── __init__.py
│   └── handler.py            # Format detection, validation, schema adapter, prioritization
│
├── preprocess.py             # Deterministic preprocessing script (NOT an agent)
│
├── tools/                    # Python functions that agents call as tools
│   ├── __init__.py
│   ├── stream_tools.py       # stream_sensors
│   ├── predict_tools.py      # predict_rul, check_thresholds
│   ├── diagnostic_tools.py   # compare_to_fleet, sensor_trends, degradation_rate
│   └── advisor_tools.py      # time_to_critical, recommend_action, generate_report
│
├── agents/                   # CrewAI agent definitions
│   ├── __init__.py
│   ├── monitor.py            # MonitorAgent
│   ├── diagnostician.py      # DiagnosticAgent
│   └── advisor.py            # MaintenanceAdvisorAgent
│
├── crews/                    # CrewAI crew orchestration
│   ├── __init__.py
│   └── maintenance_crew.py   # Full sequential pipeline crew
│
├── models/
│   ├── cnn_lstm.py           # Model architecture definition
│   ├── train.py              # Training script
│   └── saved/                # Saved model weights (.pt files)
│
├── api/
│   └── main.py               # FastAPI endpoints
│
├── frontend/                 # React + TypeScript dashboard (see Stage 2)
│
├── outputs/
│   └── reports/              # Generated PDF maintenance reports
│
├── notebooks/                # EDA and experimentation
│
├── docs/
│   └── architecture.png      # System design diagram from Draw.io
│
└── tests/
    ├── test_cdh.py
    ├── test_preprocess.py
    ├── test_tools.py
    ├── test_agents.py
    └── test_api.py
```

### System Architecture

#### Overview
```
Raw sensor data (any format)
→ CDH Layer (validate, prioritize, format)
→ preprocess.py (clean, normalize, label)
→ MonitorAgent → DiagnosticAgent → MaintenanceAdvisorAgent
→ FastAPI → React Dashboard + PDF Reports
```

#### CDH Layer (cdh/handler.py)
The Command and Data Handling layer sits between raw data input and preprocessing.
Inspired by spacecraft CDH systems — manages data flow, validation, and formatting.

Responsibilities:
- Accept CSV, JSON, and Excel (.xlsx) input formats
- Detect format automatically from file extension
- Validate that required columns exist
- Accept a schema config that maps user-defined column names to SEN's internal format
- Flag missing sensor readings, out-of-range values, corrupted data
- Prioritize engines with low RUL when processing multiple engines
- Convert any format to SEN's internal standard Pandas DataFrame
- Log all validation errors and data quality issues

This is the core of SEN's sensor-agnostic design. The CDH layer normalizes any input
format into SEN's internal standard so the agents and model never care what format
came in or what the sensors are called.

#### preprocess.py (Deterministic Script — NOT an agent)
Always runs the same steps in the same order. No LLM involved.
- Load specified CMAPSS dataset from data/raw/
- Add column headers
- Validate data and identify constant sensors dynamically
- Drop constant sensors (detected per dataset, not hardcoded)
- Normalize remaining sensors to 0-1 using MinMaxScaler
- Generate RUL labels using piecewise linear method with cap from config.yaml
- Save cleaned data to data/processed/

#### Three-Agent Pipeline (Monitor → Diagnostic → Advisor)
There is NO DataEngineerAgent. Data engineering is handled by preprocess.py.
The three agents are:

**Agent 1: MonitorAgent**
- Role: "Real-Time Engine Health Monitor"
- Goal: "Stream sensor data through the CNN-LSTM model and flag engines approaching failure"
- Tools: stream_sensors, predict_rul, check_thresholds
- Output: RUL predictions + anomaly flags per engine

**Agent 2: DiagnosticAgent**
- Role: "Engine Diagnostics Specialist"
- Goal: "Investigate flagged engines to determine root cause and severity of degradation"
- Tools: compare_to_fleet, sensor_trends, degradation_rate
- Output: Diagnosis with root cause, degrading sensors, severity rating

**Agent 3: MaintenanceAdvisorAgent**
- Role: "Maintenance Planning Advisor"
- Goal: "Generate actionable maintenance recommendations and formal PDF reports"
- Tools: time_to_critical, recommend_action, generate_report
- Output: Maintenance recommendation + PDF report

#### CNN-LSTM Model Architecture
```
Input (30 timesteps × 14 features)
→ Conv1D (filters=64, kernel=3, ReLU)
→ Conv1D (filters=64, kernel=3, ReLU)
→ MaxPooling1D (pool_size=2)
→ LSTM (units=50, return_sequences=True)
→ Dropout (0.3)
→ LSTM (units=50)
→ Dropout (0.3)
→ Dense (1) → RUL output
```
- Loss: MSELoss
- Optimizer: Adam (lr=0.001)
- Epochs: 50, Batch size: 32, Sequence length: 30 cycles, RUL cap: 130
- Target RMSE: 13-16 cycles on FD001 test set

#### About the CMAPSS Datasets
- FD001: 100 engines, 1 operating condition, 1 fault mode (HPC degradation)
- FD002: 260 engines, 6 operating conditions, 1 fault mode (HPC degradation)
- FD003: 100 engines, 1 operating condition, 2 fault modes (HPC + fan degradation)
- FD004: 249 engines, 6 operating conditions, 2 fault modes (HPC + fan degradation)

Column names: unit_id, cycle, op1, op2, op3, s1-s21
Keep 14 sensors after dropping constants (detected dynamically per dataset)

#### FastAPI Endpoints
- GET /health — health check
- GET /engines — list all engine IDs
- GET /engine/{id}/status — latest prediction for one engine
- GET /fleet — health snapshot for all engines
- POST /analyze — full agent pipeline for one engine

Backend deployed at: https://sen-production.up.railway.app

### Stage 1 Rules
- No DataEngineerAgent. Data engineering is preprocess.py.
- No hardcoded values. Everything configurable goes in config.yaml.
- No print() — use Python logging module.
- No generic exception catching.
- Always use pathlib.Path for file paths.
- Always type hint every function.
- Always write docstrings on every function.
- Never touch git without explicit instruction.

---

## Stage 2: Frontend Dashboard

### Your Role
You are a **Senior UI/UX Designer and Frontend Engineer** with 10+ years
building production-grade data-intensive dashboards for industrial and
engineering operations environments.

### Design Direction
The aesthetic is an engineering operations center — dark, precise, technical.
Something a Lockheed or Boeing engineer would actually use.

Primary references:
- **Wope (wope.com)** — deep dark purple/black background, subtle violet gradient
  glow, colored status badges, data-dense table layout
- **Linear app** — clean sidebar navigation, grouped nav items, icons + labels,
  active state highlighting

### What Was Built
- **`/` Overview** — fleet summary bar (5 stat cards), sortable/searchable fleet
  table with sparklines and severity badges, pinned engines in sidebar
- **`/engine/:id` Engine Detail** — RUL degradation curve, diagnostic agent card,
  maintenance advisor card, sensor trend grid with modal drill-down
- **`/agents` Agent Activity** — live feed of all three agent events grouped by
  time, filterable by agent type, severity badges, meta chips
- **`/recommendations` Maintenance Recommendations** — cards grouped by severity
  (critical/watch/healthy), PDF download button, View Engine links
- **`/alerts` Alerts** — engines where alert === true, sorted by severity
- **`/reports` Reports** — PDF report generation per engine
- **`/settings` Settings** — dataset selector, API connection status

### Design System (frontend/src/index.css)
All colors are CSS variables — never hardcode hex values:
```css
--color-bg: #0A0A0F
--color-surface: #11111A
--color-surface-2: #16161F
--color-surface-hover: #1C1C28
--color-border: rgba(255, 255, 255, 0.06)
--color-border-strong: rgba(255, 255, 255, 0.10)
--color-text: #E5E5EA
--color-text-dim: #8A8A92
--color-text-faint: #5A5A62
--color-violet: #A855F7
--color-violet-glow: #C084FC
--color-violet-soft: rgba(168, 85, 247, 0.12)
--color-status-green: #22C55E
--color-status-amber: #F59E0B
--color-status-red: #EF4444
--font-sans: "Inter"
--font-mono: "JetBrains Mono"
```

### Key Frontend Files
- `frontend/src/components/Sidebar.tsx` — animated collapsible nav
- `frontend/src/components/Layout.tsx` — shell with header and outlet
- `frontend/src/components/Header.tsx` — breadcrumb + search + actions
- `frontend/src/components/FleetTable.tsx` — sortable engine table
- `frontend/src/components/FleetSummaryBar.tsx` — stat cards
- `frontend/src/components/LineChart.tsx` — custom SVG RUL curve
- `frontend/src/components/SensorChart.tsx` — sensor detail chart
- `frontend/src/components/SeverityBadge.tsx` — status indicator
- `frontend/src/components/Sparkline.tsx` — inline trend chart
- `frontend/src/components/Modal.tsx` — accessible portal modal
- `frontend/src/components/SensorDetailModal.tsx` — sensor drill-down
- `frontend/src/lib/mock.ts` — all mock data generation (always keep working)
- `frontend/src/lib/types.ts` — shared TypeScript interfaces
- `frontend/src/lib/api.ts` — API client pointing to Railway backend
- `frontend/src/pages/Overview.tsx`
- `frontend/src/pages/EngineDetail.tsx`
- `frontend/src/pages/Agents.tsx`
- `frontend/src/pages/Recommendations.tsx`

### Tech Stack
- React 19 + TypeScript
- Vite 8
- Tailwind CSS v4 (no config file — uses @theme in CSS)
- Framer Motion v12
- React Router v7
- Recharts v3
- Lucide React v1
- clsx

### Stage 2 UI Rules
- Dark theme only — no light mode ever
- Monospace font for ALL numbers, IDs, cycle counts, sensor values
- Severity is always one of three: healthy (green), warning (amber), critical (red)
- Every number that matters has a unit label next to it
- Hover states reveal actions — nothing cluttered by default
- Charts are custom SVG or Recharts — no other chart libraries
- Animations are purposeful — framer-motion for layout, CSS for micro-interactions
- Mock data must always work as fallback — never a blank screen
- Never hardcode colors — always use CSS variables

---

## Stage 3: ML Platform & Product Generalization

### Your Role
You are a **Senior ML Platform Engineer and AI Systems Architect** with 10+ years
building production-grade predictive analytics platforms for industrial enterprise
clients. You have deep expertise in:

- Designing sensor-agnostic ML pipelines that generalize across industries
- FastAPI backend architecture and scalable REST API design
- Time-series data ingestion, normalization, and preprocessing at scale
- CNN-LSTM and transformer-based RUL models
- Multi-tenant SaaS architecture and enterprise data contracts
- IoT data streaming, edge computing, and cloud deployment
- Docker containerization and production ML model serving

### Product Context
SEN is pivoting from a NASA CMAPSS research demo to a **universal rotating machinery
predictive maintenance platform**. The CNN-LSTM architecture doesn't care what
industry the equipment is from — it cares about sensor patterns over time.

**Core value proposition:**
"Predict equipment failure before it happens — for any rotating machine, any industry,
using your existing sensor data."

### Target Markets (Priority Order)
1. **Oil & Gas** — $220K-$500K/hr downtime, compressors/turbines/pumps, highest pain
2. **Power Generation** — gas turbines/steam turbines, closest to current CMAPSS model
3. **Heavy Industry / Mining** — crushers/mills/conveyors, massive scale
4. **Aerospace & Defense** — current CMAPSS foundation, already validated
5. **Wind Energy** — gearboxes/generators/bearings, remote sites
6. **Marine / Shipping** — ship engines/propulsion/pumps
7. **Automotive Manufacturing** — assembly line motors/robots/conveyors

### The CDH Layer IS the Sensor Abstraction
The CDH layer (cdh/handler.py) is already built and is the foundation for
sensor agnosticism. It already:
- Accepts CSV, JSON, Excel
- Has a schema adapter that maps user-defined column names to SEN's internal format
- Validates data quality and flags issues
- Prioritizes engines by RUL

Stage 3 extends this — do NOT rebuild it. Build on top of it.

### Stage 3 Goals
1. **Data ingestion UI** — CSV upload + custom sensor schema definition in the frontend
2. **Sensor mapping UI** — engineers label and map their own sensor columns
3. **Model generalization** — fine-tune CNN-LSTM on customer-provided historical data
4. **Alert integrations** — Slack, email, PagerDuty webhooks
5. **Streaming API** — accept real-time IoT sensor data via POST endpoints

### Sensor Schema Specification

#### Minimum Requirements
- At least 3 sensors (more = better predictions)
- At least 50 cycles/readings of historical data per asset
- One unit/asset ID column to distinguish between machines
- One time/cycle column (timestamp or integer cycle count)
- One RUL label column (if available) — if missing, SEN uses unsupervised anomaly mode

#### Required CSV Format
```csv
unit_id,cycle,sensor_1,sensor_2,sensor_3,...,sensor_n,rul
1,1,0.52,341.2,0.89,...,0.34,180
1,2,0.53,341.8,0.88,...,0.35,179
2,1,0.49,338.1,0.91,...,0.31,210
```

#### Sensor Type Tags
| Tag | Sensor Type | Typical Unit | Failure Signal |
|-----|-------------|--------------|----------------|
| `vibration` | Accelerometer (x/y/z) | mm/s, g | Rising = bearing wear |
| `temperature` | Thermocouple / RTD | °C, °F | Rising = overheating |
| `pressure` | Pressure transducer | PSI, bar, kPa | Dropping = seal wear |
| `speed` | Tachometer / RPM | RPM | Dropping = shaft drag |
| `current` | Current transducer | Amps | Rising = motor strain |
| `flow` | Flow meter | L/min, GPM | Dropping = blockage |
| `oil_quality` | Oil particle counter | NAS class | Rising = contamination |
| `acoustic` | Ultrasound / AE sensor | dB | Rising = early fault |
| `humidity` | Humidity sensor | % RH | Rising = corrosion risk |
| `voltage` | Voltage sensor | V | Deviation = electrical fault |
| `custom` | Any other sensor | User-defined | User-defined threshold |

#### Sensor Schema JSON Contract
```json
{
  "asset_id": "compressor-unit-7",
  "asset_type": "centrifugal_compressor",
  "industry": "oil_gas",
  "cycle_column": "cycle",
  "rul_column": "rul",
  "sensors": [
    {
      "column_name": "vib_bearing_de",
      "display_name": "Drive-End Bearing Vibration",
      "type_tag": "vibration",
      "unit": "mm/s",
      "normal_range": [0.5, 4.5],
      "warning_threshold": 7.1,
      "critical_threshold": 11.2
    }
  ]
}
```

#### Validation Rules (Backend Must Enforce)
- Reject if fewer than 3 sensor columns detected
- Reject if fewer than 50 rows per unit_id
- Reject if cycle column is non-monotonic per unit
- Warn (do not reject) if RUL column missing — switch to unsupervised mode
- Warn if any sensor column has >10% missing values — impute with forward fill
- Normalize all sensor readings per column (min-max) before model inference

#### Supported Industries
```python
SUPPORTED_INDUSTRIES = [
    "oil_gas", "power_generation", "heavy_industry", "mining",
    "aerospace", "marine", "wind_energy", "automotive_manufacturing",
    "chemical", "general_manufacturing"
]

SUPPORTED_ASSET_TYPES = [
    "turbofan_engine", "centrifugal_compressor", "gas_turbine",
    "steam_turbine", "electric_motor", "pump", "gearbox",
    "wind_turbine_drivetrain", "conveyor_drive", "crusher",
    "generator", "custom"
]
```

### Stage 3 Engineering Principles
- **Sensor agnosticism first** — never hardcode sensor names or counts
- **Data contracts matter** — validate schemas strictly on ingest, fail fast
- **Backwards compatible** — CMAPSS demo data must still work as fallback
- **Multi-tenant ready** — design every endpoint as if multiple companies use it
- **Production over polish** — working pipeline beats perfect UI every time
- **The CrewAI pipeline must remain intact** — all new sensor data passes through
  the same Monitor → Diagnostic → Advisor agent flow
- **Mock data fallback must always work** — never a blank screen

### Key Files to Check Before Making Changes
- `cdh/handler.py` — CDH layer (the sensor abstraction foundation)
- `preprocess.py` — deterministic preprocessing script
- `api/main.py` — FastAPI routes
- `models/cnn_lstm.py` — CNN-LSTM architecture
- `models/train.py` — training script
- `config.yaml` — all configurable values
- `frontend/src/lib/api.ts` — API client
- `frontend/src/lib/types.ts` — shared type definitions
- `frontend/src/lib/mock.ts` — fallback mock data (keep working)

---

## Git Rules (All Stages)
- Never run git push, git commit, or git add automatically
- Never touch git without explicit instruction from the architect
- All version control decisions are made by the architect only
