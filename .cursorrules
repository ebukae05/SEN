# SEN — Sensor Engine Network (v3)

## Your Role
You are a senior Python engineer implementing a system designed by the architect.
The architecture is final. Do not suggest alternative frameworks, models, or patterns.
Build exactly what is specified below. Ask clarifying questions only about
implementation details, never about design decisions.

## What This Project Is
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

## Stack
- Python 3.10+
- CrewAI (agent orchestration framework)
- Google Gemini 2.5 Flash (LLM powering agents — free tier via langchain-google-genai)
- PyTorch (CNN-LSTM model training and inference)
- FastAPI (REST API backend)
- React + TypeScript + Tailwind CSS (frontend dashboard — built separately in v0.dev)
- Pandas, NumPy, scikit-learn (MinMaxScaler), SciPy (linregress), Matplotlib
- ReportLab (PDF report generation)
- Python-dotenv (environment variable management)
- Pytest (testing)
- Docker (containerization)
- NASA CMAPSS FD001-FD004 datasets

## Project Structure
```
SEN/
├── .cursorrules              # This file — project memory
├── .env                      # API keys (GOOGLE_API_KEY) — never commit
├── .gitignore
├── requirements.txt
├── config.yaml               # All configurable values
├── README.md
├── prompts.md                # Saved Cursor prompts
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
├── outputs/
│   └── reports/              # Generated PDF maintenance reports
│
├── notebooks/                # EDA and experimentation
│   └── eda.ipynb
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

## System Architecture

### Overview
```
Raw sensor data (any format)
→ CDH Layer (validate, prioritize, format)
→ preprocess.py (clean, normalize, label)
→ MonitorAgent → DiagnosticAgent → MaintenanceAdvisorAgent
→ FastAPI → React Dashboard + PDF Reports
```

### CDH Layer (cdh/handler.py)
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

This is what makes SEN sensor-agnostic. The CDH layer normalizes any input format
into SEN's internal standard so the agents and model never care what format came in.

### preprocess.py (Deterministic Script — NOT an agent)
Always runs the same steps in the same order. No LLM involved.
- Load specified CMAPSS dataset from data/raw/
- Add column headers
- Validate data and identify constant sensors dynamically
- Drop constant sensors (detected per dataset, not hardcoded)
- Normalize remaining sensors to 0-1 using MinMaxScaler
- Generate RUL labels using piecewise linear method with cap from config.yaml
- Save cleaned data to data/processed/

### Agent 1: MonitorAgent
- Role: "Real-Time Engine Health Monitor"
- Goal: "Stream sensor data through the CNN-LSTM model and flag engines approaching failure"
- Tools:
  - stream_sensors(df, engine_id, window_size) → yields sliding windows
  - predict_rul(window) → runs CNN-LSTM inference, returns RUL float
  - check_thresholds(engine_id, rul, threshold) → returns alert if RUL below threshold
- Libraries: PyTorch, NumPy
- Output: RUL predictions + anomaly flags per engine

### Agent 2: DiagnosticAgent
- Role: "Engine Diagnostics Specialist"
- Goal: "Investigate flagged engines to determine root cause and severity of degradation"
- Tools:
  - compare_to_fleet(df, engine_id) → compares engine metrics to fleet average
  - sensor_trends(df, engine_id) → ranks sensors by rate of decline
  - degradation_rate(df, engine_id) → calculates rate of decline using scipy linregress
- Libraries: Pandas, NumPy, SciPy
- Output: Diagnosis with root cause, degrading sensors, severity rating

### Agent 3: MaintenanceAdvisorAgent
- Role: "Maintenance Planning Advisor"
- Goal: "Generate actionable maintenance recommendations and formal PDF reports"
- Tools:
  - time_to_critical(rul, degradation_rate) → estimates cycles until unsafe
  - recommend_action(diagnosis) → calls Gemini 2.5 Flash, returns recommendation string
  - generate_report(engine_id, diagnosis, recommendation) → creates PDF via ReportLab
- Libraries: NumPy, Google Gemini API, ReportLab
- Output: Maintenance recommendation + PDF report

## CNN-LSTM Model Architecture
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
- Epochs: 50
- Batch size: 32
- Sequence length: 30 cycles
- RUL cap: 130 (piecewise linear labeling)
- Target RMSE: 13-16 cycles on FD001 test set

## About the CMAPSS Datasets
All four datasets share the same 21 sensor columns. Constant sensors vary per dataset
and must be detected dynamically by validate_sensors, not hardcoded.

- FD001: 100 engines, 1 operating condition, 1 fault mode (HPC degradation)
- FD002: 260 engines, 6 operating conditions, 1 fault mode (HPC degradation)
- FD003: 100 engines, 1 operating condition, 2 fault modes (HPC + fan degradation)
- FD004: 249 engines, 6 operating conditions, 2 fault modes (HPC + fan degradation)

Column names: unit_id, cycle, op1, op2, op3, s1-s21
Keep 14 sensors after dropping constants (exact sensors determined dynamically per dataset)

## Data File Locations
- data/raw/train_FD001.txt through train_FD004.txt
- data/raw/test_FD001.txt through test_FD004.txt
- data/raw/RUL_FD001.txt through RUL_FD004.txt

## CrewAI Configuration
```python
from crewai import Crew, Process

crew = Crew(
    agents=[monitor, diagnostician, advisor],
    tasks=[monitor_task, diagnose_task, advise_task],
    process=Process.sequential,
    verbose=True
)
```
- LLM: Gemini 2.5 Flash via langchain-google-genai
- Process: Sequential
- Each agent receives the previous agent's output as context

## FastAPI Endpoints
- GET /health — health check, returns status ok
- GET /engines — list all engine IDs from processed dataset
- GET /engine/{id}/status — latest prediction for one engine
- POST /analyze — accepts engine_id, triggers full crew pipeline, returns results

## Frontend Dashboard (React + TypeScript — built in v0.dev)
The frontend is a separate React/TypeScript/Tailwind application.
FastAPI serves data. The dashboard consumes it via REST API calls.
Do NOT build a Plotly Dash dashboard. Do NOT build any Python frontend.

Dashboard panels:
- Fleet health summary bar — total engines, green/yellow/red counts, avg RUL, active alerts
- Fleet overview grid — all engines color-coded by status, sortable by urgency
- Single engine detail — RUL countdown, degradation curve, sensor trends over cycles
- Agent activity log — scrolling feed of what each agent found, color-coded by severity
- Maintenance recommendations panel — latest recommendations with severity badges

## Sensor-Agnostic Design Principles
SEN is not an aircraft-only tool. The CDH layer's schema adapter allows any operator
to map their own column names to SEN's internal format. This means SEN can monitor:
- Aircraft turbofan engines (current use case)
- Wind turbine gearboxes
- Railroad wheel bearings
- Industrial pumps and compressors
- Naval vessel engines
- Manufacturing equipment

The model needs retraining per equipment type but the architecture stays the same.

## Build Phases — Follow This Order

### Phase 1: Project Setup
- Create full folder structure
- Set up venv, install all dependencies
- Create config.yaml with all configurable values
- Create .env with GOOGLE_API_KEY placeholder
- Create .gitignore
- Verify CrewAI and Gemini 2.5 Flash connect successfully

### Phase 2: CDH Layer
- Build cdh/handler.py
- Support CSV, JSON, Excel input formats
- Schema adapter for user-defined column mapping
- Data validation and error flagging
- Engine prioritization by RUL
- Write tests in tests/test_cdh.py
- Test with CMAPSS CSV and a manually created JSON file

### Phase 3: Preprocessing
- Build preprocess.py as a deterministic script
- Dynamic sensor detection (not hardcoded)
- Normalize, label, save to data/processed/
- Write tests in tests/test_preprocess.py
- Test with all four CMAPSS datasets

### Phase 4: CNN-LSTM Model
- Build models/cnn_lstm.py (architecture)
- Build models/train.py (training script)
- Train on FD001, save weights to models/saved/
- Target RMSE: 13-16 cycles
- Verify model loads and runs inference

### Phase 5: Tools
- Build all four tool files
- Test every function individually
- Write tests in tests/test_tools.py
- Full pipeline test: raw data → CDH → preprocess → stream → predict → RUL output

### Phase 6: Agents + Crew
- Build all three agents
- Build crews/maintenance_crew.py
- Test crew.kickoff() end to end
- Verify output makes sense

### Phase 7: FastAPI
- Build api/main.py
- Test all endpoints with Swagger UI at /docs

### Phase 8: Integration + Docker
- Verify full pipeline works end to end
- Ensure Docker container runs the full stack
- Deploy to Railway for a shareable demo URL

### Phase 9: README + Demo
- Add architecture diagram screenshot
- Add dashboard screenshot
- Add working quickstart instructions
- Add API documentation
- Record Loom walkthrough

## Rules — Never Do These
- Do not build a Plotly Dash or any Python frontend. Frontend is React/TypeScript only.
- Do not create a DataEngineerAgent. Data engineering is handled by preprocess.py.
- Do not skip phases. Build and test each phase before moving to the next.
- Do not write functions longer than 30 lines.
- Do not use vague variable names like x, df2, temp, data1.
- Do not hardcode values. Everything configurable goes in config.yaml.
- Do not store API keys in code. Use .env and python-dotenv.
- Do not install packages without adding them to requirements.txt.
- Do not use print() for logging. Use Python logging module.
- Do not catch generic exceptions. Catch specific ones.
- Do not bleed responsibilities between layers. CDH validates. preprocess cleans. Tools compute. Agents orchestrate.

## Rules — Always Do These
- Always read config.yaml for any configurable value.
- Always type hint every function parameter and return value.
- Always write a docstring for every function.
- Always validate inputs at the start of every function.
- Always use pathlib.Path for file paths.
- Always use logging.getLogger(__name__) for logging.
- Always test after completing each phase before moving on.

## Git Rules
- Never run git push, git commit, or git add automatically.
- Never touch git without explicit instruction from the architect.
- All version control decisions are made by the architect only.

## Current Phase
Phase 1 — Project Setup