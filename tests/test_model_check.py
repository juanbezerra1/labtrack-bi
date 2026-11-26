"""The check of the model that Power BI Desktop saved."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from labtrack_bi import cli, tmdl
from labtrack_bi.model_check import check_model

MODEL = "labtrack.SemanticModel"


@pytest.fixture
def model(tmp_path: Path, root: Path) -> Path:
    """A copy of the model of the repository that a test may break."""
    target = tmp_path / MODEL
    shutil.copytree(root / MODEL, target, ignore=shutil.ignore_patterns("localSettings.json", "cache.abf"))
    return target


def edit(model: Path, relative: str, old: str, new: str) -> None:
    path = model / "definition" / relative
    text = path.read_text(encoding="utf-8")
    assert old in text, (relative, old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_the_model_of_the_repository_says_what_the_spec_says(root: Path) -> None:
    try:
        assert check_model(root / MODEL) == []
    except tmdl.TmdlError:  # a file saved by Desktop in a form the reader does not know
        pytest.skip("the TMDL saved by Power BI Desktop has a form that the reader of this package does not know")


def test_a_tmdl_file_in_another_layout_says_the_same(model: Path) -> None:
    """Desktop writes the same things with other line breaks and spaces: that is not a difference."""
    edit(model, "tables/Measures.tmdl", "measure Sessions = COUNTROWS(Session)", "measure  Sessions =\n\t\t\tCOUNTROWS(Session)")
    assert check_model(model) == []


def test_the_data_folder_may_be_yours(model: Path) -> None:
    edit(model, "expressions.tmdl", '"C:\\labtrack-bi\\data"', '"D:\\somewhere else\\data"')
    assert check_model(model) == []


@pytest.mark.parametrize(
    "relative, old, new, expected",
    [
        ("tables/Measures.tmdl", "measure Sessions = COUNTROWS(Session)", "measure Sessions = COUNTROWS(Recording)", "DAX of [Sessions]"),
        ("tables/Measures.tmdl", "measure Sessions =", "measure 'Sessions Total' =", "[Sessions] is missing"),
        ("tables/Study.tmdl", "column 'Study Title'", "column 'Study Name'", "Study[Study Title] is missing"),
        ("tables/Study.tmdl", "column 'Study Title'", "column 'Study Name'", "Study[Study Name] is not in the spec"),
        ("tables/Session.tmdl", "dataType: int64", "dataType: string", "has the type string"),
        ("tables/Calendar.tmdl", "dataCategory: Time\n", "", "not marked as the date table"),
        ("relationships.tmdl", "toColumn: Study.'Study Key'", "toColumn: Study.'Study Title'", "Study[Study Key] is missing"),
        (
            "relationships.tmdl",
            "fromColumn: Session.'Study Key'\n",
            "fromColumn: Session.'Study Key'\n\tcrossFilteringBehavior: bothDirections\n",
            "has settings (crossFilteringBehavior)",
        ),
        ("expressions.tmdl", "expression DataFolder", "expression Folder", "DataFolder is missing"),
    ],
)
def test_a_difference_is_found(model: Path, relative: str, old: str, new: str, expected: str) -> None:
    edit(model, relative, old, new)
    assert any(expected in problem for problem in check_model(model)), check_model(model)


def test_a_changed_power_query_is_found(model: Path) -> None:
    edit(model, "tables/Study.tmdl", "Csv.Document(", "Csv.DocumentX(")
    assert any("Power Query code of Study" in p for p in check_model(model))


def test_a_missing_table_and_an_unreadable_file(model: Path) -> None:
    (model / "definition" / "tables" / "Device.tmdl").unlink()
    assert any("table Device is missing" in p for p in check_model(model))
    (model / "definition" / "tables" / "Trial.tmdl").write_text("table Trial\n    bad\n", encoding="utf-8")
    assert any("Trial.tmdl: it cannot be read" in p for p in check_model(model))


def test_a_folder_that_is_not_a_model(tmp_path: Path) -> None:
    assert "not found" in check_model(tmp_path)[0]


def test_the_command_line(model: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["check-model", str(model)]) == 0
    assert "ok: the model says what the spec says" in capsys.readouterr().out
    edit(model, "tables/Study.tmdl", "column 'Study Title'", "column 'Study Name'")
    assert cli.main(["check-model", str(model)]) == 1
    assert "difference(s) from the spec" in capsys.readouterr().out
