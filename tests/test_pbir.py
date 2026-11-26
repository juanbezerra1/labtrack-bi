"""The report skeleton (PBIR): pages, theme, and the small files of the project."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from labtrack_bi import pbir
from labtrack_bi.spec import PAGES

from .support import BASE, SMALL_FILE_SCHEMAS

pytestmark = pytest.mark.seed

REPORT = "labtrack.Report"
MODEL = "labtrack.SemanticModel"
SCHEMAS = os.environ.get("LABTRACK_BI_SCHEMAS")  # a clone of github.com/microsoft/json-schemas


def load(root: Path, relative: str) -> dict:  # type: ignore[type-arg]
    result: dict = json.loads((root / relative).read_text(encoding="utf-8"))  # type: ignore[type-arg]
    return result


def test_the_pages_are_those_of_the_spec_in_order(root: Path) -> None:
    pages = load(root, f"{REPORT}/definition/pages/pages.json")
    assert pages["pageOrder"] == [pbir.page_id(p) for p in PAGES]
    assert pages["activePageName"] == pages["pageOrder"][0]
    for spec in PAGES:
        page = load(root, f"{REPORT}/definition/pages/{pbir.page_id(spec)}/page.json")
        assert page["displayName"] == spec.name and page["name"] == pbir.page_id(spec)
        assert (page["width"], page["height"], page["displayOption"]) == (1280, 720, "FitToPage")
        assert re.fullmatch(r"[0-9a-f]{20}", page["name"])
    assert len({pbir.page_id(p) for p in PAGES}) == len(PAGES)


def test_the_theme_carries_the_palette_and_is_the_one_the_report_uses(root: Path) -> None:
    report = load(root, f"{REPORT}/definition/report.json")
    custom = report["themeCollection"]["customTheme"]
    assert custom == {"name": "LabTrack.json", "reportVersionAtImport": "5.61", "type": "RegisteredResources"}
    theme = load(root, f"{REPORT}/StaticResources/RegisteredResources/LabTrack.json")
    assert theme["name"] == "LabTrack" and tuple(theme["dataColors"]) == pbir.PALETTE
    assert "#fcfcfb" in json.dumps(theme["visualStyles"])
    base = report["themeCollection"]["baseTheme"]["name"]
    assert (root / REPORT / "StaticResources/SharedResources/BaseThemes" / f"{base}.json").exists()
    for package in report["resourcePackages"]:
        for item in package["items"]:
            folder = "RegisteredResources" if package["type"] == "RegisteredResources" else "SharedResources"
            assert (root / REPORT / "StaticResources" / folder / item["path"]).exists(), item


def test_the_small_files_are_written_as_power_bi_desktop_writes_them(root: Path) -> None:
    """These four have no $schema in the sample project that Microsoft publishes, and the schema of the editor
    settings does not even list a field that Desktop writes in it. The structure is the one of that sample."""
    assert load(root, "labtrack.pbip") == {
        "version": "1.0",
        "artifacts": [{"report": {"path": REPORT}}],
        "settings": {"enableAutoRecovery": True},
    }
    assert load(root, f"{REPORT}/definition.pbir") == {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{MODEL}"}}}
    assert load(root, f"{MODEL}/definition.pbism") == {"version": "4.1", "settings": {}}
    assert set(load(root, f"{MODEL}/.pbi/editorSettings.json")) == {
        "version",
        "autodetectRelationships",
        "parallelQueryLoading",
        "relationshipImportEnabled",
        "shouldNotifyUserOfNameConflictResolution",
    }


@pytest.mark.parametrize("kind", ["Report", "SemanticModel"])
def test_the_platform_files(root: Path, kind: str) -> None:
    folder = REPORT if kind == "Report" else MODEL
    data = load(root, f"{folder}/.platform")
    assert data["$schema"].endswith("/gitIntegration/platformProperties/2.0.0/schema.json")
    assert data["metadata"] == {"type": kind, "displayName": "labtrack"}
    assert data["config"]["version"] == "2.0" and re.fullmatch(r"[0-9a-f-]{36}", data["config"]["logicalId"])
    other = load(root, f"{MODEL if kind == 'Report' else REPORT}/.platform")
    assert other["config"]["logicalId"] != data["config"]["logicalId"]


def test_the_ids_are_stable() -> None:
    assert pbir.page_id(PAGES[0]) == pbir.page_id(PAGES[0])
    assert pbir.logical_id("Report") == pbir.logical_id("Report") != pbir.logical_id("SemanticModel")


def test_the_report_has_no_visuals_yet(root: Path) -> None:
    """The visuals are built in Power BI Desktop; `labtrack-bi check-report` compares them with the spec."""
    assert not list((root / REPORT / "definition" / "pages").rglob("visual.json"))


def schema_tools(schemas: Path):  # type: ignore[no-untyped-def]
    """The `jsonschema` module and a registry that finds, in the clone of Microsoft's schemas, every schema a `$ref` names."""
    jsonschema = pytest.importorskip("jsonschema")
    referencing = pytest.importorskip("referencing")
    from referencing.jsonschema import DRAFT7

    def retrieve(uri: str):  # type: ignore[no-untyped-def]
        return referencing.Resource.from_contents(
            json.loads((schemas / uri.split("#")[0][len(BASE) :]).read_text(encoding="utf-8")), default_specification=DRAFT7
        )

    return jsonschema, referencing.Registry(retrieve=retrieve)


@pytest.mark.skipif(not SCHEMAS, reason="set LABTRACK_BI_SCHEMAS to a clone of github.com/microsoft/json-schemas")
def test_the_json_files_are_valid_against_the_schemas_of_microsoft(root: Path) -> None:
    schemas = Path(str(SCHEMAS))
    jsonschema, registry = schema_tools(schemas)
    checked = 0
    for path in sorted(root.rglob("*.json")):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        document = json.loads(path.read_text(encoding="utf-8-sig"))
        uri = document.get("$schema") if isinstance(document, dict) else None
        if not uri or not uri.startswith(BASE) or not (schemas / uri[len(BASE) :]).exists():
            continue
        schema = json.loads((schemas / uri[len(BASE) :]).read_text(encoding="utf-8"))
        errors = list(jsonschema.Draft7Validator(schema, registry=registry).iter_errors(document))
        assert not errors, f"{path.relative_to(root)}: {errors[0].message}"
        checked += 1
    assert checked >= 7


@pytest.mark.skipif(not SCHEMAS, reason="set LABTRACK_BI_SCHEMAS to a clone of github.com/microsoft/json-schemas")
@pytest.mark.parametrize("relative", list(SMALL_FILE_SCHEMAS))
def test_the_three_small_files_only_lack_the_schema_line(root: Path, relative: str) -> None:
    """The generator writes these files as Desktop does, without `$schema`, which the schemas list as required. That is
    the only thing the schemas may object to, and the line that the build guide gives as first aid makes each one valid."""
    schemas = Path(str(SCHEMAS))
    jsonschema, registry = schema_tools(schemas)
    schema = json.loads((schemas / SMALL_FILE_SCHEMAS[relative]).read_text(encoding="utf-8"))
    assert schema["$id"] == BASE + SMALL_FILE_SCHEMAS[relative]
    validator = jsonschema.Draft7Validator(schema, registry=registry)
    document = load(root, relative)
    assert "$schema" not in document
    errors = list(validator.iter_errors(document))
    assert len(errors) == 1 and errors[0].validator == "required" and "$schema" in errors[0].message, [e.message for e in errors]
    assert not list(validator.iter_errors({"$schema": schema["$id"], **document}))
