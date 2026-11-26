"""Compares the semantic model that is saved in the project with the spec.

Power BI Desktop rewrites the TMDL files every time it saves, so after the first save they are no longer the bytes
that `labtrack-bi build` wrote. What has to stay the same is what they say: the tables and their columns, the
measures and their DAX, the relationships, the Power Query code. This module reads the files back with the TMDL reader
of this package and compares exactly that. Layout, order, quotes, line breaks and the value of the DataFolder
parameter (which is yours) are not compared.
"""

from __future__ import annotations

import re
from pathlib import Path

from . import mcode, tmdl
from .spec import MEASURES, MEASURES_TABLE, RELATIONSHIPS, TABLES

NAME = r"'(?:[^']|'')+'|[^.'\s]+"
REFERENCE = re.compile(rf"^(?P<table>{NAME})\.(?P<column>{NAME})$")


def _unquote(name: str) -> str:
    return name[1:-1].replace("''", "'") if name.startswith("'") else name


def _split(reference: str) -> tuple[str, str]:
    m = REFERENCE.match(reference.strip())
    if not m:
        raise tmdl.TmdlError(f"a column reference was expected, found {reference!r}")
    return _unquote(m.group("table")), _unquote(m.group("column"))


def _squash(text: str) -> str:
    return " ".join(text.split())


def _read(path: Path) -> list[tmdl.Node]:
    return tmdl.parse(path.read_text(encoding="utf-8-sig"), lenient=True)


def check_model(model_folder: Path) -> list[str]:
    """What differs between the saved model and the spec, one sentence each. An empty list: they say the same."""
    definition = model_folder / "definition"
    if not definition.is_dir():
        return [f"{definition} not found: the model is not saved in the TMDL format"]
    problems: list[str] = []
    found_tables: dict[str, tmdl.Node] = {}
    for path in sorted((definition / "tables").glob("*.tmdl")):
        try:
            nodes = _read(path)
        except tmdl.TmdlError as error:
            problems.append(f"{path.name}: it cannot be read: {error}")
            continue
        for node in nodes:
            if node.kind == "table":
                found_tables[node.name] = node
    wanted = {t.name for t in TABLES} | {MEASURES_TABLE}
    problems += [f"table {name} is missing" for name in sorted(wanted - found_tables.keys())]
    problems += [f"table {name} is not in the spec" for name in sorted(found_tables.keys() - wanted)]

    for table in TABLES:
        table_node = found_tables.get(table.name)
        if table_node is None:
            continue
        columns = {c.name: c for c in table_node.all("column")}
        for spec in table.columns:
            column = columns.get(spec.name)
            if column is None:
                problems.append(f"{table.name}[{spec.name}] is missing")
            elif column.props.get("dataType") != tmdl.DATA_TYPES[spec.dtype]:
                problems.append(
                    f"{table.name}[{spec.name}] has the type {column.props.get('dataType')}, the spec says {tmdl.DATA_TYPES[spec.dtype]}"
                )
        problems += [f"{table.name}[{name}] is not in the spec" for name in sorted(columns.keys() - {c.name for c in table.columns})]
        partitions = table_node.all("partition")
        if len(partitions) != 1:
            problems.append(f"{table.name} has {len(partitions)} partitions, it must have one")
        else:
            source = str(partitions[0].props.get("source", ""))
            if _squash(source) != _squash(mcode.query(table)):
                problems.append(f"the Power Query code of {table.name} is not the one of model/powerquery/{table.name}.pq")
        if table.date_table and table_node.props.get("dataCategory") != "Time":
            problems.append(f"{table.name} is not marked as the date table (dataCategory: Time)")

    measures_node = found_tables.get(MEASURES_TABLE)
    if measures_node is not None:
        found = {m.name: m for m in measures_node.all("measure")}
        for spec_measure in MEASURES:
            measure = found.get(spec_measure.name)
            if measure is None:
                problems.append(f"the measure [{spec_measure.name}] is missing")
                continue
            if _squash(str(measure.value or "")) != _squash(spec_measure.dax):
                problems.append(f"the DAX of [{spec_measure.name}] is not the one of the spec")
            if measure.props.get("formatString") != spec_measure.fmt:
                problems.append(
                    f"[{spec_measure.name}] has the format {measure.props.get('formatString')}, the spec says {spec_measure.fmt}"
                )
            if measure.props.get("displayFolder") != spec_measure.folder:
                problems.append(
                    f"[{spec_measure.name}] is in the folder {measure.props.get('displayFolder')}, the spec says {spec_measure.folder}"
                )
        problems += [f"the measure [{name}] is not in the spec" for name in sorted(found.keys() - {m.name for m in MEASURES})]

    relationships = definition / "relationships.tmdl"
    if not relationships.exists():
        problems.append("relationships.tmdl is missing")
    else:
        try:
            seen: set[tuple[tuple[str, str], tuple[str, str]]] = set()
            for node in _read(relationships):
                pair = (_split(str(node.props["fromColumn"])), _split(str(node.props["toColumn"])))
                seen.add(pair)
                extra = sorted(set(node.props) - {"fromColumn", "toColumn"})
                if extra:
                    problems.append(
                        f"the relationship {pair[0][0]}[{pair[0][1]}] to {pair[1][0]}[{pair[1][1]}] has settings "
                        f"({', '.join(extra)}): the model needs the defaults, many to one, one direction, active"
                    )
            wanted_pairs = {(tuple(r.many.split(".", 1)), tuple(r.one.split(".", 1))) for r in RELATIONSHIPS}
            problems += [f"the relationship {a[0]}[{a[1]}] to {b[0]}[{b[1]}] is missing" for a, b in sorted(wanted_pairs - seen)]
            problems += [f"the relationship {a[0]}[{a[1]}] to {b[0]}[{b[1]}] is not in the spec" for a, b in sorted(seen - wanted_pairs)]
        except (tmdl.TmdlError, KeyError) as error:
            problems.append(f"relationships.tmdl: it cannot be read: {error}")

    expressions = definition / "expressions.tmdl"
    if not expressions.exists() or "expression DataFolder" not in expressions.read_text(encoding="utf-8-sig"):
        problems.append("the parameter DataFolder is missing")
    return problems
