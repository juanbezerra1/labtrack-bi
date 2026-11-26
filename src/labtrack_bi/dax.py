"""DAX: the file with all the measures, and a linter for the measures and for the queries of the checks.

The linter does not run DAX. It reads it: strings and brackets are closed, every function is one that this project has
looked up, every table and column exists in the model, every [Measure] exists and no measure uses itself, variables are
declared before they are used, and a text that a measure compares with a column is a value that the column holds.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from .spec import MEASURES, MEASURES_TABLE, TABLES, Measure, table_by_name

# Every function the project uses. Add one here only after reading its page in the DAX reference.
FUNCTIONS = frozenset(
    {
        "ALL",
        "AVERAGE",
        "CALCULATE",
        "CALCULATETABLE",
        "COUNTROWS",
        "DISTINCTCOUNT",
        "DIVIDE",
        "FALSE",
        "FILTER",
        "HASONEVALUE",
        "IF",
        "MAX",
        "MIN",
        "REMOVEFILTERS",
        "ROW",
        "SAMEPERIODLASTYEAR",
        "SUM",
        "SUMMARIZECOLUMNS",
        "TOTALYTD",
        "TRUE",
    }
)
KEYWORDS = frozenset({"VAR", "RETURN", "EVALUATE", "ORDER", "BY", "DEFINE", "MEASURE", "ASC", "DESC"})

TOKEN = re.compile(
    r"""
    (?P<comment>//[^\n]*|--[^\n]*|/\*.*?\*/)
  | (?P<string>"(?:[^"]|"")*")
  | (?P<table>'(?:[^']|'')+')
  | (?P<bracket>\[[^\]]+\])
  | (?P<number>\d+(?:\.\d+)?)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op><=|>=|<>|&&|\|\||[-+*/=<>&^,(){}])
  | (?P<space>\s+)
""",
    re.VERBOSE | re.DOTALL,
)


@dataclass(frozen=True)
class Token:
    kind: str
    text: str


def tokenize(text: str) -> list[Token]:
    out: list[Token] = []
    pos = 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise ValueError(f"DAX: cannot read {text[pos : pos + 25]!r}")
        pos = m.end()
        kind = m.lastgroup or ""
        if kind not in ("space", "comment"):
            out.append(Token(kind, m.group(0)))
    return out


def column_names(table: str) -> set[str]:
    return {c.name for c in table_by_name(table).columns}


def model_columns() -> dict[str, set[str]]:
    return {t.name: column_names(t.name) for t in TABLES}


def measure_names() -> set[str]:
    return {m.name for m in MEASURES}


def references(text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """(Table, Column) pairs and [Measure] names found in a piece of DAX."""
    tokens = tokenize(text)
    columns: list[tuple[str, str]] = []
    measures: list[str] = []
    for i, tok in enumerate(tokens):
        if tok.kind != "bracket":
            continue
        name = tok.text[1:-1]
        prev = tokens[i - 1] if i > 0 else None
        if prev is not None and prev.kind == "table":
            columns.append((prev.text[1:-1].replace("''", "'"), name))
        elif prev is not None and prev.kind == "name" and prev.text not in KEYWORDS and prev.text not in FUNCTIONS:
            columns.append((prev.text, name))
        else:
            measures.append(name)
    return columns, measures


def lint(text: str, where: str, known_measures: set[str] | None = None) -> list[str]:
    """Problems found in one measure or query; an empty list means none."""
    problems: list[str] = []
    try:
        tokens = tokenize(text)
    except ValueError as error:
        return [f"{where}: {error}"]
    depth = 0
    declared: set[str] = set()
    known = known_measures if known_measures is not None else measure_names()
    for i, tok in enumerate(tokens):
        if tok.text in "({" and tok.kind == "op":
            depth += 1
        elif tok.text in ")}" and tok.kind == "op":
            depth -= 1
            if depth < 0:
                problems.append(f"{where}: a closing bracket without an opening one")
                depth = 0
        elif tok.kind == "name":
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            prev = tokens[i - 1] if i > 0 else None
            if prev is not None and prev.text == "VAR":
                declared.add(tok.text)
            elif nxt is not None and nxt.text == "(":
                if tok.text.upper() not in FUNCTIONS:
                    problems.append(f"{where}: the function {tok.text} is not in dax.FUNCTIONS")
            elif nxt is not None and nxt.kind == "bracket":
                pass  # Table[Column], checked below
            elif tok.text in KEYWORDS or tok.text.upper() in FUNCTIONS or tok.text in {t.name for t in TABLES}:
                pass  # a keyword, TRUE/FALSE, or a table name
            elif tok.text not in declared:
                problems.append(f"{where}: {tok.text} is used and never declared")
    if depth != 0:
        problems.append(f"{where}: brackets are not balanced")
    cols = model_columns()
    pairs, used = references(text)
    for table, column in pairs:
        if table == MEASURES_TABLE:
            if column not in known:
                problems.append(f"{where}: {table}[{column}] is not a measure")
        elif table not in cols:
            problems.append(f"{where}: the table {table} is not in the model")
        elif column not in cols[table]:
            problems.append(f"{where}: the column {table}[{column}] is not in the model")
    for name in used:
        if name not in known:
            problems.append(f"{where}: the measure [{name}] is not in the model")
    return problems


LITERAL = re.compile(r"([A-Za-z_]\w*|'[^']+')\[([^\]]+)\]\s*=\s*\"((?:[^\"]|\"\")*)\"")


def literal_checks(text: str) -> list[tuple[str, str, str]]:
    """(table, column, text) for every `Table[Column] = "text"` in the DAX."""
    return [(m.group(1).strip("'"), m.group(2), m.group(3).replace('""', '"')) for m in LITERAL.finditer(text)]


def dependencies(measure: Measure) -> set[str]:
    return set(references(measure.dax)[1])


def find_cycle(measures: Iterable[Measure]) -> list[str] | None:
    graph = {m.name: dependencies(m) for m in measures}
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(name: str) -> list[str] | None:
        if state.get(name) == 2:
            return None
        if state.get(name) == 1:
            return [*stack[stack.index(name) :], name]
        state[name] = 1
        stack.append(name)
        for dep in sorted(graph.get(name, ())):
            found = visit(dep)
            if found:
                return found
        stack.pop()
        state[name] = 2
        return None

    for name in graph:
        found = visit(name)
        if found:
            return found
    return None


def measures_file() -> str:
    """model/measures.dax: every measure as `Name = expression`, for the manual path (Home > New measure)."""
    out = [
        "// labtrack-bi: the measures of the model, for the manual path.",
        "// Create a table called Measures (Home > Enter data, one empty column, then delete the column) and, for each block",
        "// below, Home > New measure and paste the line (or lines) after the comment. Set the format and the display",
        "// folder that the comment names (Measure tools > Format; Model view > Properties > Display folder).",
        "// If you opened labtrack.pbip you do not need this file: the project already has the measures.",
    ]
    for m in MEASURES:
        out += ["", f"// {m.folder} | format: {m.fmt}", f"// {m.desc}"]
        out.append(f"{m.name} = {m.dax}" if "\n" not in m.dax else f"{m.name} =\n{m.dax}")
    return "\n".join(out) + "\n"
