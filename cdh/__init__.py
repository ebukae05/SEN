"""CDH (Command and Data Handling) layer — sensor-agnostic input adapter."""

from cdh.handler import (
    DataQualityReport,
    apply_schema,
    check_data_quality,
    detect_format,
    handle,
    load_file,
    prioritize_engines,
    validate_required_columns,
)

__all__ = [
    "DataQualityReport",
    "apply_schema",
    "check_data_quality",
    "detect_format",
    "handle",
    "load_file",
    "prioritize_engines",
    "validate_required_columns",
]
