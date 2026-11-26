"""The DAX of the measures and of the check queries."""

from __future__ import annotations

from pathlib import Path

import pytest

from labtrack_bi import data as bi_data
from labtrack_bi import dax, expected
from labtrack_bi.spec import MEASURES

NAMES = {m.name for m in MEASURES}
FOLDERS = {"1 Counts", "2 Sessions", "3 Time", "4 Recruitment", "5 Quality", "6 Findings"}


@pytest.mark.parametrize("measure", MEASURES, ids=lambda m: m.name)
def test_every_measure_passes_the_linter(measure) -> None:  # type: ignore[no-untyped-def]
    assert dax.lint(measure.dax, measure.name, NAMES) == []


@pytest.mark.parametrize("check", expected.CHECKS, ids=lambda c: c.id)
def test_every_check_query_passes_the_linter(check) -> None:  # type: ignore[no-untyped-def]
    assert dax.lint(expected.dax_query(check), check.id, NAMES) == []


def test_no_measure_depends_on_itself() -> None:
    assert dax.find_cycle(MEASURES) is None


def test_the_cycle_finder_finds_a_cycle() -> None:
    from labtrack_bi.spec import Measure

    a = Measure("A", "[B] + 1", "0", "1 Counts", "a")
    b = Measure("B", "[A] + 1", "0", "1 Counts", "b")
    assert dax.find_cycle([a, b]) is not None


def test_the_text_that_a_measure_compares_with_exists_in_the_data(data_dir: Path) -> None:
    data = bi_data.load(data_dir)
    seen = 0
    for measure in MEASURES:
        for table, column, value in dax.literal_checks(measure.dax):
            values = {row[column] for row in data[table.strip("'")]}
            assert value in values, f'{measure.name}: {table}[{column}] = "{value}" never happens in the data'
            seen += 1
    assert seen >= 8


def test_every_measure_is_documented_and_formatted() -> None:
    for m in MEASURES:
        assert m.desc.endswith("."), m.name
        assert m.folder in FOLDERS, m.name
        assert m.fmt, m.name
    assert len(MEASURES) == len(NAMES) == 46


def test_every_measure_is_in_the_dax_file(root: Path) -> None:
    text = (root / "model/measures.dax").read_text(encoding="utf-8")
    for m in MEASURES:
        assert f"// {m.folder} | format: {m.fmt}\n// {m.desc}\n{m.name} =" in text, m.name
        assert m.dax.strip() in text, m.name


@pytest.mark.parametrize(
    "text, expected_message",
    [
        ("SUM(Session[Nope])", "Nope"),
        ("[No Such Measure] + 1", "No Such Measure"),
        ("FOOBAR(1)", "FOOBAR"),
        ("SUM(Trial[Force CV]", "not balanced"),
        ('CALCULATE([Sessions], Session[Status] = "Completed"', "not balanced"),
        ("SUM(Nowhere[Column])", "Nowhere"),
    ],
)
def test_the_linter_finds_the_mistakes(text: str, expected_message: str) -> None:
    messages = dax.lint(text, "test", NAMES)
    assert any(expected_message in m for m in messages), messages


def test_the_linter_accepts_a_correct_measure() -> None:
    assert dax.lint('CALCULATE([Sessions], Session[Status] = "Completed")', "test", NAMES) == []
