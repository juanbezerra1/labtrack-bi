"""The numbers that Power BI must show."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from labtrack_bi import expected
from labtrack_bi.spec import MEASURES


@pytest.fixture(scope="module")
def numbers(data_dir: Path) -> dict[str, list[list[object]]]:
    return expected.compute(data_dir)


def row(numbers: dict[str, list[list[object]]], check_id: str, **where: object) -> dict[str, object]:
    check = expected.check_by_id(check_id)
    columns = expected.columns_of(check)
    for values in numbers[check_id]:
        record = dict(zip(columns, values, strict=True))
        if all(record[k.replace("__", ".")] == v for k, v in where.items()):
            return record
    raise AssertionError(f"{check_id}: no row with {where}")


def test_there_is_one_check_per_query_in_the_dax_file(root: Path) -> None:
    text = (root / "model/check.dax").read_text(encoding="utf-8")
    assert len(re.findall(r"^EVALUATE", text, flags=re.MULTILINE)) == len(expected.CHECKS) == 13
    assert len({c.id for c in expected.CHECKS}) == len(expected.CHECKS)


def test_the_overall_check_has_every_measure_but_the_time_ones(numbers: dict[str, list[list[object]]]) -> None:
    columns = expected.columns_of(expected.check_by_id("overall"))
    assert columns == [m.name for m in MEASURES if m.name not in expected.TIME_INTELLIGENCE]
    assert len(numbers["overall"]) == 1


def test_the_numbers_of_the_story(numbers: dict[str, list[list[object]]]) -> None:
    overall = row(numbers, "overall")
    assert overall["Sessions"] == 909
    assert overall["Sessions Completed"] == 817
    assert overall["Participants Enrolled"] == 200 and overall["Participants Attended"] == 199
    assert overall["Recordings"] == 1634 and overall["Trials"] == 45806
    assert overall["Target N"] == 231
    assert overall["Visit Retention"] is None, "blank unless one visit is selected"
    assert round(float(overall["Feedback Effect on Force CV"]), 4) == -0.484  # type: ignore[arg-type]
    assert round(float(overall["MDF Change After Fatigue"]), 4) == -11.0094  # type: ignore[arg-type]
    assert round(float(overall["RMS Change After Fatigue"]), 4) == 15.2528  # type: ignore[arg-type]
    assert round(float(overall["Alpha Change Large vs Small Stimulus"]), 4) == -3.9176  # type: ignore[arg-type]


def test_the_statuses_add_up(numbers: dict[str, list[list[object]]]) -> None:
    o = row(numbers, "overall")
    assert o["Sessions"] == o["Sessions Completed"] + o["Sessions Cancelled"] + o["Sessions No Show"] + o["Sessions Scheduled"]  # type: ignore[operator]
    assert o["Sessions Closed"] == o["Sessions"] - o["Sessions Scheduled"]  # type: ignore[operator]
    assert o["Trials"] == o["Valid Trials"] + o["Rejected Trials"]  # type: ignore[operator]
    assert sum(r[1] for r in numbers["by_status"]) == o["Sessions"]  # type: ignore[misc]


def test_the_groups_add_up(numbers: dict[str, list[list[object]]]) -> None:
    o = row(numbers, "overall")
    assert sum(r[1] for r in numbers["by_study"]) == o["Sessions"]  # type: ignore[misc]
    assert sum(r[10] for r in numbers["by_study"]) == o["Recordings"]  # type: ignore[misc]
    assert sum(r[11] for r in numbers["by_study"]) == o["Trials"]  # type: ignore[misc]
    assert sum(r[1] for r in numbers["by_modality"]) == o["Recordings"]  # type: ignore[misc]
    assert sum(r[2] for r in numbers["by_modality"]) == o["Trials"]  # type: ignore[misc]
    assert sum(r[1] for r in numbers["by_qc"]) == o["Recordings"]  # type: ignore[misc]
    assert sum(r[1] for r in numbers["by_reason"]) == o["Rejected Trials"]  # type: ignore[misc]
    assert sum(r[2] for r in numbers["by_age_sex"]) == o["Participants Attended"]  # type: ignore[misc]


def test_what_the_notes_say_is_true(numbers: dict[str, list[list[object]]]) -> None:
    """The notes of the checks quote numbers; here they are checked against the numbers themselves."""
    assert sum(r[3] for r in numbers["by_study"]) == 211 and row(numbers, "overall")["Participants Attended"] == 199  # type: ignore[misc]
    by_year = {r[0]: r for r in numbers["by_year"]}
    assert set(by_year) == {2024, 2025, 2026, 2027}
    assert by_year[2027][1] is None and by_year[2027][4] == by_year[2026][1] and by_year[2027][5] == -1
    months = {r[0]: r for r in numbers["by_month"]}
    assert months["2026-11"][2] is None and months["2026-12"][2] is None and months["2026-10"][2] == 817
    visits = {r[0]: r for r in numbers["by_visit"]}
    assert set(visits) == {1, 2, 3, 4, 5, 6, 7} and visits[1][2] == 1


def test_running_totals_never_decrease(numbers: dict[str, list[list[object]]]) -> None:
    for column in (2, 3):
        values = [r[column] for r in numbers["by_month"] if r[column] is not None]
        assert values == sorted(values)  # type: ignore[type-var]


def test_the_planted_effects_have_the_sign_the_story_needs(numbers: dict[str, list[list[object]]]) -> None:
    groups = {r[0]: r for r in numbers["feedback_by_group"]}
    assert set(groups) == {"Control", "Intervention"}
    assert groups["Intervention"][4] < groups["Control"][4] < 0  # type: ignore[operator]


def test_the_json_and_the_markdown_hold_the_same_rows(root: Path, numbers: dict[str, list[list[object]]]) -> None:
    data = json.loads((root / "docs/expected-numbers.json").read_text(encoding="utf-8"))
    assert [c["id"] for c in data["checks"]] == [c.id for c in expected.CHECKS]
    text = (root / "docs/expected-numbers.md").read_text(encoding="utf-8")
    for check in expected.CHECKS:
        assert f"`{check.id}`" in text


def test_dax_literals() -> None:
    assert expected.dax_literal("O'Neil") == '"O\'Neil"'
    assert expected.dax_literal('say "hi"') == '"say ""hi"""'
    assert expected.dax_literal(2024) == "2024"
    assert expected.dax_column("Calendar.Year-Month") == "'Calendar'[Year-Month]"
    assert expected.dax_column("Session.Status") == "Session[Status]"
