"""Power Query (M) code of the model, made from the spec.

One query per table. Every query follows the same steps, so a person who opens the Power Query editor finds the same
shape in all of them:

    Source     read the CSV file (the folder comes from the DataFolder parameter)
    Headers    use the first row as the names of the columns
    Dropped    remove the columns that the model does not use (only when there are some)
    Cleaned    empty text becomes null, so that numbers and dates can be typed
    Typed      give each column its type, reading numbers and dates with the en-US culture
    Labelled   turn codes into labels (no_show -> No Show; emg -> EMG)
    Add...     one step per column that is made here (the age band, the feedback of a trial, ...)
    Renamed    use the names of the model
    Selected   keep the columns of the model, in order
"""

from __future__ import annotations

import re

from .spec import DATA_FOLDER_DEFAULT, VALUE_MAPS, Column, Table

M_TYPES = {
    "string": "type text",
    "int64": "Int64.Type",
    "double": "type number",
    "date": "type date",
    "datetime": "type datetime",
    "boolean": "type logical",
}

CULTURE = "en-US"


def q(text: str) -> str:
    """An M text literal. In M the only escape inside a text is the doubled quote; a backslash is just a backslash."""
    return '"' + text.replace('"', '""') + '"'


def _items(items: list[str]) -> str:
    return "{" + ", ".join(items) + "}"


def parameter() -> str:
    """The text of the DataFolder parameter, as Power Query keeps it."""
    return f'{q(DATA_FOLDER_DEFAULT)} meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]'


def step_name(column: Column) -> str:
    return "Add" + re.sub(r"[^A-Za-z0-9]", "", column.name.title().replace(" ", ""))


def _transform_function(column: Column) -> str:
    if column.transform == "label":
        return 'each if _ = null then null else Text.Proper(Text.Replace(_, "_", " "))'
    assert column.transform is not None
    pairs = ", ".join(f"{code} = {q(label)}" for code, label in VALUE_MAPS[column.transform].items())
    return f"each if _ = null then null else Record.FieldOrDefault([{pairs}], _, _)"


def query(table: Table) -> str:
    """The M text of the query of one table, without any indentation of the file it will be written to."""
    kept = [c for c in table.columns if c.source]
    made = [c for c in table.columns if c.m]
    path = f'Text.TrimEnd(DataFolder, "\\") & "\\{table.csv}.csv"'
    steps: list[tuple[str, str]] = [
        ("Source", f'Csv.Document(File.Contents({path}), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv])'),
        ("Headers", "Table.PromoteHeaders(Source, [PromoteAllScalars = true])"),
    ]
    last = "Headers"
    if table.drop:
        steps.append(("Dropped", f"Table.RemoveColumns({last}, {_items([q(h) for h in table.drop])})"))
        last = "Dropped"
    sources = [q(c.source or "") for c in kept]
    steps.append(("Cleaned", f'Table.ReplaceValue({last}, "", null, Replacer.ReplaceValue, {_items(sources)})'))
    types = [f"{{{q(c.source or '')}, {M_TYPES[c.dtype]}}}" for c in kept]
    steps.append(("Typed", f"Table.TransformColumnTypes(Cleaned, {_items(types)}, {q(CULTURE)})"))
    last = "Typed"
    labelled = [c for c in kept if c.transform]
    if labelled:
        entries = [f"{{{q(c.source or '')}, {_transform_function(c)}, type text}}" for c in labelled]
        steps.append(("Labelled", f"Table.TransformColumns(Typed, {_items(entries)})"))
        last = "Labelled"
    for c in made:
        name = step_name(c)
        steps.append((name, f"Table.AddColumn({last}, {q(c.name)}, each {c.m}, {M_TYPES[c.dtype]})"))
        last = name
    renames = [f"{{{q(c.source or '')}, {q(c.name)}}}" for c in kept if c.source != c.name]
    steps.append(("Renamed", f"Table.RenameColumns({last}, {_items(renames)})"))
    steps.append(("Selected", f"Table.SelectColumns(Renamed, {_items([q(c.name) for c in table.columns])})"))
    body = ",\n".join(f"    {name} = {expr}" for name, expr in steps)
    return f"let\n{body}\nin\n    Selected"


def pq_file(table: Table) -> str:
    """The same query as a .pq file, for people who paste it into the Advanced Editor instead of opening the project."""
    return (
        f"// labtrack-bi: query of the table {table.name} ({table.csv}.csv).\n"
        f"// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query {table.name}.\n"
        f"// Needs the DataFolder parameter first (see DataFolder.pq).\n" + query(table) + "\n"
    )


def parameter_file() -> str:
    return (
        "// labtrack-bi: the DataFolder parameter.\n"
        "// Power Query > Manage Parameters > New Parameter: Name DataFolder, Type Text, Required, and as the current value\n"
        "// the full path of the data folder of this repository. Or: New Source > Blank Query > Advanced Editor > paste\n"
        "// the line below, and name the query DataFolder.\n" + parameter() + "\n"
    )
