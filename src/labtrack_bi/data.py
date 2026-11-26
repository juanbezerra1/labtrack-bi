"""Reads the CSV files the way the Power Query of the model reads them, so that the numbers can be worked out without Power BI.

Every table of the model becomes a list of rows; a row is a dict keyed by the column names of the MODEL ("Session Date",
"Group"), with Python values (int, float, bool, date, datetime, str, None). Empty cells are None, codes are turned into
labels and the columns that Power Query makes are made here too, by the functions of DERIVED: the same rules written a
second time, in Python, which is what the tests compare with the SQL of labtrack-db.
"""

from __future__ import annotations

import csv
import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .spec import TABLES, VALUE_MAPS, Column, Table

Row = dict[str, Any]


class DataError(ValueError):
    pass


def _parse(value: str, column: Column) -> Any:
    if value == "":
        return None
    kind = column.dtype
    if kind == "int64":
        return int(value)
    if kind == "double":
        return float(value)
    if kind == "boolean":
        if value not in ("true", "false"):
            raise DataError(f"{column.name}: {value!r} is not a boolean")
        return value == "true"
    if kind == "date":
        return date.fromisoformat(value)
    if kind == "datetime":
        return datetime.fromisoformat(value)
    return value


def _label(value: str) -> str:
    return " ".join(word[:1].upper() + word[1:].lower() for word in value.replace("_", " ").split(" "))


def _transform(value: Any, column: Column) -> Any:
    if value is None or column.transform is None:
        return value
    if column.transform == "label":
        return _label(value)
    return VALUE_MAPS[column.transform].get(value, value)


def _age_band(row: Row) -> str:
    age = row["Age at Consent"]
    return "Under 30" if age < 30 else "30-44" if age < 45 else "45-59" if age < 60 else "60+"


def _age_band_order(row: Row) -> int:
    age = row["Age at Consent"]
    return 1 if age < 30 else 2 if age < 45 else 3 if age < 60 else 4


def _feedback(row: Row) -> str | None:
    condition: str = row["Condition"]
    return "Off" if condition.endswith("_nofb") else "On" if condition.endswith("_fb") else None


def _hold_level(row: Row) -> int | None:
    condition: str = row["Condition"]
    return int(condition[5:7]) if condition.startswith("hold_") else None


def _fatigue(row: Row) -> str | None:
    condition: str = row["Condition"]
    return ("Post" if condition.endswith("_post") else "Pre") if condition.startswith("fatigue_") else None


def _stimulus(row: Row) -> str | None:
    condition: str = row["Condition"]
    return ("Large" if condition.endswith("_large") else "Small") if condition.startswith("stimulus_") else None


DERIVED: dict[tuple[str, str], Callable[[Row], Any]] = {
    ("Calendar", "Year-Quarter"): lambda r: f"{r['Year']} Q{r['Quarter']}",
    ("Participant", "Status"): lambda r: "Withdrawn" if r["Is Withdrawn"] else "Active",
    ("Participant", "Age at Consent"): lambda r: r["Consent Date"].year - r["Birth Year"],
    ("Participant", "Age Band"): _age_band,
    ("Participant", "Age Band Order"): _age_band_order,
    ("Recording", "Calibration"): lambda r: "Calibrated" if r["Device Calibrated"] else "Not calibrated",
    ("Trial", "Validity"): lambda r: "Valid" if r["Valid"] else "Rejected",
    ("Trial", "Feedback"): _feedback,
    ("Trial", "Hold Level"): _hold_level,
    ("Trial", "Fatigue Phase"): _fatigue,
    ("Trial", "Stimulus Size"): _stimulus,
}


def read_table(table: Table, folder: Path) -> list[Row]:
    """The rows of one table, as the model will hold them."""
    path = folder / f"{table.csv}.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        expected = table.source_headers()
        if sorted(header) != sorted(expected):
            raise DataError(f"{path.name}: the columns are {header}, the model accounts for {expected}")
        position = {name: i for i, name in enumerate(header)}
        rows: list[Row] = []
        for record in reader:
            row: Row = {}
            for column in table.columns:
                if column.source:
                    row[column.name] = _transform(_parse(record[position[column.source]], column), column)
                else:
                    row[column.name] = DERIVED[(table.name, column.name)](row)
            rows.append(row)
    return rows


@dataclass
class Data:
    tables: dict[str, list[Row]]

    def __getitem__(self, name: str) -> list[Row]:
        return self.tables[name]


def load(folder: Path) -> Data:
    missing = [t.name for t in TABLES if not (folder / f"{t.csv}.csv").exists()]
    if missing:
        raise DataError(f"the files of {missing} are not in {folder}")
    return Data({t.name: read_table(t, folder) for t in TABLES})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_sums(folder: Path) -> dict[str, str]:
    """SHA256SUMS: file name -> hash."""
    sums: dict[str, str] = {}
    for line in (folder / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, _, name = line.partition("  ")
            sums[name.strip()] = digest.strip()
    return sums
