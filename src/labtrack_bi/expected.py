"""The numbers that Power BI must show, and the DAX queries that show them.

Each CHECK is one DAX query for the DAX query view of Power BI Desktop (model/check.dax) and the rows it must return
(docs/expected-numbers.md and .json). The rows are worked out by engine.py, never typed in. If the model, the data or a
measure changes, `labtrack-bi build` writes them again and the tests fail until it is run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from itertools import product
from pathlib import Path
from typing import Any

from . import data as datamod
from . import engine
from .spec import MEASURES

TIME_INTELLIGENCE = ("Sessions YTD", "Sessions Previous Year", "Sessions YoY")


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    measures: tuple[str, ...]
    groups: tuple[str, ...] = ()  # "Table.Column"
    where: tuple[tuple[str, tuple[Any, ...]], ...] = ()  # fixed filters, same notation
    note: str = ""


ALL_BUT_TIME = tuple(m.name for m in MEASURES if m.name not in TIME_INTELLIGENCE)

CHECKS: tuple[Check, ...] = (
    Check(
        "overall",
        "Every measure with no filter",
        ALL_BUT_TIME,
        note="The three measures of time intelligence are left out: they only make sense by year or month (checks by_year, by_month).",
    ),
    Check(
        "by_study",
        "By study",
        (
            "Sessions",
            "Sessions Completed",
            "Participants Attended",
            "Target N",
            "Recruitment Progress",
            "Completion Rate",
            "Avg Session Minutes",
            "Participants Withdrawn",
            "Hours Recorded",
            "Recordings",
            "Trials",
            "QC Pass Rate",
            "Trial Rejection Rate",
            "Uncalibrated Recordings",
        ),
        ("Study.Study Code",),
        note="Participants Attended adds up to 211 here but is 199 in the check overall: 12 people took part in two studies.",
    ),
    Check(
        "by_year",
        "By year (time intelligence)",
        ("Sessions", "Sessions Completed", "Sessions YTD", "Sessions Previous Year", "Sessions YoY"),
        ("Calendar.Year",),
        note="2027 is listed with blank sessions only because its previous year (2026) has sessions, so [Sessions YoY] is -1 "
        "there. Power BI leaves out a year when every measure is blank: that is why 2023 and 2028 are not here.",
    ),
    Check(
        "by_month",
        "By month (running totals)",
        ("Sessions Completed", "Completed Sessions Running Total", "Participants Attended Running Total", "Sessions YTD"),
        ("Calendar.Year-Month",),
        note="The running totals are blank after the last completed session, so the last two months (2026-11 and 2026-12) "
        "show a blank in those two columns. A month in which every measure is blank is not listed.",
    ),
    Check("by_status", "Sessions by status", ("Sessions",), ("Session.Status",)),
    Check(
        "by_visit",
        "Participants and retention by visit",
        ("Participants Attended", "Visit Retention"),
        ("Session.Visit No",),
        note="Visits 5 to 7 are extra visits; the visual of the report is filtered to visits 1 to 4.",
    ),
    Check("by_age_sex", "Participants by age band and sex", ("Participants Attended",), ("Participant.Age Band", "Participant.Sex")),
    Check(
        "by_modality",
        "Data quality by modality",
        ("Recordings", "Trials", "QC Pass Rate", "Uncalibrated Recordings", "Uncalibrated Rate", "Trial Rejection Rate"),
        ("Recording.Modality",),
    ),
    Check("by_qc", "Recordings by quality-control result", ("Recordings",), ("Recording.QC",)),
    Check("by_reason", "Rejected trials by reason", ("Rejected Trials",), ("Trial.Reject Reason",)),
    Check("by_device", "Devices", ("Recordings", "Uncalibrated Recordings", "Uncalibrated Rate"), ("Device.Serial No",)),
    Check(
        "feedback_by_group",
        "Force variability by group (study FFB-01)",
        ("Mean Force CV", "Mean Force CV Feedback On", "Mean Force CV Feedback Off", "Feedback Effect on Force CV"),
        ("Session.Group",),
        (("Study.Study Code", ("FFB-01",)),),
    ),
    Check(
        "findings",
        "The three effects",
        (
            "Mean MDF",
            "Mean RMS",
            "Mean Alpha Power",
            "MDF Change After Fatigue",
            "RMS Change After Fatigue",
            "Alpha Change Large vs Small Stimulus",
        ),
    ),
)


def check_by_id(check_id: str) -> Check:
    return next(c for c in CHECKS if c.id == check_id)


# ---------------------------------------------------------------------------------------------------------------
# the rows
# ---------------------------------------------------------------------------------------------------------------
def _group_values(index: engine.Index, column: str) -> list[Any]:
    table, name = column.split(".", 1)
    values = {row[name] for row in index.data[table]}
    return sorted(values, key=lambda v: (v is not None, v if v is not None else 0))


def rows_of(check: Check, base: engine.Ctx) -> list[list[Any]]:
    """The rows of one check: the values of the group columns, then the measures; rows with every measure blank are not
    listed, as SUMMARIZECOLUMNS does not list them."""
    ctx = base.calc_columns({column: values for column, values in check.where})
    if not check.groups:
        return [[engine.M[m](ctx) for m in check.measures]]
    out: list[list[Any]] = []
    for combo in product(*(_group_values(base.index, g) for g in check.groups)):
        scoped = ctx.calc_columns({g: [v] for g, v in zip(check.groups, combo, strict=True)})
        values = [engine.M[m](scoped) for m in check.measures]
        if any(v is not None for v in values):
            out.append([*combo, *values])
    return out


def columns_of(check: Check) -> list[str]:
    return [*check.groups, *check.measures]


def compute(folder: Path) -> dict[str, list[list[Any]]]:
    base = engine.whole(datamod.load(folder))
    return {c.id: rows_of(c, base) for c in CHECKS}


# ---------------------------------------------------------------------------------------------------------------
# DAX queries
# ---------------------------------------------------------------------------------------------------------------
QUOTED_TABLES = frozenset({"Calendar"})  # also the name of a DAX function: always written 'Calendar'[...]


def dax_column(column: str) -> str:
    table, name = column.split(".", 1)
    return f"'{table}'[{name}]" if table in QUOTED_TABLES else f"{table}[{name}]"


def dax_literal(value: Any) -> str:
    return '"' + value.replace('"', '""') + '"' if isinstance(value, str) else str(value)


def _arguments(items: list[str]) -> list[str]:
    return [f"    {item}{',' if i < len(items) - 1 else ''}" for i, item in enumerate(items)]


def dax_query(check: Check) -> str:
    pairs = [f'"{m}", [{m}]' for m in check.measures]
    groups = [dax_column(g) for g in check.groups]
    lines = ["SUMMARIZECOLUMNS(", *_arguments([*groups, *pairs]), ")"] if groups else ["ROW(", *_arguments(pairs), ")"]
    if check.where:
        filters = [f"{dax_column(c)} = {dax_literal(v[0])}" for c, v in check.where]
        inner = ["    " + line for line in lines]
        inner[-1] += ","
        lines = ["CALCULATETABLE(", *inner, *_arguments(filters), ")"]
    text = "EVALUATE\n" + "\n".join(lines)
    if groups:
        text += "\nORDER BY " + ", ".join(groups)
    return text


def check_file() -> str:
    """model/check.dax: one query per check. In the DAX query view select ONE query and press Run."""
    parts = [
        "// labtrack-bi: queries to check the model against docs/expected-numbers.md.",
        "// Power BI Desktop > DAX query view. Select ONE of the queries below (all of its lines, from EVALUATE to the end)",
        "// and press Run. Compare the result with the table of the same number in docs/expected-numbers.md.",
    ]
    for number, check in enumerate(CHECKS, start=1):
        parts.append("")
        parts.append(f"// ---- {number}. {check.title} ({check.id})")
        parts.append(dax_query(check))
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------------------------------------------
# documents
# ---------------------------------------------------------------------------------------------------------------
def fmt(value: Any) -> str:
    if value is None:
        return "(blank)"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def jsonable(value: Any) -> Any:
    if isinstance(value, float):
        return float(f"{value:.9g}")
    if isinstance(value, date):
        return value.isoformat()
    return value


def expected_json(folder: Path) -> str:
    results = compute(folder)
    sums = datamod.read_sums(folder)
    doc = {
        "data": sums,
        "checks": [
            {
                "id": c.id,
                "title": c.title,
                "groups": list(c.groups),
                "measures": list(c.measures),
                "where": [[col, list(v)] for col, v in c.where],
                "rows": [[jsonable(v) for v in row] for row in results[c.id]],
            }
            for c in CHECKS
        ],
    }
    return json.dumps(doc, indent=1, ensure_ascii=False) + "\n"


def expected_markdown(folder: Path) -> str:
    results = compute(folder)
    out = [
        "# Expected numbers",
        "",
        "What Power BI must show when the model is loaded with the files of `data/`. Every number here was worked out by "
        "`src/labtrack_bi/engine.py` (a second, hand-written version of the measures), never typed in, and the tests "
        "fail when this file is out of date.",
        "",
        "**How to check.** Open `model/check.dax` in the DAX query view of Power BI Desktop, select one query, press Run, "
        "and compare the result with the table of the same number below. Numbers are shown with six significant digits; "
        "Power BI shows more. Rows may come in another order.",
        "",
        "`(blank)` means that the measure is blank for that row: Power BI leaves the cell empty.",
        "",
    ]
    for number, check in enumerate(CHECKS, start=1):
        out += [f"## {number}. {check.title}", "", f"Query {number} of `model/check.dax` (`{check.id}`)."]
        if check.where:
            out.append("Only " + ", ".join(f"`{dax_column(c)}` = {', '.join(map(str, v))}" for c, v in check.where) + ".")
        if check.note:
            out += ["", check.note]
        out.append("")
        names = [dax_column(g) for g in check.groups] + [f"[{m}]" for m in check.measures]
        rows = results[check.id]
        if len(check.groups) == 0:
            out += ["| Measure | Value |", "|---|---:|"]
            out += [f"| [{m}] | {fmt(v)} |" for m, v in zip(check.measures, rows[0], strict=True)]
        else:
            out += [
                "| " + " | ".join(names) + " |",
                "|" + "|".join("---" for _ in names[: len(check.groups)]) + "|" + "|".join("---:" for _ in check.measures) + "|",
            ]
            out += ["| " + " | ".join(fmt(v) for v in row) + " |" for row in rows]
        out.append("")
    return "\n".join(out)
