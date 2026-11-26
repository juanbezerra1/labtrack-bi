"""The files that `labtrack-bi build` writes are all there and up to date, and they are written the way Git and
Power BI Desktop want them. The project is special: after Desktop has saved it, `build` leaves it alone."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from labtrack_bi import cli, generate, mcode, tmdl
from labtrack_bi.spec import TABLES


def test_every_derived_file_is_up_to_date(root: Path, generated: dict[str, bytes]) -> None:
    stale = [
        path
        for path, content in generated.items()
        if not generate.is_project_path(path) and (not (root / path).exists() or (root / path).read_bytes() != content)
    ]
    assert stale == [], "run `labtrack-bi build` and commit the result"


@pytest.mark.seed
def test_the_project_is_up_to_date_while_desktop_has_not_saved_it(root: Path, generated: dict[str, bytes]) -> None:
    assert generate.project_state(root, generated) == "pristine"


def test_generated_files_use_lf_and_end_with_a_newline(generated: dict[str, bytes]) -> None:
    for path, content in generated.items():
        if "BaseThemes" in path:
            continue  # the base theme of Microsoft is kept as it came
        assert b"\r" not in content, path
        assert content.endswith(b"\n"), path
        content.decode("utf-8")


def test_json_files_parse_and_use_two_spaces(generated: dict[str, bytes]) -> None:
    for path, content in generated.items():
        if (
            path.endswith((".json", ".pbip", ".pbir", ".pbism", ".platform"))
            and "BaseThemes" not in path
            and "expected-numbers" not in path
        ):
            assert json.dumps(json.loads(content), indent=2, ensure_ascii=False) + "\n" == content.decode("utf-8"), path


def test_the_power_query_files_hold_the_query_of_the_spec(root: Path) -> None:
    for table in TABLES:
        in_file = (root / f"model/powerquery/{table.name}.pq").read_text(encoding="utf-8")
        assert mcode.query(table).strip() in in_file, table.name


@pytest.mark.seed
def test_the_power_query_files_hold_the_same_m_as_the_model(root: Path) -> None:
    for table in TABLES:
        node = tmdl.parse_one((root / f"labtrack.SemanticModel/definition/tables/{table.name}.tmdl").read_text(encoding="utf-8"))
        partition = node.child("partition")
        assert partition is not None
        assert tmdl.unindent(str(partition.props["source"])).strip() == mcode.query(table).strip()


@pytest.mark.seed
def test_the_tmdl_files_are_indented_with_tabs(root: Path) -> None:
    """Tabs first; spaces are allowed only after the tabs, inside an M or DAX block."""
    for path in (root / "labtrack.SemanticModel" / "definition").rglob("*.tmdl"):
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
            assert not line.startswith(" "), (path.name, number)
            assert not re.match(r"\t* +\t", line), (path.name, number)


@pytest.mark.seed
def test_the_generated_paths_match_what_the_pbip_file_points_to(root: Path) -> None:
    pbip = json.loads((root / "labtrack.pbip").read_text(encoding="utf-8"))
    report = root / pbip["artifacts"][0]["report"]["path"]
    definition = json.loads((report / "definition.pbir").read_text(encoding="utf-8"))
    model = (report / definition["datasetReference"]["byPath"]["path"]).resolve()
    assert model == (root / "labtrack.SemanticModel").resolve()
    assert (model / "definition.pbism").exists() and (model / "definition" / "model.tmdl").exists()


@pytest.fixture
def fake_files(generated: dict[str, bytes], monkeypatch: pytest.MonkeyPatch) -> dict[str, bytes]:
    """`generate.files` answers from the cache, so that the commands below do not recompute everything each time."""
    monkeypatch.setattr(generate, "files", lambda _root: generated)
    return generated


def test_build_writes_everything_the_first_time_and_check_agrees(
    tmp_path: Path, fake_files: dict[str, bytes], capsys: pytest.CaptureFixture[str]
) -> None:
    assert cli.main(["--root", str(tmp_path), "check"]) == 1  # nothing is built yet
    assert cli.main(["--root", str(tmp_path), "build"]) == 0
    assert {p for p in fake_files if (tmp_path / p).exists()} == set(fake_files)
    assert cli.main(["--root", str(tmp_path), "check"]) == 0
    assert generate.project_state(tmp_path, fake_files) == "pristine"
    (tmp_path / "model" / "measures.dax").write_text("changed\n", encoding="utf-8")
    assert cli.main(["--root", str(tmp_path), "check"]) == 1
    assert "out of date: model/measures.dax" in capsys.readouterr().out
    assert cli.main(["--root", str(tmp_path), "build"]) == 0
    assert cli.main(["--root", str(tmp_path), "check"]) == 0


def test_after_desktop_has_saved_the_project_build_leaves_it_alone(
    tmp_path: Path, fake_files: dict[str, bytes], capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(["--root", str(tmp_path), "build"])
    # what Desktop does: it rewrites a file its own way and adds the visuals and the settings of this computer
    saved = tmp_path / "labtrack.Report" / "definition" / "report.json"
    saved.write_text(saved.read_text(encoding="utf-8").replace("  ", "\t"), encoding="utf-8")
    visual = tmp_path / "labtrack.Report" / "definition" / "pages" / "p" / "visuals" / "v" / "visual.json"
    visual.parent.mkdir(parents=True)
    visual.write_text("{}", encoding="utf-8")
    local = tmp_path / "labtrack.SemanticModel" / ".pbi" / "localSettings.json"
    local.write_text("{}", encoding="utf-8")
    assert generate.project_state(tmp_path, fake_files) == "saved"
    before = saved.read_bytes()
    (tmp_path / "docs" / "model.md").write_text("old\n", encoding="utf-8")
    capsys.readouterr()
    assert cli.main(["--root", str(tmp_path), "build"]) == 0
    out = capsys.readouterr().out
    assert "was saved by Power BI Desktop" in out and "docs/model.md" in out
    assert saved.read_bytes() == before and visual.exists()  # the project was not touched
    assert cli.main(["--root", str(tmp_path), "check"]) == 0  # and check does not complain about it
    assert "saved by Power BI Desktop" in capsys.readouterr().out


def test_reset_project_keeps_the_old_folders_as_backup(
    tmp_path: Path, fake_files: dict[str, bytes], capsys: pytest.CaptureFixture[str]
) -> None:
    cli.main(["--root", str(tmp_path), "build"])
    visual = tmp_path / "labtrack.Report" / "definition" / "pages" / "p" / "visuals" / "v" / "visual.json"
    visual.parent.mkdir(parents=True)
    visual.write_text("{}", encoding="utf-8")
    assert cli.main(["--root", str(tmp_path), "build", "--reset-project"]) == 0
    assert (tmp_path / "labtrack.Report.backup" / "definition" / "pages" / "p" / "visuals" / "v" / "visual.json").exists()
    assert (tmp_path / "labtrack.SemanticModel.backup").is_dir()
    assert not visual.exists()
    assert generate.project_state(tmp_path, fake_files) == "pristine"
    shutil.rmtree(tmp_path / "labtrack.Report")
    visual.parent.mkdir(parents=True)
    visual.write_text("{}", encoding="utf-8")
    assert cli.main(["--root", str(tmp_path), "build", "--reset-project"]) == 0
    assert (tmp_path / "labtrack.Report.backup1").is_dir()  # an older backup is never overwritten
