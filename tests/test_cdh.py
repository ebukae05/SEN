"""Tests for the CDH (Command and Data Handling) layer."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cdh import handler  # noqa: E402
from cdh.handler import (  # noqa: E402
    DataQualityReport,
    apply_schema,
    check_data_quality,
    detect_format,
    handle,
    load_file,
    prioritize_engines,
    validate_required_columns,
)


CMAPSS_COLUMNS = (
    ["unit_id", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]
)


@pytest.fixture
def cdh_config() -> dict:
    """The 'cdh' section of the project config."""
    return handler._load_config()["cdh"]


@pytest.fixture
def cmapss_csv(tmp_path: Path) -> Path:
    """Convert CMAPSS train_FD001.txt to CSV with SEN-standard headers."""
    raw_txt = REPO_ROOT / "data" / "raw" / "train_FD001.txt"
    if not raw_txt.exists():
        pytest.skip(f"CMAPSS source data not available at {raw_txt}")
    df = pd.read_csv(raw_txt, sep=r"\s+", header=None, names=CMAPSS_COLUMNS)
    out = tmp_path / "fd001.csv"
    df.to_csv(out, index=False)
    return out


@pytest.fixture
def manual_json(tmp_path: Path) -> Path:
    """Hand-rolled JSON file in user-defined schema (needs the adapter)."""
    records = [
        {
            "EngineID": 1, "TimeInCycles": 1,
            "OpSet1": 0.0, "OpSet2": 0.0, "OpSet3": 100.0,
            "Sensor1": 518.67, "Sensor2": 641.82,
        },
        {
            "EngineID": 1, "TimeInCycles": 2,
            "OpSet1": 0.0, "OpSet2": 0.0, "OpSet3": 100.0,
            "Sensor1": 518.67, "Sensor2": 642.15,
        },
        {
            "EngineID": 2, "TimeInCycles": 1,
            "OpSet1": 0.0, "OpSet2": 0.0, "OpSet3": 100.0,
            "Sensor1": 518.67, "Sensor2": 641.55,
        },
    ]
    out = tmp_path / "manual.json"
    out.write_text(json.dumps(records), encoding="utf-8")
    return out


@pytest.fixture
def manual_schema_map() -> dict[str, str]:
    """Map the manual JSON's user-defined columns to SEN's internal names."""
    return {
        "EngineID": "unit_id",
        "TimeInCycles": "cycle",
        "OpSet1": "op1",
        "OpSet2": "op2",
        "OpSet3": "op3",
        "Sensor1": "s1",
        "Sensor2": "s2",
    }


class TestDetectFormat:
    def test_csv(self) -> None:
        assert detect_format(Path("foo.csv")) == "csv"

    def test_json(self) -> None:
        assert detect_format(Path("foo.json")) == "json"

    def test_xlsx(self) -> None:
        assert detect_format(Path("foo.xlsx")) == "xlsx"

    def test_uppercase_extension(self) -> None:
        assert detect_format(Path("foo.CSV")) == "csv"

    def test_unsupported_raises(self) -> None:
        with pytest.raises(ValueError, match="Unsupported format"):
            detect_format(Path("foo.parquet"))

    def test_type_check(self) -> None:
        with pytest.raises(TypeError):
            detect_format("foo.csv")  # type: ignore[arg-type]


class TestLoadFile:
    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_file(tmp_path / "nope.csv")

    def test_load_csv(self, cmapss_csv: Path) -> None:
        df = load_file(cmapss_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "unit_id" in df.columns

    def test_load_json(self, manual_json: Path) -> None:
        df = load_file(manual_json)
        assert len(df) == 3
        assert "EngineID" in df.columns

    def test_empty_csv_raises(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.csv"
        empty.write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match="empty"):
            load_file(empty)


class TestApplySchema:
    def test_none_returns_unchanged(self) -> None:
        df = pd.DataFrame({"a": [1], "b": [2]})
        result = apply_schema(df, None)
        assert list(result.columns) == ["a", "b"]

    def test_renames_columns(self) -> None:
        df = pd.DataFrame({"EngineID": [1], "TimeInCycles": [10]})
        result = apply_schema(df, {"EngineID": "unit_id", "TimeInCycles": "cycle"})
        assert list(result.columns) == ["unit_id", "cycle"]

    def test_unknown_user_column_raises(self) -> None:
        df = pd.DataFrame({"a": [1]})
        with pytest.raises(ValueError, match="missing columns"):
            apply_schema(df, {"nonexistent": "unit_id"})


class TestValidateRequiredColumns:
    def test_all_present(self) -> None:
        df = pd.DataFrame({"unit_id": [1], "cycle": [1]})
        assert validate_required_columns(df, ["unit_id", "cycle"]) == []

    def test_some_missing(self) -> None:
        df = pd.DataFrame({"unit_id": [1]})
        assert validate_required_columns(df, ["unit_id", "cycle"]) == ["cycle"]


class TestCheckDataQuality:
    def test_clean_data(self, cdh_config: dict) -> None:
        df = pd.DataFrame({"unit_id": [1, 1, 2], "cycle": [1, 2, 1], "s1": [0.1, 0.2, 0.3]})
        report = check_data_quality(df, cdh_config)
        assert report.is_valid
        assert report.rows_loaded == 3
        assert report.engines_loaded == 2
        assert report.missing_values == 0

    def test_missing_required_column(self, cdh_config: dict) -> None:
        df = pd.DataFrame({"unit_id": [1], "s1": [0.1]})  # no 'cycle'
        report = check_data_quality(df, cdh_config)
        assert not report.is_valid
        assert "cycle" in report.missing_required_columns

    def test_missing_values_flagged(self, cdh_config: dict) -> None:
        df = pd.DataFrame({"unit_id": [1, 2], "cycle": [1, 2], "s1": [0.1, None]})
        report = check_data_quality(df, cdh_config)
        assert report.missing_values == 1
        assert any("missing" in w for w in report.warnings)

    def test_out_of_range_flagged(self, cdh_config: dict) -> None:
        df = pd.DataFrame({"unit_id": [1], "cycle": [1], "s1": [99999.0]})
        report = check_data_quality(df, cdh_config)
        assert report.out_of_range_values >= 1


class TestPrioritizeEngines:
    def test_rul_map_orders_ascending(self) -> None:
        df = pd.DataFrame({
            "unit_id": [1, 1, 2, 2, 3, 3],
            "cycle": [1, 2, 1, 2, 1, 2],
        })
        rul_map = {1: 100.0, 2: 20.0, 3: 60.0}
        result = prioritize_engines(df, rul_map)
        assert result["unit_id"].tolist() == [2, 2, 3, 3, 1, 1]

    def test_fallback_max_cycle(self) -> None:
        df = pd.DataFrame({
            "unit_id": [1, 2, 2, 3, 3, 3],
            "cycle": [1, 1, 2, 1, 2, 3],
        })
        result = prioritize_engines(df, rul_map=None)
        assert result["unit_id"].iloc[0] == 3

    def test_requires_unit_id(self) -> None:
        df = pd.DataFrame({"cycle": [1, 2]})
        with pytest.raises(ValueError, match="unit_id"):
            prioritize_engines(df, None)


class TestHandleEndToEnd:
    def test_cmapss_csv(self, cmapss_csv: Path) -> None:
        df, report = handle(cmapss_csv)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(report, DataQualityReport)
        assert report.is_valid
        assert report.engines_loaded == 100
        assert {"unit_id", "cycle"}.issubset(df.columns)

    def test_manual_json_with_schema(
        self, manual_json: Path, manual_schema_map: dict[str, str]
    ) -> None:
        df, report = handle(manual_json, schema_map=manual_schema_map)
        assert report.is_valid
        assert report.engines_loaded == 2
        assert "unit_id" in df.columns
        assert "EngineID" not in df.columns

    def test_rul_prioritization_orders_first_row(
        self, manual_json: Path, manual_schema_map: dict[str, str]
    ) -> None:
        df, _ = handle(
            manual_json,
            schema_map=manual_schema_map,
            rul_map={1: 80.0, 2: 10.0},
        )
        assert df["unit_id"].iloc[0] == 2
