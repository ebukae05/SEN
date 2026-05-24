"""Tests for the four tool modules used by the CrewAI agents.

Covers each tool function individually plus a full pipeline integration
test: raw CMAPSS txt -> CDH -> preprocess -> stream -> predict.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import preprocess  # noqa: E402
from cdh import handler  # noqa: E402
from tools import (  # noqa: E402
    advisor_tools, diagnostic_tools, predict_tools, stream_tools,
)
from tools.advisor_tools import (  # noqa: E402
    generate_report, recommend_action, time_to_critical,
)
from tools.diagnostic_tools import (  # noqa: E402
    compare_to_fleet, degradation_rate, sensor_trends,
)
from tools.predict_tools import check_thresholds, predict_rul  # noqa: E402
from tools.stream_tools import stream_sensors  # noqa: E402

CMAPSS_COLUMNS = (
    ["unit_id", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]
)


@pytest.fixture(scope="module")
def config() -> dict:
    """Loaded project config."""
    return preprocess._load_config()


@pytest.fixture(scope="module")
def processed_fd001(config: dict) -> pd.DataFrame:
    """Load the cleaned FD001 dataset produced by preprocess.py."""
    csv_path = (
        REPO_ROOT / config["paths"]["data_processed"]
        / config["data"]["processed_filename"].format(dataset_id="FD001")
    )
    if not csv_path.exists():
        pytest.skip(f"Run preprocess.py first; {csv_path} missing")
    return pd.read_csv(csv_path)


class TestStreamSensors:
    def test_yields_correct_shape(self, processed_fd001: pd.DataFrame) -> None:
        windows = list(stream_sensors(processed_fd001, engine_id=1, window_size=30))
        assert len(windows) > 0
        for window in windows:
            assert window.shape == (30, 14)
            assert window.dtype == np.float32

    def test_window_count_matches_cycles(self, processed_fd001: pd.DataFrame) -> None:
        engine_cycles = (processed_fd001["unit_id"] == 1).sum()
        windows = list(stream_sensors(processed_fd001, engine_id=1, window_size=30))
        assert len(windows) == engine_cycles - 30 + 1

    def test_missing_engine_raises(self, processed_fd001: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="No rows"):
            list(stream_sensors(processed_fd001, engine_id=99999, window_size=30))

    def test_invalid_window_size_raises(self, processed_fd001: pd.DataFrame) -> None:
        with pytest.raises(ValueError):
            list(stream_sensors(processed_fd001, engine_id=1, window_size=0))


class TestPredictRul:
    def test_returns_float_in_plausible_range(
        self, processed_fd001: pd.DataFrame
    ) -> None:
        window = next(stream_sensors(processed_fd001, engine_id=1, window_size=30))
        rul = predict_rul(window, dataset_id="FD001")
        assert isinstance(rul, float)
        assert 0.0 <= rul <= 200.0

    def test_last_window_lower_than_first(
        self, processed_fd001: pd.DataFrame
    ) -> None:
        windows = list(stream_sensors(processed_fd001, engine_id=1, window_size=30))
        first_rul = predict_rul(windows[0], dataset_id="FD001")
        last_rul = predict_rul(windows[-1], dataset_id="FD001")
        assert last_rul < first_rul

    def test_wrong_shape_raises(self) -> None:
        bad_window = np.zeros((30, 5), dtype=np.float32)
        with pytest.raises(ValueError, match="shape"):
            predict_rul(bad_window, dataset_id="FD001")

    def test_non_ndarray_raises(self) -> None:
        with pytest.raises(TypeError):
            predict_rul([[0.0] * 14] * 30, dataset_id="FD001")  # type: ignore[arg-type]


class TestCheckThresholds:
    def test_below_threshold_alerts(self) -> None:
        alert = check_thresholds(engine_id=5, rul=20.0, threshold=50.0)
        assert alert is not None
        assert alert["engine_id"] == 5
        assert alert["severity"] == "critical"
        assert alert["alert"] is True

    def test_watch_severity(self) -> None:
        alert = check_thresholds(engine_id=7, rul=45.0, threshold=50.0)
        assert alert is not None
        assert alert["severity"] == "watch"

    def test_above_threshold_returns_none(self) -> None:
        assert check_thresholds(engine_id=8, rul=120.0, threshold=50.0) is None

    def test_default_threshold_from_config(self) -> None:
        alert = check_thresholds(engine_id=9, rul=10.0)
        assert alert is not None and alert["threshold"] == 50


class TestCompareToFleet:
    def test_returns_per_sensor_comparison(
        self, processed_fd001: pd.DataFrame
    ) -> None:
        result = compare_to_fleet(processed_fd001, engine_id=1)
        assert isinstance(result, dict)
        sample_sensor = next(iter(result))
        assert sample_sensor.startswith("s")
        assert set(result[sample_sensor]) == {"engine_mean", "fleet_mean", "deviation"}

    def test_deviation_is_difference(self, processed_fd001: pd.DataFrame) -> None:
        result = compare_to_fleet(processed_fd001, engine_id=1)
        for sensor, stats in result.items():
            assert stats["deviation"] == pytest.approx(
                stats["engine_mean"] - stats["fleet_mean"]
            )

    def test_missing_engine_raises(self, processed_fd001: pd.DataFrame) -> None:
        with pytest.raises(ValueError):
            compare_to_fleet(processed_fd001, engine_id=99999)


class TestSensorTrends:
    def test_ranked_by_abs_slope(self, processed_fd001: pd.DataFrame) -> None:
        result = sensor_trends(processed_fd001, engine_id=1)
        slopes = list(result.values())
        for earlier, later in zip(slopes, slopes[1:]):
            assert abs(earlier) >= abs(later)

    def test_all_sensors_present(self, processed_fd001: pd.DataFrame) -> None:
        sensor_count = sum(col.startswith("s") for col in processed_fd001.columns)
        result = sensor_trends(processed_fd001, engine_id=1)
        assert len(result) == sensor_count


class TestDegradationRate:
    def test_returns_positive_ratio(self, processed_fd001: pd.DataFrame) -> None:
        ratio = degradation_rate(processed_fd001, engine_id=1)
        assert isinstance(ratio, float)
        assert ratio > 0

    def test_unknown_engine_raises(self, processed_fd001: pd.DataFrame) -> None:
        with pytest.raises(ValueError):
            degradation_rate(processed_fd001, engine_id=99999)


class TestTimeToCritical:
    def test_already_critical_returns_zero(self) -> None:
        assert time_to_critical(rul=20.0, degradation_rate=1.0) == 0.0

    def test_normal_rate_simple_difference(self) -> None:
        result = time_to_critical(rul=80.0, degradation_rate=1.0)
        assert result == pytest.approx(80.0 - 30.0)

    def test_accelerated_rate_shortens_time(self) -> None:
        normal = time_to_critical(rul=80.0, degradation_rate=1.0)
        accelerated = time_to_critical(rul=80.0, degradation_rate=2.0)
        assert accelerated < normal

    def test_negative_rul_raises(self) -> None:
        with pytest.raises(ValueError):
            time_to_critical(rul=-1.0, degradation_rate=1.0)


class TestRecommendAction:
    def test_returns_non_empty_string(self) -> None:
        diagnosis = {
            "engine_id": 12,
            "rul": 25.0,
            "severity": "critical",
            "degrading_sensors": ["s11", "s12", "s4"],
            "time_to_critical": 0.0,
        }
        recommendation = recommend_action(diagnosis)
        assert isinstance(recommendation, str)
        assert len(recommendation) > 20

    def test_empty_diagnosis_raises(self) -> None:
        with pytest.raises(ValueError):
            recommend_action({})


class TestGenerateReport:
    def test_writes_pdf(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(advisor_tools, "REPO_ROOT", tmp_path)
        diagnosis = {"engine_id": 1, "rul": 25.0, "severity": "critical"}
        recommendation = "Replace HPC stage 3 blade. Ground engine within 5 cycles."
        pdf_path = generate_report(1, diagnosis, recommendation)
        assert pdf_path.exists()
        with pdf_path.open("rb") as pdf_file:
            assert pdf_file.read(4) == b"%PDF"
        assert pdf_path.stat().st_size > 500


class TestFullPipeline:
    """Raw CMAPSS txt -> CDH -> preprocess -> stream -> predict."""

    def test_end_to_end_fd001(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict
    ) -> None:
        raw_txt = REPO_ROOT / "data" / "raw" / "train_FD001.txt"
        raw_df = pd.read_csv(raw_txt, sep=r"\s+", header=None, names=CMAPSS_COLUMNS)
        engine1 = raw_df[raw_df["unit_id"] == 1]
        csv_path = tmp_path / "engine1.csv"
        engine1.to_csv(csv_path, index=False)

        cdh_df, report = handler.handle(csv_path)
        assert report.is_valid
        assert cdh_df["unit_id"].nunique() == 1

        sensor_cols = [f"s{i}" for i in range(1, 22)]
        keep = config["preprocessing"]["expected_sensor_count_after_drop"]
        # Use FD001's pre-computed drop list by re-running detector on the full set
        full = pd.read_csv(raw_txt, sep=r"\s+", header=None, names=CMAPSS_COLUMNS)
        to_drop = preprocess.identify_constant_sensors(full, sensor_cols, keep)
        cleaned = preprocess.drop_sensors(cdh_df, to_drop)
        kept = [col for col in sensor_cols if col not in to_drop]
        normalized, _ = preprocess.normalize_sensors(cleaned, kept, (0.0, 1.0))
        labeled = preprocess.generate_rul_labels(normalized, cap=130)

        windows = list(stream_sensors(labeled, engine_id=1, window_size=30))
        assert len(windows) > 0
        predictions = [predict_rul(window, dataset_id="FD001") for window in windows]
        assert all(isinstance(prediction, float) for prediction in predictions)
        assert predictions[-1] < predictions[0]
