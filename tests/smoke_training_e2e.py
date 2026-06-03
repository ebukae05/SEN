"""End-to-end smoke test: upload -> schema -> train -> verify CNN-LSTM predictions.

Run against a live API at http://127.0.0.1:8765. Not part of the pytest suite —
intended for one-shot manual verification of Goal 3 + TrainingPanel wiring.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

BASE = os.environ.get("SEN_SMOKE_BASE", "http://127.0.0.1:8765")
KEY = os.environ["SEN_API_KEY"]
HEADERS = {"X-API-Key": KEY}
DATASET_FILE = Path(__file__).resolve().parent.parent / "data" / "test" / "synthetic_compressor.csv"


def step(name: str) -> None:
    print(f"\n=== {name} ===", flush=True)


def main() -> int:
    if not DATASET_FILE.exists():
        print(f"missing dataset: {DATASET_FILE}", flush=True)
        return 1

    step("1. upload")
    with DATASET_FILE.open("rb") as fh:
        res = requests.post(
            f"{BASE}/ingest/upload",
            headers=HEADERS,
            files={"file": (DATASET_FILE.name, fh, "text/csv")},
            timeout=30,
        )
    res.raise_for_status()
    preview = res.json()
    upload_id = preview["upload_id"]
    cols = preview["columns"]
    print(f"upload_id={upload_id} rows={preview['row_count']} cols={cols}", flush=True)
    assert preview["quality"]["is_valid"], preview["quality"]

    step("2. schema + process")
    sensor_cols = ["vibration_x", "vibration_y", "temperature_bearing", "pressure_inlet", "rpm_shaft"]
    type_for = {
        "vibration_x": "vibration",
        "vibration_y": "vibration",
        "temperature_bearing": "temperature",
        "pressure_inlet": "pressure",
        "rpm_shaft": "speed",
    }
    mappings = [
        {"column_name": "unit_id", "role": "unit_id", "display_name": "Unit", "type_tag": "custom", "unit": "", "warning_threshold": None, "critical_threshold": None},
        {"column_name": "cycle", "role": "cycle", "display_name": "Cycle", "type_tag": "custom", "unit": "", "warning_threshold": None, "critical_threshold": None},
        {"column_name": "rul", "role": "rul", "display_name": "RUL", "type_tag": "custom", "unit": "cycles", "warning_threshold": None, "critical_threshold": None},
    ]
    for c in sensor_cols:
        mappings.append({
            "column_name": c, "role": "sensor", "display_name": c.replace("_", " ").title(),
            "type_tag": type_for[c], "unit": "", "warning_threshold": None, "critical_threshold": None,
        })
    schema_payload = {
        "upload_id": upload_id,
        "asset_id": "smoke-compressor",
        "asset_type": "centrifugal_compressor",
        "industry": "oil_gas",
        "cycle_column": "cycle",
        "unit_id_column": "unit_id",
        "rul_column": "rul",
        "mappings": mappings,
    }
    res = requests.post(f"{BASE}/ingest/schema", headers=HEADERS, json=schema_payload, timeout=60)
    res.raise_for_status()
    result = res.json()
    dataset_id = result["dataset_id"]
    print(f"dataset_id={dataset_id} status={result['status']} has_rul={result['meta']['has_rul']}", flush=True)
    assert result["status"] == "ready", result

    step("3. baseline engine status (heuristic — before training)")
    engines = requests.get(f"{BASE}/engines?dataset={dataset_id}", headers=HEADERS, timeout=10).json()
    engine_id = engines[0]
    pre = requests.get(f"{BASE}/engine/{engine_id}/status?dataset={dataset_id}", headers=HEADERS, timeout=10).json()
    print(f"engine {engine_id} pre-train: rul={pre['predicted_rul']:.2f} severity={pre['severity']}", flush=True)

    step("4. trigger training")
    res = requests.post(f"{BASE}/ingest/dataset/{dataset_id}/train", headers=HEADERS, timeout=10)
    res.raise_for_status()
    print(res.json(), flush=True)

    step("5. poll training status")
    deadline = time.time() + 600  # 10 min cap
    last_status = None
    while time.time() < deadline:
        s = requests.get(f"{BASE}/ingest/dataset/{dataset_id}/training", headers=HEADERS, timeout=10).json()
        if s["status"] != last_status:
            print(f"  status={s['status']} rmse={s.get('training_rmse')} err={s.get('training_error')}", flush=True)
            last_status = s["status"]
        if s["status"] in ("trained", "training_failed", "failed"):
            break
        time.sleep(3)
    else:
        print("TIMEOUT waiting for training", flush=True)
        return 2

    if s["status"] != "trained":
        print(f"FAILED: {s}", flush=True)
        return 3

    step("6. post-train engine status (should use CNN-LSTM)")
    post = requests.get(f"{BASE}/engine/{engine_id}/status?dataset={dataset_id}", headers=HEADERS, timeout=15).json()
    print(f"engine {engine_id} post-train: rul={post['predicted_rul']:.2f} severity={post['severity']}", flush=True)

    step("7. verify training meta surfaces in /ingest/datasets")
    datasets = requests.get(f"{BASE}/ingest/datasets", headers=HEADERS, timeout=10).json()
    meta = next(d for d in datasets if d["dataset_id"] == dataset_id)
    print(f"meta.status={meta['status']} rmse={meta.get('training_rmse')} n_features={meta.get('n_features_trained')}", flush=True)
    assert meta["status"] == "trained"
    assert meta.get("training_rmse") is not None
    assert meta.get("n_features_trained") == len(sensor_cols)

    step("8. cleanup")
    requests.delete(f"{BASE}/ingest/dataset/{dataset_id}", headers=HEADERS, timeout=10).raise_for_status()
    print("deleted dataset", flush=True)

    print("\nSMOKE OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
