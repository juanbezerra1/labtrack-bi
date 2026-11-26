"""The Power Query (M) code of the model."""

from __future__ import annotations

from pathlib import Path

import pytest

from labtrack_bi import mcode, mlint
from labtrack_bi.spec import DATA_FOLDER_DEFAULT, TABLES


@pytest.mark.parametrize("table", TABLES, ids=lambda t: t.name)
def test_the_query_of_each_table_passes_the_linter(table) -> None:  # type: ignore[no-untyped-def]
    assert mlint.lint(mcode.query(table), table.name) == []


def test_the_parameter_file(root: Path) -> None:
    text = (root / "model/powerquery/DataFolder.pq").read_text(encoding="utf-8")
    assert DATA_FOLDER_DEFAULT in text and "IsParameterQuery = true" in text


def test_every_query_reads_its_csv_from_the_data_folder() -> None:
    for table in TABLES:
        query = mcode.query(table)
        assert f'"\\{table.csv}.csv"' in query
        assert "Text.TrimEnd(DataFolder" in query
        assert "Encoding = 65001" in query and "QuoteStyle.Csv" in query


def test_the_library_knows_the_functions_the_model_uses() -> None:
    library = mlint.library()
    for name in ("Csv.Document", "Table.PromoteHeaders", "Table.TransformColumnTypes", "Table.AddColumn", "Text.Proper"):
        assert name in library
    assert library["Table.TransformColumnTypes"] == mlint.Signature(2, 3)


@pytest.mark.parametrize(
    "code, expected",
    [
        ("let Source = Table.PromoteHeader(x, [PromoteAllScalars = true]) in Source", "not in the library"),
        ("let Source = Table.PromoteHeaders(x, [PromoteAllScalars = true], 3, 4) in Source", "takes 1 to 2 argument(s), it has 4"),
        ("let Source = Table.PromoteHeaders() in Source", "takes 1 to 2 argument(s), it has 0"),
        ("let Source = Table.PromoteHeaders(x in Source", "not closed"),
        ('let Source = Text.From("abc) in Source', "string is not closed"),
        ("let Source = Text.From(x)) in Source", "closes nothing"),
        ("let Source = Text.From({1, 2) in Source", "where '}' was expected"),
        ("let Source = Text.From(x) /* in Source", "comment is not closed"),
    ],
)
def test_the_linter_finds_the_mistakes(code: str, expected: str) -> None:
    assert any(expected in message for message in mlint.lint(code, "test"))


def test_the_linter_counts_arguments_inside_lists_and_strings() -> None:
    code = 'let T = Table.RenameColumns(S, {{"a, b", "c"}, {"d", "e"}}) in T'
    assert mlint.lint(code, "test") == []
    assert mlint.scan(code)[0][0].arguments == 2
    assert mlint.lint('let T = Text.From("(") in T', "test") == []  # a delimiter inside a string is text
    assert mlint.lint("let T = Text.From(1) // ) is a comment\nin T", "test") == []
