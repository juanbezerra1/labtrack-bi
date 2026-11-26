"""Helpers of the tests: a report written the way Power BI Desktop writes it (PBIR), made from the spec."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from labtrack_bi.report_check import ROLES, VISUAL_TYPES
from labtrack_bi.spec import MEASURES_TABLE, PAGES, Page, Visual

FIELD = re.compile(r"^(?P<table>[^\[]*)\[(?P<name>.+)\]$")
BASE = "https://developer.microsoft.com/json-schemas/"
SCHEMA = BASE + "fabric/item/report/definition/visualContainer/1.5.0/schema.json"
# The three small files that the generator writes as Power BI Desktop writes them, that is, without `$schema`, which
# the schemas of Microsoft list as required; and the schema of each (docs/verification.md, "Three small files").
SMALL_FILE_SCHEMAS = {
    "labtrack.pbip": "fabric/pbip/pbipProperties/1.0.0/schema.json",
    "labtrack.Report/definition.pbir": "fabric/item/report/definitionProperties/2.0.0/schema.json",
    "labtrack.SemanticModel/definition.pbism": "fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
}


def field_json(text: str) -> dict[str, Any]:
    m = FIELD.match(text)
    assert m, text
    table, name = m.group("table"), m.group("name")
    kind = "Column" if table else "Measure"
    return {kind: {"Expression": {"SourceRef": {"Entity": table or MEASURES_TABLE}}, "Property": name}}


def visual_json(v: Visual, name: str, z: int, title: bool = True) -> dict[str, Any]:
    body: dict[str, Any] = {"visualType": VISUAL_TYPES[v.kind][0]}
    if v.fields:
        state: dict[str, Any] = {}
        for well, fields in v.fields:
            role = ROLES[well][0]
            state[role] = {
                "projections": [
                    {"field": field_json(f), "queryRef": f, "nativeQueryRef": f, **({"active": True} if i == 0 else {})}
                    for i, f in enumerate(fields)
                ]
            }
        body["query"] = {"queryState": state}
    if v.kind == "textbox":
        body["objects"] = {"general": [{"properties": {"paragraphs": [{"textRuns": [{"value": v.title}]}]}}]}
    elif title:
        body["visualContainerObjects"] = {
            "title": [{"properties": {"text": {"expr": {"Literal": {"Value": "'" + v.title.replace("'", "''") + "'"}}}}}]
        }
    return {
        "$schema": SCHEMA,
        "name": name,
        "position": {"x": v.x, "y": v.y, "z": z, "height": v.h, "width": v.w, "tabOrder": z},
        "visual": body,
    }


def write_report(folder: Path, pages: tuple[Page, ...] = PAGES, title: bool = True) -> Path:
    """A report folder with one visual.json for each visual of the spec. Returns the folder of the report."""
    report = folder / "labtrack.Report"
    pages_folder = report / "definition" / "pages"
    for number, page in enumerate(pages, start=1):
        page_folder = pages_folder / f"page{number:02d}"
        page_folder.mkdir(parents=True)
        (page_folder / "page.json").write_text(json.dumps({"name": page_folder.name, "displayName": page.name}), encoding="utf-8")
        for index, v in enumerate(page.visuals, start=1):
            visual_folder = page_folder / "visuals" / f"v{index:03d}"
            visual_folder.mkdir(parents=True)
            (visual_folder / "visual.json").write_text(
                json.dumps(visual_json(v, visual_folder.name, index * 1000, title)), encoding="utf-8"
            )
    return report
