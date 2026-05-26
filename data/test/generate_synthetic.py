"""Generate a synthetic compressor dataset for testing the ingestion wizard.

10 units × 200 cycles = 2000 rows. Each unit is stable for the first 100
cycles and then deteriorates over the last 100: vibration and bearing
temperature rise, inlet pressure drops, and shaft RPM falls off slightly.
Per-unit baselines and noise are seeded so the file is reproducible.

Run from anywhere:
    python data/test/generate_synthetic.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_PATH = Path(__file__).resolve().parent / "synthetic_compressor.csv"

N_UNITS = 10
N_CYCLES = 200
STABLE_CYCLES = 100


def _unit_baselines(unit_id: int, rng: np.random.Generator) -> dict[str, float]:
    """Pick slightly different healthy baselines per unit so fleet variance is realistic."""
    return {
        "vibration_x": 2.0 + rng.uniform(-0.2, 0.2),
        "vibration_y": 1.8 + rng.uniform(-0.2, 0.2),
        "temperature_bearing": 65.0 + rng.uniform(-2.0, 2.0),
        "pressure_inlet": 5.0 + rng.uniform(-0.1, 0.1),
        "rpm_shaft": 3600.0 + rng.uniform(-15.0, 15.0),
    }


def _degradation_factor(cycle: int) -> float:
    """0.0 for cycles 1..STABLE_CYCLES, then ramps quadratically to 1.0 at the final cycle."""
    if cycle <= STABLE_CYCLES:
        return 0.0
    progress = (cycle - STABLE_CYCLES) / (N_CYCLES - STABLE_CYCLES)
    return progress ** 2


def _build_unit(unit_id: int, rng: np.random.Generator) -> pd.DataFrame:
    """Build one unit's 200-cycle time series with stable phase + degradation phase."""
    baseline = _unit_baselines(unit_id, rng)
    rows: list[dict[str, float]] = []
    for cycle in range(1, N_CYCLES + 1):
        deg = _degradation_factor(cycle)
        noise = rng.normal(0.0, 1.0, size=5) * np.array([0.04, 0.04, 0.5, 0.02, 4.0])
        rows.append(
            {
                "unit_id": unit_id,
                "cycle": cycle,
                "vibration_x": baseline["vibration_x"] + 6.0 * deg + noise[0],
                "vibration_y": baseline["vibration_y"] + 5.0 * deg + noise[1],
                "temperature_bearing": baseline["temperature_bearing"] + 25.0 * deg + noise[2],
                "pressure_inlet": baseline["pressure_inlet"] - 1.2 * deg + noise[3],
                "rpm_shaft": baseline["rpm_shaft"] - 80.0 * deg + noise[4],
                "rul": N_CYCLES - cycle,
            }
        )
    return pd.DataFrame(rows)


def generate() -> pd.DataFrame:
    """Generate the full multi-unit dataset deterministically."""
    rng = np.random.default_rng(seed=42)
    frames = [_build_unit(unit_id, rng) for unit_id in range(1, N_UNITS + 1)]
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    """Write the dataset to OUTPUT_PATH."""
    df = generate()
    df["unit_id"] = df["unit_id"].astype(int)
    df["cycle"] = df["cycle"].astype(int)
    df["rul"] = df["rul"].astype(int)
    df = df.round(
        {
            "vibration_x": 3,
            "vibration_y": 3,
            "temperature_bearing": 2,
            "pressure_inlet": 3,
            "rpm_shaft": 1,
        }
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
