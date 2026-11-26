"""Compares the report you built in Power BI Desktop with the spec.

Desktop saves the report as one folder per visual (`labtrack.Report/definition/pages/<page>/visuals/<visual>/visual.json`).
This module reads those files, takes from each the type of the visual, its title, its position and the fields in each
well, and says what is missing or different from `spec.py`. It only reads: it never changes the report.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .spec import MEASURES_TABLE, PAGES, Page, Visual

# the type of visual in the spec -> the names that Power BI gives it in visual.json
VISUAL_TYPES: dict[str, tuple[str, ...]] = {
    "textbox": ("textbox",),
    "slicer": ("slicer",),
    "card": ("card", "cardVisual"),
    "stackedColumn": ("columnChart",),
    "clusteredColumn": ("clusteredColumnChart",),
    "clusteredBar": ("clusteredBarChart",),
    "line": ("lineChart",),
    "table": ("tableEx",),
}
# the well of the spec -> the names of the data role in visual.json (the first one is the usual one)
ROLES: dict[str, tuple[str, ...]] = {
    "X-axis": ("Category",),
    "Y-axis": ("Y",),
    "Legend": ("Series", "Legend"),
    "Tooltips": ("Tooltips",),
    "Columns": ("Values",),
    "Field": ("Values",),
    "Fields": ("Values", "Data"),
}
POSITION_TOLERANCE = 8.0  # pixels
NEAREST_LIMIT = 80.0  # pixels: how far a visual may be from the spec to be taken as that visual


@dataclass(frozen=True)
class Built:
    """A visual as it was saved by Power BI Desktop."""

    page: str
    folder: str
    kind: str
    title: str | None
    text: str | None
    x: float
    y: float
    w: float
    h: float
    roles: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def fields(self) -> frozenset[str]:
        return frozenset(f for fs in self.roles.values() for f in fs)


@dataclass(frozen=True)
class Finding:
    severity: str  # "error" or "warning"
    page: str
    visual: str
    message: str

    def __str__(self) -> str:
        where = f"{self.page}: {self.visual}" if self.visual else self.page
        return f"{self.severity.upper():7} {where}: {self.message}"


@dataclass(frozen=True)
class Result:
    findings: list[Finding]
    expected: int  # visuals in the spec
    matched: int  # visuals of the spec that were found with the right type and fields

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def ok(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------------------------------------------
# reading
# ---------------------------------------------------------------------------------------------------------------
def _json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def _literal(node: Any) -> str | None:
    """The text of {"expr": {"Literal": {"Value": "'text'"}}}, or None."""
    value = (((node or {}).get("expr") or {}).get("Literal") or {}).get("Value") if isinstance(node, dict) else None
    if isinstance(value, str) and len(value) >= 2 and value[0] == value[-1] == "'":
        return value[1:-1].replace("''", "'")
    return None


def field_label(node: dict[str, Any]) -> str:
    """'Table[Column]' for a column, '[Measure]' for a measure of the Measures table, and something recognisably
    different for what the spec never uses (an aggregation of a column, a level of a hierarchy)."""
    for key in ("Column", "Measure"):
        if key in node:
            body = node[key]
            entity = ((body.get("Expression") or {}).get("SourceRef") or {}).get("Entity", "?")
            prop = body.get("Property", "?")
            return f"[{prop}]" if key == "Measure" and entity == MEASURES_TABLE else f"{entity}[{prop}]"
    if "Aggregation" in node:
        inner = field_label(node["Aggregation"].get("Expression") or {})
        return f"aggregation of {inner}"
    if "HierarchyLevel" in node:
        level = node["HierarchyLevel"]
        return f"hierarchy level {level.get('Level', '?')}"
    return "unknown field"


def _built(page: str, folder: Path) -> Built | None:
    path = folder / "visual.json"
    if not path.exists():
        return None
    data = _json(path)
    body = data.get("visual")
    if not isinstance(body, dict):  # a group of visuals has no "visual"
        return None
    position = data.get("position") or {}
    containers = body.get("visualContainerObjects") or {}
    title = None
    if containers.get("title"):
        title = _literal((containers["title"][0].get("properties") or {}).get("text"))
    text = None
    if body.get("visualType") == "textbox":
        runs = [
            run.get("value", "")
            for general in (body.get("objects") or {}).get("general", [])
            for paragraph in (general.get("properties") or {}).get("paragraphs", [])
            for run in paragraph.get("textRuns", [])
        ]
        text = " ".join(r for r in runs if r) or None
    roles: dict[str, tuple[str, ...]] = {}
    for role, state in ((body.get("query") or {}).get("queryState") or {}).items():
        roles[role] = tuple(field_label(p.get("field") or {}) for p in state.get("projections", []))
    return Built(
        page,
        folder.name,
        str(body.get("visualType", "")),
        title,
        text,
        float(position.get("x", 0)),
        float(position.get("y", 0)),
        float(position.get("width", 0)),
        float(position.get("height", 0)),
        roles,
    )


def read_report(report_folder: Path) -> dict[str, list[Built]]:
    """Display name of the page -> its visuals, for every page of the report folder."""
    pages_folder = report_folder / "definition" / "pages"
    if not pages_folder.is_dir():
        raise FileNotFoundError(f"{pages_folder} not found: this is not a report in the PBIR format")
    pages: dict[str, list[Built]] = {}
    for page_json in sorted(pages_folder.glob("*/page.json")):
        name = str(_json(page_json).get("displayName", page_json.parent.name))
        visuals_folder = page_json.parent / "visuals"
        found = [b for f in sorted(visuals_folder.iterdir()) if f.is_dir() and (b := _built(name, f))] if visuals_folder.is_dir() else []
        pages[name] = found
    return pages


# ---------------------------------------------------------------------------------------------------------------
# comparing
# ---------------------------------------------------------------------------------------------------------------
def _spec_fields(v: Visual) -> frozenset[str]:
    return frozenset(f for _, fs in v.fields for f in fs)


def _distance(v: Visual, b: Built) -> float:
    return abs(v.x - b.x) + abs(v.y - b.y)


def _match(v: Visual, candidates: list[Built]) -> tuple[Built | None, str]:
    """The visual that was built for `v`: by title, else by fields, else the nearest of the same type."""
    same = [b for b in candidates if b.kind in VISUAL_TYPES[v.kind]]
    for b in same:
        if (b.title and b.title.strip().lower() == v.title.strip().lower()) or (
            v.kind == "textbox" and b.text and v.title.strip().lower() in b.text.strip().lower()
        ):
            return b, "title"
    wanted = _spec_fields(v)
    if wanted:
        for b in same:
            if b.fields == wanted:
                return b, "fields"
    near = sorted(same, key=lambda b: _distance(v, b))
    if near and _distance(v, near[0]) <= NEAREST_LIMIT:
        return near[0], "position"
    return None, ""


def _compare_fields(page: str, v: Visual, b: Built) -> list[Finding]:
    out: list[Finding] = []
    for well, wanted in v.fields:
        names = ROLES.get(well, (well,))
        have = next((b.roles[n] for n in names if n in b.roles), ())
        if set(have) == set(wanted):
            continue
        missing = [f for f in wanted if f not in have]
        extra = [f for f in have if f not in wanted]
        parts = []
        if missing:
            parts.append("missing " + ", ".join(missing))
        if extra:
            parts.append("unexpected " + ", ".join(extra))
        out.append(Finding("error", page, v.title, f"well {well}: " + "; ".join(parts)))
    known = {n for well, _ in v.fields for n in ROLES.get(well, (well,))}
    for role, fields in b.roles.items():
        if role not in known and fields:
            out.append(Finding("error", page, v.title, f"unexpected fields in {role}: " + ", ".join(fields)))
    return out


def compare(built: dict[str, list[Built]], pages: tuple[Page, ...] = PAGES) -> Result:
    findings: list[Finding] = []
    expected = matched = 0
    for page in pages:
        expected += len(page.visuals)
        candidates = list(built.get(page.name, []))
        if page.name not in built:
            findings.append(Finding("error", page.name, "", "the page is not in the report"))
            continue
        for v in page.visuals:
            found, how = _match(v, candidates)
            if found is None:
                same = [b for b in candidates if b.kind in VISUAL_TYPES[v.kind]]
                hint = f" (the report has {len(same)} unmatched {VISUAL_TYPES[v.kind][0]})" if same else ""
                findings.append(
                    Finding(
                        "error",
                        page.name,
                        v.title,
                        f"missing: a {v.kind} with these fields {', '.join(sorted(_spec_fields(v))) or '-'}{hint}",
                    )
                )
                continue
            candidates.remove(found)
            problems = _compare_fields(page.name, v, found)
            findings.extend(problems)
            if not problems:
                matched += 1
            if how == "position":
                findings.append(Finding("warning", page.name, v.title, "found by its position: set the title as in the spec"))
            elif how == "fields" and v.kind not in ("card", "slicer", "textbox"):
                findings.append(Finding("warning", page.name, v.title, "found by its fields: set the title as in the spec"))
            moved = max(abs(found.x - v.x), abs(found.y - v.y), abs(found.w - v.w), abs(found.h - v.h))
            if moved > POSITION_TOLERANCE:
                findings.append(
                    Finding(
                        "warning",
                        page.name,
                        v.title,
                        f"position or size differs from the spec by {math.ceil(moved)} px (spec: x={v.x} y={v.y} w={v.w} h={v.h})",
                    )
                )
        for b in candidates:
            label = b.title or b.text or b.folder
            findings.append(Finding("warning", page.name, "", f"extra visual not in the spec: {b.kind} '{label}'"))
    known = {p.name for p in pages}
    for name in built:
        if name not in known:
            findings.append(Finding("warning", name, "", "a page that is not in the spec"))
    return Result(findings, expected, matched)


def check_report(report_folder: Path) -> Result:
    return compare(read_report(report_folder))


def format_result(result: Result) -> str:
    lines = [str(f) for f in sorted(result.findings, key=lambda f: (f.severity != "error", f.page, f.visual))]
    lines.append(f"{result.matched} of {result.expected} visuals of the spec are in the report with the right type and fields.")
    if result.ok:
        lines.append("No errors.")
    else:
        lines.append(f"{len(result.errors)} error(s). Fix them in Power BI Desktop, save, and run the check again.")
    return "\n".join(lines)
