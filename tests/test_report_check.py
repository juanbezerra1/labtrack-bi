"""The check of the report that is built in Power BI Desktop."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from labtrack_bi import cli
from labtrack_bi.report_check import check_report, field_label, format_result, read_report
from labtrack_bi.spec import PAGES

from .support import write_report


def test_a_report_made_from_the_spec_has_no_findings(tmp_path: Path) -> None:
    result = check_report(write_report(tmp_path))
    assert result.findings == []
    assert result.expected == result.matched == sum(len(p.visuals) for p in PAGES)
    assert "No errors." in format_result(result)


def test_visuals_without_a_title_are_found_by_their_fields(tmp_path: Path) -> None:
    result = check_report(write_report(tmp_path, title=False))
    assert result.ok
    assert result.matched == result.expected
    warned = {f.visual for f in result.findings if "found by its fields" in f.message}
    assert "Sessions by month and status" in warned


def test_a_missing_visual_is_an_error(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    victim = next(report.glob("definition/pages/page01/visuals/v010"))
    (victim / "visual.json").unlink()
    result = check_report(report)
    assert not result.ok
    assert [f.visual for f in result.errors] == ["Sessions by month and status"]
    assert "missing" in result.errors[0].message


def test_a_wrong_field_is_an_error(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    path = report / "definition/pages/page01/visuals/v005/visual.json"  # the card Sessions Completed
    data = json.loads(path.read_text(encoding="utf-8"))
    projection = data["visual"]["query"]["queryState"]["Values"]["projections"][0]
    projection["field"]["Measure"]["Property"] = "Sessions Cancelled"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_report(report)
    messages = [f.message for f in result.errors]
    assert any("missing [Sessions Completed]" in m and "unexpected [Sessions Cancelled]" in m for m in messages)


def test_a_wrong_type_is_a_missing_visual(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    path = report / "definition/pages/page01/visuals/v010/visual.json"  # a stacked column chart
    data = json.loads(path.read_text(encoding="utf-8"))
    data["visual"]["visualType"] = "pieChart"
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_report(report)
    assert any(f.visual == "Sessions by month and status" and "missing" in f.message for f in result.errors)
    assert any("extra visual" in f.message and "pieChart" in f.message for f in result.findings)


def test_a_field_in_an_unexpected_well_is_an_error(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    path = report / "definition/pages/page01/visuals/v010/visual.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["visual"]["query"]["queryState"]["Rows"] = {
        "projections": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "Study"}}, "Property": "Study Code"}}}]
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    assert any("unexpected fields in Rows" in f.message for f in check_report(report).errors)


def test_an_aggregated_column_is_shown_as_different(tmp_path: Path) -> None:
    label = field_label(
        {
            "Aggregation": {
                "Expression": {"Column": {"Expression": {"SourceRef": {"Entity": "Trial"}}, "Property": "Force CV"}},
                "Function": 1,
            }
        }
    )
    assert label == "aggregation of Trial[Force CV]"
    assert field_label({"HierarchyLevel": {"Level": "Year"}}) == "hierarchy level Year"


def test_a_moved_visual_is_a_warning_not_an_error(tmp_path: Path) -> None:
    report = write_report(tmp_path)
    path = report / "definition/pages/page02/visuals/v009/visual.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["position"]["x"] += 120
    path.write_text(json.dumps(data), encoding="utf-8")
    result = check_report(report)
    assert result.ok
    assert any("position or size differs" in f.message for f in result.findings)


def test_a_missing_page_and_an_extra_page(tmp_path: Path) -> None:
    report = write_report(tmp_path, pages=PAGES[:3])
    result = check_report(report)
    assert any(f.page == PAGES[3].name and "not in the report" in f.message for f in result.errors)
    extra = report / "definition/pages/page99"
    extra.mkdir()
    (extra / "page.json").write_text(json.dumps({"displayName": "Scratch"}), encoding="utf-8")
    assert any("not in the spec" in f.message for f in check_report(report).findings)


def test_a_folder_that_is_not_pbir_is_refused(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_report(tmp_path)


def test_the_command_line(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = write_report(tmp_path)
    assert cli.main(["--root", str(tmp_path), "check-report", str(report)]) == 0
    assert "No errors." in capsys.readouterr().out
    (report / "definition/pages/page01/visuals/v010/visual.json").unlink()
    assert cli.main(["--root", str(tmp_path), "check-report", str(report)]) == 1
    assert cli.main(["--root", str(tmp_path), "check-report", str(tmp_path / "nowhere")]) == 2
