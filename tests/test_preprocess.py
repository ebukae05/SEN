"""Tests for the deterministic preprocessing pipeline."""

from __future__ import annotations

import pickle
import sys
from pathlib import Path

import pandas as pd
import pytest
from sklearn.preprocessing import MinMaxScaler

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import preprocess  # noqa: E402
from preprocess import (  # noqa: E402
    drop_sensors,
    generate_rul_labels,
    identify_constant_sensors,
    load_raw,
    normalize_sensors,
    preprocess_dataset,
    save_processed,
)

DATASET_IDS = ["FD001", "FD002", "FD003", "FD004"]
SENSOR_COLUMNS = [f"s{i}" for i in range(1, 22)]


@pytest.fixture
def config() -> dict:
    """Loaded project config."""
    return preprocess._load_config()


@pytest.fixture
def fd001_raw(config: dict) -> pd.DataFrame:
    """Raw FD001 DataFrame, loaded once per test."""
    return load_raw("FD001", config)


class TestLoadRaw:
    @pytest.mark.parametrize("dataset_id", DATASET_IDS)
    def test_loads_all_datasets(self, dataset_id: str, config: dict) -> None:
        df = load_raw(dataset_id, config)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert list(df.columns) == config["data"]["schema"]["columns"]
        assert df["unit_id"].nunique() > 0

    def test_unknown_dataset_raises(self, config: dict) -> None:
        with pytest.raises(ValueError, match="Unknown dataset_id"):
            load_raw("FD999", config)


class TestIdentifyConstantSensors:
    def test_returns_lowest_variance(self, fd001_raw: pd.DataFrame) -> None:
        dropped = identify_constant_sensors(fd001_raw, SENSOR_COLUMNS, keep_count=14)
        assert len(dropped) == 7
        # FD001's true constants must be in the drop list
        for known_constant in ["s1", "s5", "s10", "s16", "s18", "s19"]:
            assert known_constant in dropped

    def test_keep_count_too_large_raises(self, fd001_raw: pd.DataFrame) -> None:
        with pytest.raises(ValueError):
            identify_constant_sensors(fd001_raw, SENSOR_COLUMNS, keep_count=100)

    def test_keep_count_zero_raises(self, fd001_raw: pd.DataFrame) -> None:
        with pytest.raises(ValueError):
            identify_constant_sensors(fd001_raw, SENSOR_COLUMNS, keep_count=0)

    @pytest.mark.parametrize("dataset_id", DATASET_IDS)
    def test_always_converges_to_target(self, dataset_id: str, config: dict) -> None:
        df = load_raw(dataset_id, config)
        keep = config["preprocessing"]["expected_sensor_count_after_drop"]
        dropped = identify_constant_sensors(df, SENSOR_COLUMNS, keep_count=keep)
        retained = [col for col in SENSOR_COLUMNS if col not in dropped]
        assert len(retained) == keep


class TestDropSensors:
    def test_drops_specified_columns(self) -> None:
        df = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
        result = drop_sensors(df, ["b"])
        assert list(result.columns) == ["a", "c"]

    def test_does_not_mutate_input(self) -> None:
        df = pd.DataFrame({"a": [1], "b": [2]})
        drop_sensors(df, ["a"])
        assert "a" in df.columns


class TestNormalizeSensors:
    def test_output_in_range(self, fd001_raw: pd.DataFrame) -> None:
        sensors_to_normalize = ["s2", "s3", "s4", "s7"]
        normalized, scaler = normalize_sensors(
            fd001_raw, sensors_to_normalize, (0.0, 1.0)
        )
        for col in sensors_to_normalize:
            assert normalized[col].min() >= 0.0
            assert normalized[col].max() <= 1.0
        assert isinstance(scaler, MinMaxScaler)

    def test_missing_column_raises(self, fd001_raw: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="missing columns"):
            normalize_sensors(fd001_raw, ["s_does_not_exist"], (0.0, 1.0))


class TestGenerateRulLabels:
    def test_piecewise_linear(self) -> None:
        df = pd.DataFrame({
            "unit_id": [1, 1, 1, 1, 2, 2],
            "cycle": [1, 2, 3, 4, 1, 2],
        })
        labeled = generate_rul_labels(df, cap=130)
        # Engine 1: max_cycle=4, so RUL = [3, 2, 1, 0]
        assert labeled[labeled["unit_id"] == 1]["RUL"].tolist() == [3, 2, 1, 0]
        # Engine 2: max_cycle=2, so RUL = [1, 0]
        assert labeled[labeled["unit_id"] == 2]["RUL"].tolist() == [1, 0]

    def test_cap_clips_high_rul(self) -> None:
        df = pd.DataFrame({
            "unit_id": [1] * 200,
            "cycle": list(range(1, 201)),
        })
        labeled = generate_rul_labels(df, cap=130)
        assert labeled["RUL"].max() == 130
        assert (labeled["RUL"] <= 130).all()

    def test_invalid_cap_raises(self) -> None:
        df = pd.DataFrame({"unit_id": [1], "cycle": [1]})
        with pytest.raises(ValueError):
            generate_rul_labels(df, cap=0)


class TestSaveProcessed:
    def test_writes_csv_and_scaler(
        self, tmp_path: Path, fd001_raw: pd.DataFrame, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(preprocess, "REPO_ROOT", tmp_path)
        config = {
            "paths": {"data_processed": "data/processed"},
            "data": {
                "processed_filename": "train_{dataset_id}_clean.csv",
                "scaler_filename": "scaler_{dataset_id}.pkl",
            },
        }
        scaler = MinMaxScaler().fit(fd001_raw[["s2", "s3"]])
        csv_path, scaler_path = save_processed(fd001_raw, scaler, "FD001", config)
        assert csv_path.exists() and scaler_path.exists()
        assert csv_path.name == "train_FD001_clean.csv"
        with scaler_path.open("rb") as scaler_file:
            loaded = pickle.load(scaler_file)
        assert isinstance(loaded, MinMaxScaler)


class TestPreprocessDatasetEndToEnd:
    @pytest.mark.parametrize("dataset_id", DATASET_IDS)
    def test_full_pipeline_per_dataset(
        self, dataset_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
        config: dict,
    ) -> None:
        original_raw = REPO_ROOT / config["paths"]["data_raw"]
        staged_raw = tmp_path / config["paths"]["data_raw"]
        staged_raw.mkdir(parents=True)
        for raw_file in original_raw.glob("*.txt"):
            (staged_raw / raw_file.name).write_bytes(raw_file.read_bytes())
        monkeypatch.setattr(preprocess, "REPO_ROOT", tmp_path)

        cleaned = preprocess_dataset(dataset_id)

        keep_count = config["preprocessing"]["expected_sensor_count_after_drop"]
        rul_cap = config["preprocessing"]["rul_cap"]
        retained_sensors = [col for col in SENSOR_COLUMNS if col in cleaned.columns]
        assert len(retained_sensors) == keep_count
        assert "RUL" in cleaned.columns
        assert cleaned["RUL"].max() <= rul_cap
        assert cleaned["RUL"].min() >= 0
        for sensor in retained_sensors:
            assert cleaned[sensor].min() >= -1e-9
            assert cleaned[sensor].max() <= 1.0 + 1e-9
        out_csv = (
            tmp_path / config["paths"]["data_processed"]
            / f"train_{dataset_id}_clean.csv"
        )
        out_scaler = (
            tmp_path / config["paths"]["data_processed"]
            / f"scaler_{dataset_id}.pkl"
        )
        assert out_csv.exists() and out_scaler.exists()
