"""The semantic model, read back from the TMDL files, says what the spec says."""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest

from labtrack_bi import mcode, tmdl
from labtrack_bi.spec import MEASURES, MEASURES_TABLE, RELATIONSHIPS, TABLES, Table

pytestmark = pytest.mark.seed

DEFINITION = "labtrack.SemanticModel/definition"
NAME = r"'(?:[^']|'')+'|[^.'\s]+"
COLUMN_REFERENCE = re.compile(rf"^(?P<table>{NAME})\.(?P<column>{NAME})$")


def unquote(name: str) -> str:
    return name[1:-1].replace("''", "'") if name.startswith("'") else name


def split(reference: str) -> tuple[str, str]:
    m = COLUMN_REFERENCE.match(reference)
    assert m, reference
    return unquote(m.group("table")), unquote(m.group("column"))


def read(root: Path, relative: str) -> tmdl.Node:
    return tmdl.parse_one((root / DEFINITION / relative).read_text(encoding="utf-8"))


def table_node(root: Path, table: Table) -> tmdl.Node:
    return read(root, f"tables/{table.name}.tmdl")


def test_every_tmdl_file_parses(root: Path) -> None:
    files = sorted((root / DEFINITION).rglob("*.tmdl"))
    assert len(files) == 14
    for path in files:
        assert tmdl.parse(path.read_text(encoding="utf-8")), path.name


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_the_columns_of_a_table_are_those_of_the_spec(root: Path, table: Table) -> None:
    node = table_node(root, table)
    assert node.name == table.name
    assert [c.name for c in node.all("column")] == [c.name for c in table.columns]
    for spec, column in zip(table.columns, node.all("column"), strict=True):
        assert column.props["dataType"] == tmdl.DATA_TYPES[spec.dtype], spec.name
        assert column.props["summarizeBy"] == "none", spec.name
        assert unquote(str(column.props["sourceColumn"])) == spec.name, spec.name
        assert bool(column.props.get("isHidden")) == spec.hidden, spec.name
        assert bool(column.props.get("isKey")) == spec.key, spec.name
        assert column.props.get("formatString") == spec.fmt, spec.name
        assert (unquote(str(column.props["sortByColumn"])) if "sortByColumn" in column.props else None) == spec.sort_by, spec.name
        assert column.doc == ([spec.desc] if spec.desc else []), spec.name


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_the_source_columns_are_the_columns_the_query_returns(root: Path, table: Table) -> None:
    query = mcode.query(table)
    listed = re.findall(r"Selected = Table\.SelectColumns\(Renamed, \{(.*)\}\)", query)
    assert len(listed) == 1
    returned = re.findall(r'"((?:[^"]|"")*)"', listed[0])
    assert returned == [c.name for c in table.columns]


def test_sort_by_columns_are_columns_of_the_same_table(root: Path) -> None:
    for table in TABLES:
        names = {c.name for c in table.columns}
        for column in table.columns:
            if column.sort_by:
                assert column.sort_by in names, (table.name, column.name)


def test_each_table_has_one_partition_with_its_query(root: Path) -> None:
    for table in TABLES:
        node = table_node(root, table)
        partitions = node.all("partition")
        assert len(partitions) == 1 and partitions[0].props["mode"] == "import"
        assert tmdl.unindent(str(partitions[0].props["source"])).strip() == mcode.query(table).strip()


def test_the_relationships_are_those_of_the_spec(root: Path) -> None:
    nodes = tmdl.parse((root / DEFINITION / "relationships.tmdl").read_text(encoding="utf-8"))
    found = {(split(str(n.props["fromColumn"])), split(str(n.props["toColumn"]))) for n in nodes}
    wanted = {(tuple(r.many.split(".", 1)), tuple(r.one.split(".", 1))) for r in RELATIONSHIPS}
    assert found == wanted
    assert len(nodes) == len(RELATIONSHIPS) == 7
    for n in nodes:
        assert set(n.props) == {"fromColumn", "toColumn"}, "the defaults are many-to-one, single direction, active"
    columns = {(t.name, c.name): c for t in TABLES for c in t.columns}
    for many, one in found:
        assert columns[many].dtype == columns[one].dtype, (many, one)


def test_the_calendar_is_the_date_table(root: Path) -> None:
    node = read(root, "tables/Calendar.tmdl")
    assert node.props["dataCategory"] == "Time"
    keys = [c for c in node.all("column") if c.props.get("isKey")]
    assert [c.name for c in keys] == ["Date"] and keys[0].props["dataType"] == "dateTime"
    assert [t.name for t in TABLES if t.date_table] == ["Calendar"]


def test_the_measures(root: Path) -> None:
    node = read(root, f"tables/{MEASURES_TABLE}.tmdl")
    measures = node.all("measure")
    assert [m.name for m in measures] == [m.name for m in MEASURES] and len(measures) == 46
    for spec, found in zip(MEASURES, measures, strict=True):
        assert tmdl.unindent(str(found.value)).strip() == spec.dax.strip(), spec.name
        assert found.props["formatString"] == spec.fmt, spec.name
        assert found.props["displayFolder"] == spec.folder, spec.name
        assert found.doc == [spec.desc], spec.name
    hidden = [c for c in node.all("column")]
    assert len(hidden) == 1 and hidden[0].props.get("isHidden")


def test_a_measure_never_has_the_name_of_a_visible_column(root: Path) -> None:
    """The field list must not show two things with one name. A hidden column may share its name with the measure
    that adds it up (Target N): only the measure is shown."""
    visible = {c.name for t in TABLES for c in t.columns if not c.hidden}
    assert not {m.name for m in MEASURES} & visible
    assert len({m.name for m in MEASURES}) == len(MEASURES)


def test_the_model_refers_to_every_table_and_orders_the_queries(root: Path) -> None:
    nodes = tmdl.parse((root / DEFINITION / "model.tmdl").read_text(encoding="utf-8"))
    refs = {n.name for n in nodes if n.kind == "ref"}
    assert refs == {f"table {t.name}" for t in TABLES} | {f"table {MEASURES_TABLE}", "cultureInfo en-US"}
    order = next(n for n in nodes if n.kind == "annotation" and n.name == "PBI_QueryOrder")
    assert order.value == '["DataFolder",' + ",".join(f'"{t.name}"' for t in TABLES) + "]"


def test_the_data_folder_parameter(root: Path) -> None:
    text = (root / DEFINITION / "expressions.tmdl").read_text(encoding="utf-8")
    assert text.startswith('expression DataFolder = "C:\\labtrack-bi\\data" meta [IsParameterQuery = true')


def test_lineage_tags_are_valid_and_never_repeat(root: Path) -> None:
    tags: list[str] = []
    for path in (root / DEFINITION).rglob("*.tmdl"):
        tags += re.findall(r"lineageTag: (\S+)", path.read_text(encoding="utf-8"))
    assert len(tags) > 100
    assert len(tags) == len(set(tags))
    for tag in tags:
        assert str(uuid.UUID(tag)) == tag


def test_the_parser_refuses_what_it_does_not_understand() -> None:
    with pytest.raises(tmdl.TmdlError):
        tmdl.parse("table T\n    column C\n")  # spaces, not tabs
    with pytest.raises(tmdl.TmdlError):
        tmdl.parse("table 'T\n")  # a name that is not closed
