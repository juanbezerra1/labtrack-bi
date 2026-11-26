"""The CSV files of data/ are what the model says they are, and the numbers that matter come out right when worked
out again in the simplest way."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

from labtrack_bi import data as bi_data
from labtrack_bi.spec import RELATIONSHIPS, TABLES, table_by_name

ROWS = {"Calendar": 2192, "Study": 3, "Participant": 200, "Researcher": 12, "Device": 24, "Session": 909, "Recording": 1634, "Trial": 45806}


def rows(data_dir: Path, name: str) -> list[dict[str, str]]:
    with (data_dir / f"{table_by_name(name).csv}.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_the_checksums_match_the_files(data_dir: Path) -> None:
    sums = bi_data.read_sums(data_dir)
    assert sorted(sums) == sorted(f"{t.csv}.csv" for t in TABLES)
    for name, digest in sums.items():
        assert bi_data.sha256(data_dir / name) == digest, name


def test_every_header_of_every_file_is_accounted_for(data_dir: Path) -> None:
    for table in TABLES:
        with (data_dir / f"{table.csv}.csv").open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        assert sorted(header) == sorted(table.source_headers()), table.name


def test_the_row_counts(data_dir: Path) -> None:
    loaded = bi_data.load(data_dir)
    assert {t.name: len(loaded[t.name]) for t in TABLES} == ROWS


def test_the_files_are_utf8_with_unix_line_endings(data_dir: Path) -> None:
    for table in TABLES:
        raw = (data_dir / f"{table.csv}.csv").read_bytes()
        assert b"\r" not in raw and not raw.startswith(b"\xef\xbb\xbf"), table.csv
        raw.decode("utf-8")


def test_the_keys_of_the_dimensions_are_unique_and_every_foreign_key_has_its_row(data_dir: Path) -> None:
    loaded = bi_data.load(data_dir)
    for r in RELATIONSHIPS:
        many_table, many_column = r.many.split(".", 1)
        one_table, one_column = r.one.split(".", 1)
        keys = [row[one_column] for row in loaded[one_table]]
        assert len(keys) == len(set(keys)), f"{r.one} has repeated values"
        missing = {row[many_column] for row in loaded[many_table]} - set(keys)
        assert not missing, f"{r.many} has values that {r.one} does not have: {sorted(map(str, missing))[:5]}"


def test_no_key_is_empty(data_dir: Path) -> None:
    loaded = bi_data.load(data_dir)
    for r in RELATIONSHIPS:
        for side in (r.many, r.one):
            table, column = side.split(".", 1)
            assert all(row[column] is not None for row in loaded[table]), side


@pytest.fixture(scope="module")
def raw(data_dir: Path) -> dict[str, list[dict[str, str]]]:
    return {name: rows(data_dir, name) for name in ("Session", "Recording", "Trial", "Participant")}


def test_sessions_by_status_counted_from_the_csv(raw: dict[str, list[dict[str, str]]]) -> None:
    assert Counter(r["status"] for r in raw["Session"]) == {"completed": 817, "cancelled": 54, "no_show": 23, "scheduled": 15}


def test_participants_attended_counted_from_the_csv(raw: dict[str, list[dict[str, str]]]) -> None:
    attended = {r["participant_key"] for r in raw["Session"] if r["status"] == "completed"}
    assert len(attended) == 199
    assert len({r["participant_key"] for r in raw["Session"]}) == 200
    assert sum(1 for r in raw["Participant"] if r["is_withdrawn"] == "true") == 6


def test_recordings_counted_from_the_csv(raw: dict[str, list[dict[str, str]]]) -> None:
    recordings = raw["Recording"]
    assert len(recordings) == 1634
    assert round(sum(float(r["duration_s"]) for r in recordings) / 3600, 3) == 154.502
    assert round(sum(float(r["size_mb"]) for r in recordings) / 1024, 4) == 10.5025
    qc = Counter(r["qc"] for r in recordings)
    assert qc == {"passed": 1423, "flagged": 137, "rejected": 62, "pending": 12}
    assert round(qc["passed"] / (len(recordings) - qc["pending"]), 6) == 0.877312
    assert sum(1 for r in recordings if r["device_calibrated"] == "false") == 162


def test_trials_counted_from_the_csv(raw: dict[str, list[dict[str, str]]]) -> None:
    trials = raw["Trial"]
    assert len(trials) == 45806
    assert sum(1 for r in trials if r["valid"] == "true") == 42052
    assert Counter(r["reject_reason"] for r in trials if r["valid"] == "false") == {
        "force_overshoot": 1000,
        "electrode_noise": 941,
        "movement_artifact": 909,
        "late_onset": 904,
    }


def test_the_effect_of_the_feedback_counted_from_the_csv(raw: dict[str, list[dict[str, str]]]) -> None:
    def mean(suffix: str) -> float:
        values = [
            float(r["force_cv_pct"])
            for r in raw["Trial"]
            if r["valid"] == "true" and r["force_cv_pct"] != "" and r["condition"].endswith(suffix)
        ]
        return sum(values) / len(values)

    assert round(mean("_fb") - mean("_nofb"), 4) == -0.484
