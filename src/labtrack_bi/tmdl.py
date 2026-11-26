"""TMDL, the text format in which Power BI Desktop saves a semantic model inside a Power BI Project.

Two halves. The writers turn the spec into the files of `SemanticModel/definition/`; their shape was copied from files
that Power BI Desktop itself saved (see docs/verification.md). The reader is a small parser used by the tests: it is not
the parser of Microsoft, it reads exactly the subset that the writers produce, and it is strict about it.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field

from . import mcode
from .spec import MEASURES, MEASURES_TABLE, PROJECT, RELATIONSHIPS, TABLES, Column, Measure, Relationship, Table

NAMESPACE = uuid.UUID("5f8a1c4e-2b7d-4e0a-9c33-6d1f0a7b9e21")
TAB = "\t"

# ---------------------------------------------------------------------------------------------------------------
# writers
# ---------------------------------------------------------------------------------------------------------------
_BARE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote(name: str) -> str:
    """A name as TMDL writes it: bare when it is made of letters, digits and underscores, otherwise in single quotes."""
    return name if _BARE.match(name) else "'" + name.replace("'", "''") + "'"


def lineage(path: str) -> str:
    """A GUID that depends only on the path of the object, so that building twice gives the same files."""
    return str(uuid.uuid5(NAMESPACE, "labtrack-bi/" + path))


def _doc(text: str, indent: int) -> list[str]:
    return [TAB * indent + "/// " + line for line in text.split("\n")] if text else []


DATA_TYPES = {"string": "string", "int64": "int64", "double": "double", "date": "dateTime", "datetime": "dateTime", "boolean": "boolean"}


def column_lines(table: Table, c: Column) -> list[str]:
    out = _doc(c.desc, 1)
    out.append(f"{TAB}column {quote(c.name)}")
    out.append(f"{TAB * 2}dataType: {DATA_TYPES[c.dtype]}")
    if c.hidden:
        out.append(f"{TAB * 2}isHidden")
    if c.fmt:
        out.append(f"{TAB * 2}formatString: {c.fmt}")
    out.append(f"{TAB * 2}lineageTag: {lineage(f'table/{table.name}/column/{c.name}')}")
    out.append(f"{TAB * 2}summarizeBy: none")
    if c.key:
        out.append(f"{TAB * 2}isKey")
    out.append(f"{TAB * 2}sourceColumn: {c.name}")
    if c.sort_by:
        out.append(f"{TAB * 2}sortByColumn: {quote(c.sort_by)}")
    out.append("")
    out.append(f"{TAB * 2}annotation SummarizationSetBy = Automatic")
    if c.dtype == "date":
        out.append("")
        out.append(f"{TAB * 2}annotation UnderlyingDateTimeDataType = Date")
    return out


def table_tmdl(table: Table) -> str:
    out = _doc(table.desc, 0)
    out.append(f"table {quote(table.name)}")
    out.append(f"{TAB}lineageTag: {lineage(f'table/{table.name}')}")
    if table.date_table:
        out.append(f"{TAB}dataCategory: Time")
    for c in table.columns:
        out.append("")
        out += column_lines(table, c)
    out.append("")
    out.append(f"{TAB}partition {quote(table.name)} = m")
    out.append(f"{TAB * 2}mode: import")
    out.append(f"{TAB * 2}source =")
    out += [TAB * 4 + line for line in mcode.query(table).split("\n")]
    out.append("")
    out.append(f"{TAB}annotation PBI_NavigationStepName = Navigation")
    out.append("")
    out.append(f"{TAB}annotation PBI_ResultType = Table")
    return "\n".join(out) + "\n"


def measure_lines(m: Measure) -> list[str]:
    out = _doc(m.desc, 1)
    head = f"{TAB}measure {quote(m.name)} ="
    if "\n" in m.dax:
        out.append(head + " ```")
        out += [TAB * 3 + line if line else "" for line in m.dax.split("\n")]
        out.append(TAB * 3 + "```")
    else:
        out.append(f"{head} {m.dax}")
    out.append(f"{TAB * 2}formatString: {m.fmt}")
    out.append(f"{TAB * 2}displayFolder: {m.folder}")
    out.append(f"{TAB * 2}lineageTag: {lineage(f'table/{MEASURES_TABLE}/measure/{m.name}')}")
    return out


def measures_tmdl() -> str:
    out = _doc("The measures of the model. Every number in the report comes from here; the model has no implicit measures.", 0)
    out.append(f"table {quote(MEASURES_TABLE)}")
    out.append(f"{TAB}lineageTag: {lineage(f'table/{MEASURES_TABLE}')}")
    for m in MEASURES:
        out.append("")
        out += measure_lines(m)
    out += [
        "",
        f"{TAB}column Value",
        f"{TAB * 2}isHidden",
        f"{TAB * 2}formatString: 0",
        f"{TAB * 2}lineageTag: {lineage(f'table/{MEASURES_TABLE}/column/Value')}",
        f"{TAB * 2}summarizeBy: sum",
        f"{TAB * 2}isNameInferred",
        f"{TAB * 2}sourceColumn: [Value]",
        "",
        f"{TAB * 2}annotation SummarizationSetBy = Automatic",
        "",
        f"{TAB}partition {quote(MEASURES_TABLE)} = calculated",
        f"{TAB * 2}mode: import",
        f"{TAB * 2}source = ```",
        f"{TAB * 4}{{0}}",
        f"{TAB * 4}```",
        "",
        f"{TAB}annotation PBI_Id = {uuid.uuid5(NAMESPACE, 'labtrack-bi/pbi-id/' + MEASURES_TABLE).hex}",
    ]
    return "\n".join(out) + "\n"


def relationship_name(r: Relationship) -> str:
    return lineage(f"relationship/{r.many}/{r.one}")


def _column_ref(ref: str) -> str:
    table, column = ref.split(".", 1)
    return f"{quote(table)}.{quote(column)}"


def relationships_tmdl() -> str:
    blocks = []
    for r in RELATIONSHIPS:
        blocks.append(f"relationship {relationship_name(r)}\n{TAB}fromColumn: {_column_ref(r.many)}\n{TAB}toColumn: {_column_ref(r.one)}\n")
    return "\n".join(blocks)


def database_tmdl() -> str:
    return f"database\n{TAB}compatibilityLevel: 1567\n"


def query_order() -> list[str]:
    return ["DataFolder", *[t.name for t in TABLES]]


def model_tmdl() -> str:
    refs = [f"ref table {quote(name)}" for name in sorted([t.name for t in TABLES] + [MEASURES_TABLE])]
    lines = [
        "model Model",
        f"{TAB}culture: en-US",
        f"{TAB}defaultPowerBIDataSourceVersion: powerBI_V3",
        f"{TAB}discourageImplicitMeasures",
        f"{TAB}sourceQueryCulture: en-US",
        f"{TAB}dataAccessOptions",
        f"{TAB * 2}legacyRedirects",
        f"{TAB * 2}returnErrorValuesAsNull",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        f"annotation PBI_QueryOrder = {json.dumps(query_order(), separators=(',', ':'))}",
        "",
        *refs,
        "",
        "ref cultureInfo en-US",
    ]
    return "\n".join(lines) + "\n"


def expressions_tmdl() -> str:
    return (
        f"expression DataFolder = {mcode.parameter()}\n"
        f"{TAB}lineageTag: {lineage('expression/DataFolder')}\n"
        "\n"
        f"{TAB}annotation PBI_ResultType = Text\n"
    )


def culture_tmdl() -> str:
    return "cultureInfo en-US\n"


def semantic_model_files() -> dict[str, str]:
    """Path (relative to the .SemanticModel folder) -> text, for everything under definition/."""
    files = {
        "definition/database.tmdl": database_tmdl(),
        "definition/model.tmdl": model_tmdl(),
        "definition/expressions.tmdl": expressions_tmdl(),
        "definition/relationships.tmdl": relationships_tmdl(),
        "definition/cultures/en-US.tmdl": culture_tmdl(),
        f"definition/tables/{MEASURES_TABLE}.tmdl": measures_tmdl(),
    }
    for t in TABLES:
        files[f"definition/tables/{t.name}.tmdl"] = table_tmdl(t)
    return files


# ---------------------------------------------------------------------------------------------------------------
# reader (for the tests)
# ---------------------------------------------------------------------------------------------------------------
OBJECT_KINDS = {
    "table",
    "column",
    "measure",
    "partition",
    "annotation",
    "relationship",
    "expression",
    "model",
    "database",
    "cultureInfo",
    "ref",
    "dataAccessOptions",
}
FLAGS = {"isHidden", "isKey", "isNameInferred", "discourageImplicitMeasures", "legacyRedirects", "returnErrorValuesAsNull"}


@dataclass
class Node:
    kind: str
    name: str = ""
    value: str | None = None  # what follows "=", already joined
    doc: list[str] = field(default_factory=list)  # the /// lines above
    props: dict[str, str | bool] = field(default_factory=dict)
    children: list[Node] = field(default_factory=list)
    line: int = 0

    def child(self, kind: str, name: str | None = None) -> Node | None:
        return next((c for c in self.children if c.kind == kind and (name is None or c.name == name)), None)

    def all(self, kind: str) -> list[Node]:
        return [c for c in self.children if c.kind == kind]


class TmdlError(ValueError):
    pass


def _read_name(text: str, line_no: int) -> tuple[str, str]:
    """Reads a name (bare or in single quotes) at the start of text; returns it and what is left after it."""
    if text.startswith("'"):
        i, out = 1, []
        while i < len(text):
            if text[i] == "'":
                if text[i + 1 : i + 2] == "'":
                    out.append("'")
                    i += 2
                    continue
                return "".join(out), text[i + 1 :]
            out.append(text[i])
            i += 1
        raise TmdlError(f"line {line_no}: a quoted name is not closed: {text!r}")
    m = re.match(r"[^\s=:']+", text)
    if not m:
        raise TmdlError(f"line {line_no}: a name was expected: {text!r}")
    return m.group(0), text[m.end() :]


def parse(text: str, lenient: bool = False) -> list[Node]:
    """Reads TMDL into a list of top-level nodes: objects, properties, flags, annotations, fenced and indented
    expressions, with tabs as the only indentation. Raises TmdlError on anything it does not understand.

    With `lenient=True` what it does not know (roles, perspectives, `changedProperty`, a new kind of object, a flag it
    never saw) is read as a node of kind "other" or as a property, so that a file saved by Power BI Desktop, which
    writes more than this package does, can still be read. Spaces for indentation still raise."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    pos = 0

    def level_of(raw: str, no: int) -> int:
        n = len(raw) - len(raw.lstrip(TAB))
        if raw[n : n + 1] == " ":
            raise TmdlError(f"line {no}: indentation must be tabs: {raw!r}")
        return n

    def skip_blank() -> None:
        nonlocal pos
        while pos < len(lines) and lines[pos].strip() == "":
            pos += 1

    def fenced(first: str, no: int) -> str:
        nonlocal pos
        content = [first] if first.strip() else []
        while pos < len(lines):
            raw = lines[pos]
            pos += 1
            if raw.strip() == "```":
                return "\n".join(content)
            content.append(raw)
        raise TmdlError(f"line {no}: a ``` block is not closed")

    def indented(parent_level: int) -> str:
        nonlocal pos
        content = []
        while pos < len(lines) and (lines[pos].strip() == "" or len(lines[pos]) - len(lines[pos].lstrip(TAB)) > parent_level):
            content.append(lines[pos])
            pos += 1
        while content and content[-1].strip() == "":
            content.pop()
        return "\n".join(content)

    def _has_children(level: int) -> bool:
        """True when the next line that is not blank is deeper than `level`."""
        i = pos
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        return i < len(lines) and len(lines[i]) - len(lines[i].lstrip(TAB)) > level

    def children(parent: Node, level: int) -> None:
        nonlocal pos
        pending: list[str] = []
        while True:
            skip_blank()
            if pos >= len(lines):
                return
            raw = lines[pos]
            no = pos + 1
            lv = level_of(raw, no)
            if lv < level:
                return
            if lv > level:
                raise TmdlError(f"line {no}: unexpected indentation: {raw!r}")
            body = raw[lv:]
            pos += 1
            if body.startswith("///"):
                pending.append(body[3:].strip())
                continue
            first = re.match(r"[A-Za-z]+", body)
            word = first.group(0) if first else ""
            after_word = body[len(word) :]
            if word in OBJECT_KINDS and (after_word == "" or after_word.startswith(" ")):
                node = Node(word, line=no, doc=pending)
                pending = []
                rest = after_word.strip()
                if word == "ref":
                    kind2, _, name = rest.partition(" ")
                    node.name = f"{kind2} {_read_name(name, no)[0]}"
                elif word in ("database", "model", "dataAccessOptions"):
                    node.name = rest
                elif rest:
                    name, tail = _read_name(rest, no)
                    node.name = name
                    tail = tail.strip()
                    if word == "partition":
                        if not tail.startswith("= "):
                            raise TmdlError(f"line {no}: a partition needs '= m' or '= calculated'")
                        node.props["_type"] = tail[2:].strip()
                    elif tail.startswith("="):
                        value = tail[1:].strip()
                        if value.startswith("```"):
                            node.value = fenced(value[3:], no)
                        elif value:
                            node.value = value
                        else:  # the expression on the next lines, one level deeper than the properties
                            node.value = indented(lv + 1)
                    elif tail:
                        raise TmdlError(f"line {no}: not understood after the name: {tail!r}")
                children(node, lv + 1)
                parent.children.append(node)
                continue
            if lenient and body.startswith("//"):
                continue
            if body in FLAGS or (lenient and re.fullmatch(r"[A-Za-z]+", body) and not _has_children(lv)):
                parent.props[body] = True
                continue
            prop = re.match(r"^([A-Za-z]+)\s*(:|=)\s*(.*)$", body)
            if prop and prop.group(2) == ":":
                parent.props[prop.group(1)] = prop.group(3)
                if lenient and _has_children(lv):  # a property with lines under it: they are read and left out
                    children(Node("other", name=body), lv + 1)
                continue
            if prop and prop.group(2) == "=" and (prop.group(1) == "source" or lenient):
                value = prop.group(3)
                if value.startswith("```"):
                    value = fenced(value[3:], no)
                elif not value:
                    value = indented(lv)
                if prop.group(1) == "changedProperty":
                    parent.props.setdefault("changedProperty", "")
                    parent.props["changedProperty"] = f"{parent.props['changedProperty']} {value}".strip()
                else:
                    parent.props[prop.group(1)] = value
                continue
            if lenient:  # an object of a kind this package does not know
                node = Node("other", name=body, line=no, doc=pending)
                pending = []
                children(node, lv + 1)
                parent.children.append(node)
                continue
            raise TmdlError(f"line {no}: not understood: {raw!r}")

    root = Node("root")
    children(root, 0)
    return root.children


def parse_one(text: str, lenient: bool = False) -> Node:
    nodes = parse(text, lenient)
    if len(nodes) < 1:
        raise TmdlError("the file is empty")
    return nodes[0]


def unindent(text: str) -> str:
    """Removes the tabs that the file adds in front of an M or DAX block."""
    lines = text.split("\n")
    margin = min((len(x) - len(x.lstrip(TAB)) for x in lines if x.strip()), default=0)
    return "\n".join(x[margin:] for x in lines)


__all__ = ["PROJECT", "Node", "TmdlError", "parse", "parse_one", "semantic_model_files", "quote", "lineage", "unindent"]
