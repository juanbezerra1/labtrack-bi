"""The documents that are made from the spec: the model reference and the report specification."""

from __future__ import annotations

from .spec import KIND_LABELS, MEASURES, MEASURES_TABLE, PAGES, RELATIONSHIPS, TABLES
from .wireframe import page_file_name

DTYPE_NAMES = {
    "string": "Text",
    "int64": "Whole number",
    "double": "Decimal number",
    "date": "Date",
    "datetime": "Date and time",
    "boolean": "True/False",
}


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def model_markdown() -> str:
    out = [
        "# The model",
        "",
        "Made by `labtrack-bi build` from `src/labtrack_bi/spec.py`; do not edit by hand. The model is a star schema: four "
        "dimensions filter `Session`, `Session` and `Device` filter `Recording`, and `Recording` filters `Trial`. "
        "Filters flow one way only, from the dimension to the fact.",
        "",
        "![The model](img/model.svg)",
        "",
        "## Relationships",
        "",
        "| From (many) | To (one) |",
        "|---|---|",
        *[f"| `{r.many}` | `{r.one}` |" for r in RELATIONSHIPS],
        "",
        "All seven are many-to-one, single direction, active. Only the date of the session is related to `Calendar`: the "
        "recordings and the trials reach the calendar through their session, so there is one path and no ambiguity.",
        "",
        "## Tables and columns",
    ]
    for table in TABLES:
        out += [
            "",
            f"### {table.name}",
            "",
            f"{table.desc}",
            "",
            f"Source: `data/{table.csv}.csv`.",
            "",
            "| Column | Type | Comes from | Notes |",
            "|---|---|---|---|",
        ]
        for c in table.columns:
            origin = f"`{c.source}`" if c.source else "made in Power Query"
            if c.transform == "label":
                origin += " (code turned into a label)"
            elif c.transform:
                origin += " (mapped to a label)"
            notes = (
                c.desc
                + (" Hidden." if c.hidden else "")
                + (f" Sorted by {c.sort_by}." if c.sort_by else "")
                + (" Key of the date table." if c.key else "")
            )
            out.append(f"| {c.name} | {DTYPE_NAMES[c.dtype]} | {origin} | {_cell(notes.strip())} |")
        if table.drop:
            out += ["", "Not imported: " + ", ".join(f"`{h}`" for h in table.drop) + "."]
    out += [
        "",
        f"## Measures (table `{MEASURES_TABLE}`)",
        "",
        f"{len(MEASURES)} explicit measures. The model discourages implicit measures, so every number in the report is one of these.",
        "",
        "| Folder | Measure | Format | What it is |",
        "|---|---|---|---|",
    ]
    out += [f"| {m.folder} | {m.name} | `{m.fmt}` | {_cell(m.desc)} |" for m in MEASURES]
    out += ["", "### The DAX of every measure"]
    for m in MEASURES:
        out += ["", f"**{m.name}**", "", "```dax", m.dax, "```"]
    return "\n".join(out) + "\n"


def report_markdown() -> str:
    out = [
        "# The report: what to build",
        "",
        "Made by `labtrack-bi build` from `src/labtrack_bi/spec.py`; do not edit by hand. `labtrack.pbip` already has the four "
        "pages (empty, 1280 x 720, with the LabTrack theme). You build the visuals, following the list of each page. "
        "The step by step is in [build-guide.md](build-guide.md).",
        "",
        "How to read a list: **Position** is x, y, width, height in pixels on the 1280 x 720 page "
        "(Format > General > Properties > Size and Position). **Fields** are what to drag into each well; `Table[Column]` is "
        "a column, `[Name]` is a measure of the table Measures. The number of the first column is the number in the drawing.",
        "",
        "Rules that apply to every visual: no more than four series in a chart, and a legend whenever there are two or more; "
        "data labels on bars and columns with one series; no dual axes, no pie or donut; the name of the visual "
        "(Format > General > Title) is the one in the list; alt text (Format > General > Alt text) says in one sentence "
        "what the visual shows.",
    ]
    for number, page in enumerate(PAGES, start=1):
        out += [
            "",
            f"## Page {number}: {page.name}",
            "",
            page.purpose,
            "",
            f"![Wireframe of the page {page.name}](img/wireframe-{page_file_name(number, page)})",
            "",
            "| # | Visual | Title | Position | Fields | Notes |",
            "|---|---|---|---|---|---|",
        ]
        for i, v in enumerate(page.visuals, start=1):
            fields = "<br>".join(f"{well}: {', '.join(f'`{f}`' for f in fs)}" for well, fs in v.fields) or "-"
            out.append(f"| {i} | {KIND_LABELS[v.kind]} | {_cell(v.title)} | {v.x}, {v.y}, {v.w}, {v.h} | {fields} | {_cell(v.notes)} |")
    return "\n".join(out) + "\n"
