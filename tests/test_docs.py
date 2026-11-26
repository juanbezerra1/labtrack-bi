"""The documents say what is true: the numbers, the links, the commands and the names of the files.

None of this needs Power BI. A failure names the file, and the line when there is one, that is wrong.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from labtrack_bi import cli, engine, expected
from labtrack_bi import data as datamod
from labtrack_bi.spec import MEASURES, PAGES, RELATIONSHIPS, TABLES

from .support import BASE, SMALL_FILE_SCHEMAS

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ["docs/build-guide.md", "docs/build-guide.pt-BR.md"]
# the documents with instructions for a person on Windows: the commands in them are typed with `py`
INSTRUCTIONS = ["README.md", "README.pt-BR.md", *GUIDES, "docs/verification.md", "tools/README.md", "data/README.md"]
MARKDOWN = [
    *INSTRUCTIONS[:2],
    "data/README.md",
    "tools/README.md",
    *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "docs").glob("*.md")),
]
LANGUAGE = {"README.md": "en", "README.pt-BR.md": "pt", "docs/build-guide.md": "en", "docs/build-guide.pt-BR.md": "pt"}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------------------------------------------
# reading Markdown
# ---------------------------------------------------------------------------------------------------------------
def lines_with_fences(text: str) -> Iterator[tuple[int, str, bool]]:
    """(line number, line, inside a fenced block); the lines of the fences themselves are left out."""
    fence = None
    for number, line in enumerate(text.splitlines(), start=1):
        marker = re.match(r"^\s*(```|~~~)", line)
        if marker and (fence is None or marker.group(1) == fence):
            fence = None if fence else marker.group(1)
            continue
        yield number, line, fence is not None


def split_markdown(text: str) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """(prose, code), as lists of (line number, text): the lines of fenced blocks and the inline code are code, and the
    inline code is taken out of the prose."""
    prose: list[tuple[int, str]] = []
    code: list[tuple[int, str]] = []
    for number, line, fenced in lines_with_fences(text):
        if fenced:
            code.append((number, line))
            continue
        code.extend((number, span) for span in re.findall(r"`([^`]+)`", line))
        prose.append((number, re.sub(r"`[^`]*`", "", line)))
    return prose, code


def slug(heading: str) -> str:
    """The anchor that GitHub makes of a heading."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower().replace("`", "")).replace(" ", "-")


def headings(text: str) -> list[str]:
    found = (re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", line) for _, line, fenced in lines_with_fences(text) if not fenced)
    return [m.group(1) for m in found if m]


def table_after(text: str, heading: str) -> list[list[str]]:
    """The rows, as lists of cells, of the first table after the heading (the header and the separator are left out)."""
    lines = text.splitlines()
    assert heading in lines, f"no line {heading!r}"
    rows: list[list[str]] = []
    for line in lines[lines.index(heading) + 1 :]:
        if line.startswith("|"):
            rows.append([cell.strip() for cell in line.strip().strip("|").split("|")])
        elif rows:
            break
    return rows[2:]


def numbers_in(text: str, language: str) -> list[float]:
    """The numbers of a piece of text: `1,634` and `154.5` in English, `1.634` and `154,5` in Portuguese."""
    found = re.findall(r"\d[\d.,]*\d|\d", text)
    if language == "pt":
        return [float(n.replace(".", "").replace(",", ".")) for n in found]
    return [float(n.replace(",", "")) for n in found]


# ---------------------------------------------------------------------------------------------------------------
# what the documents have to agree with
# ---------------------------------------------------------------------------------------------------------------
def csv_rows(table_csv: str) -> int:
    with (ROOT / "data" / f"{table_csv}.csv").open(encoding="utf-8", newline="") as handle:
        return sum(1 for _ in csv.reader(handle)) - 1


ROWS = {t.name: csv_rows(t.csv) for t in TABLES}
VISUALS = sum(len(p.visuals) for p in PAGES)


@pytest.fixture(scope="module")
def overall() -> dict[str, float]:
    """Every measure with no filter, as the engine works it out from the CSV files."""
    check = expected.check_by_id("overall")
    rows = expected.rows_of(check, engine.whole(datamod.load(ROOT / "data")))
    return dict(zip(expected.columns_of(check), rows[0], strict=True))


# ---------------------------------------------------------------------------------------------------------------
# the numbers
# ---------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(("readme", "heading"), [("README.md", "## At a glance"), ("README.pt-BR.md", "## Em resumo")])
def test_the_glance_table_has_the_counts_of_the_spec_and_the_data(readme: str, heading: str) -> None:
    rows = table_after(read(readme), heading)
    shown = [int(float(numbers_in(row[-1], LANGUAGE[readme])[0])) for row in rows]
    queries = len(list((ROOT / "model" / "powerquery").glob("*.pq")))
    assert shown == [
        len(TABLES) + 1,  # the eight tables with data, and `Measures`
        len(RELATIONSHIPS),
        len(MEASURES),
        queries,
        len(PAGES),
        VISUALS,
        len(expected.CHECKS),
        sum(ROWS.values()),
    ]


@pytest.mark.parametrize(
    ("readme", "heading"), [("README.md", "## What the report will show"), ("README.pt-BR.md", "## O que o relatório vai mostrar")]
)
def test_the_page_table_has_the_pages_and_the_visuals_of_the_spec(readme: str, heading: str) -> None:
    rows = table_after(read(readme), heading)
    assert [(row[0], int(row[2])) for row in rows] == [(f"{i}. {p.name}", len(p.visuals)) for i, p in enumerate(PAGES, start=1)]


@pytest.mark.parametrize(("readme", "heading"), [("README.md", "## The numbers"), ("README.pt-BR.md", "## Os números")])
def test_the_numbers_of_the_readme_are_those_the_engine_works_out(readme: str, heading: str, overall: dict[str, float]) -> None:
    language = LANGUAGE[readme]
    rows = table_after(read(readme), heading)
    assert len(rows) == 7
    pct = lambda name: round(overall[name] * 100, 1)  # noqa: E731
    wanted = [
        ([overall["Sessions Closed"], overall["Sessions"]], [overall["Sessions Completed"], pct("Completion Rate")]),
        ([overall["Participants Enrolled"]], [overall["Participants Attended"]]),
        ([], [overall["Recordings"], overall["Trials"], overall["Valid Trials"]]),
        ([], [round(overall["Hours Recorded"], 1)]),
        ([], [pct("QC Pass Rate")]),
        ([], [pct("Trial Rejection Rate")]),
        ([], [round(overall["Mean Force CV Feedback On"], 2), round(overall["Mean Force CV Feedback Off"], 2)]),
    ]
    for row, (in_label, in_value) in zip(rows, wanted, strict=True):
        assert numbers_in(row[0], language) == pytest.approx(in_label, abs=1e-9), row
        assert numbers_in(row[1], language) == pytest.approx(in_value, abs=1e-9), row


WORDS = {
    "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "dois": 2, "três": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10,
}  # fmt: skip
# what a number before these words must be, and whether the number may be written in words ("seven relationships"; but
# "two measures" can be a few of them)
CLAIMS = {
    r"(?:DAX )?measures|medidas(?: DAX)?": ({len(MEASURES)}, False),
    r"relationships|relacionamentos": ({len(RELATIONSHIPS)}, True),
    r"check queries|consultas de conferência": ({len(expected.CHECKS)}, False),
    r"visuals|visuais": ({VISUALS, *(len(p.visuals) for p in PAGES)}, False),
}


@pytest.mark.parametrize("relative", [*INSTRUCTIONS[:4], "docs/design.md", "docs/verification.md"])
def test_the_counts_in_the_prose_are_those_of_the_spec(relative: str) -> None:
    prose, _ = split_markdown(read(relative))
    wrong = []
    for number, line in prose:
        for nouns, (allowed, in_words) in CLAIMS.items():
            written = rf"\d+|{'|'.join(WORDS)}" if in_words else r"\d+"
            for found in re.finditer(rf"\b({written}) ({nouns})\b", line):
                value = int(found.group(1)) if found.group(1).isdigit() else WORDS[found.group(1)]
                if value not in allowed:
                    wrong.append(f"{relative}:{number}: {found.group(0)!r}, the spec has {sorted(allowed)}")
    assert not wrong, "\n".join(wrong)


@pytest.mark.parametrize("relative", GUIDES)
def test_the_guide_has_the_row_counts_and_the_pages_of_the_spec(relative: str) -> None:
    text, language = read(relative), LANGUAGE[relative]
    cells = re.findall(r"^\s*\| (\w+) \| ([\d.,]+) \| (\w+) \| ([\d.,]+) \|$", text, re.MULTILINE)
    shown = {name: int(numbers_in(count, language)[0]) for left, a, right, b in cells for name, count in ((left, a), (right, b))}
    assert shown == ROWS
    pages = re.findall(r"\*\*(?:Page|Página) (\d), (.+?)\*\* \((\d+)(?: visuals| visuais)?\)", text)
    assert [(int(n), name, int(count)) for n, name, count in pages] == [(i, p.name, len(p.visuals)) for i, p in enumerate(PAGES, start=1)]


# ---------------------------------------------------------------------------------------------------------------
# the translations say the same things
# ---------------------------------------------------------------------------------------------------------------
def link_targets(relative: str) -> set[str]:
    prose, _ = split_markdown(read(relative))
    targets = {t for _, line in prose for t in LINK.findall(line)}
    return {t.replace("build-guide.pt-BR.md", "build-guide.md").replace("README.pt-BR.md", "README.md") for t in targets}


@pytest.mark.parametrize(("english", "portuguese"), [("README.md", "README.pt-BR.md"), (GUIDES[0], GUIDES[1])])
def test_the_two_languages_have_the_same_shape(english: str, portuguese: str) -> None:
    en, pt = read(english), read(portuguese)
    assert len(headings(en)) == len(headings(pt))
    assert [h[:3] for h in re.findall(r"^#+ ", en, re.MULTILINE)] == [h[:3] for h in re.findall(r"^#+ ", pt, re.MULTILINE)]
    assert sum(line.startswith("|") for line in en.splitlines()) == sum(line.startswith("|") for line in pt.splitlines())
    assert len(re.findall(r"^```", en, re.MULTILINE)) == len(re.findall(r"^```", pt, re.MULTILINE))
    assert link_targets(english) == link_targets(portuguese)


# ---------------------------------------------------------------------------------------------------------------
# links, commands, file names
# ---------------------------------------------------------------------------------------------------------------
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


@pytest.mark.parametrize("relative", MARKDOWN)
def test_every_link_and_image_resolves(relative: str) -> None:
    path = ROOT / relative
    problems = []
    for number, line in split_markdown(read(relative))[0]:
        for target in LINK.findall(line):
            if re.match(r"^(https?:|mailto:)", target):
                continue
            file_part, _, anchor = target.partition("#")
            destination = path.parent / file_part if file_part else path
            if not destination.exists():
                problems.append(f"{relative}:{number}: {target}: no such file")
            elif (
                anchor
                and destination.suffix == ".md"
                and anchor not in {slug(h) for h in headings(destination.read_text(encoding="utf-8"))}
            ):
                problems.append(f"{relative}:{number}: {target}: no such heading")
    assert not problems, "\n".join(problems)


def subcommands() -> dict[str, set[str]]:
    """Every subcommand of the program, with the options it accepts (its own and the ones before the subcommand)."""
    parser = cli.build_parser()
    group = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    shared = {option for a in parser._actions for option in a.option_strings}
    return {name: shared | {option for a in sub._actions for option in a.option_strings} for name, sub in group.choices.items()}


LAUNCHED = re.compile(r"\b(?:py|python3?) -m labtrack_bi\b((?: [^\s`]+)*)")
SHORT = re.compile(r"(?<![\w\\/.-])labtrack-bi\b((?: [^\s`]+)*)")
PLACEHOLDERS = {"<command>", "<comando>"}


def invalid_uses(text: str, where: str) -> list[str]:
    known = subcommands()
    problems = []
    for number, line in split_markdown(text)[1]:
        for pattern in (LAUNCHED, SHORT):
            for found in pattern.finditer(line):
                words = found.group(1).split(" #")[0].split()
                if not words or words[0] in PLACEHOLDERS:
                    continue
                if words[0] not in known:
                    problems.append(f"{where}:{number}: {found.group(0).strip()!r}: there is no subcommand {words[0]!r}")
                    continue
                problems.extend(
                    f"{where}:{number}: {words[0]} has no option {w}" for w in words[1:] if w.startswith("--") and w not in known[words[0]]
                )
    return problems


@pytest.mark.parametrize("relative", MARKDOWN)
def test_the_commands_in_the_documents_exist(relative: str) -> None:
    problems = invalid_uses(read(relative), relative)
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("relative", INSTRUCTIONS)
def test_the_commands_to_type_are_written_for_the_py_launcher(relative: str) -> None:
    """On Windows the command is `py`, and `labtrack-bi` only works when Python's Scripts folder is on the PATH, so the
    documents say `py -m labtrack_bi build` and mention the short form only as `labtrack-bi <command>`."""
    problems = []
    for number, line in split_markdown(read(relative))[1]:
        problems.extend(f"{relative}:{number}: {m.group(0)!r}" for m in re.finditer(r"\bpython3? -m\b|(?<!-m )\bpip install\b", line))
        for short in SHORT.finditer(line):
            words = short.group(1).split(" #")[0].split()
            if words and words[0] not in PLACEHOLDERS:
                problems.append(f"{relative}:{number}: {short.group(0).strip()!r}")
    assert not problems, "\n".join(problems)


def test_the_hints_of_the_program_name_real_commands_and_can_be_typed(monkeypatch: pytest.MonkeyPatch) -> None:
    source = (ROOT / "src" / "labtrack_bi" / "cli.py").read_text(encoding="utf-8")
    hints = re.findall(r"run_hint\('([^']+)'\)", source)
    assert hints, "no hint found: has the call changed?"
    known = subcommands()
    for hint in hints:
        name, *options = hint.split()
        assert name in known and set(options) <= known[name], hint
    monkeypatch.setattr(sys, "platform", "win32")
    assert cli.run_hint("build") == "py -m labtrack_bi build"
    monkeypatch.setattr(sys, "platform", "linux")
    assert cli.run_hint("check-model") == "python3 -m labtrack_bi check-model"


PATH = re.compile(r"(?<![\w/.\\-])((?:docs|tools|model|data|tests|src/labtrack_bi|\.github/workflows)/[\w.\-/]*\w)")
NOT_YET = re.compile(r"^docs/img/screenshot-")  # the names that the person gives to the screenshots that they take
TEXT_FILES = [
    *MARKDOWN,
    *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "src" / "labtrack_bi").glob("*.py")),
    *sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").glob("*.py") if p.name != "test_docs.py"),
    "tools/crosscheck_sql.py",
    "tools/check_m.cjs",
    ".github/workflows/ci.yml",
    "pyproject.toml",
]


@pytest.mark.parametrize("relative", TEXT_FILES)
def test_the_paths_that_a_file_names_exist(relative: str) -> None:
    missing = []
    for number, line in enumerate(read(relative).splitlines(), start=1):
        for found in PATH.finditer(line):
            path = found.group(1)
            if NOT_YET.match(path) or (ROOT / path).exists() or list((ROOT / path).parent.glob(Path(path).name + "*")):
                continue
            missing.append(f"{relative}:{number}: {path}")
    assert not missing, "\n".join(missing)


def test_the_workflow_runs_things_that_exist() -> None:
    text = read(".github/workflows/ci.yml")
    scripts = json.loads(read("tools/package.json"))["scripts"]
    assert re.findall(r"npm run (\S+)", text) == ["check-m"] and "check-m" in scripts
    known = subcommands()
    assert {c for c in re.findall(r"python -m labtrack_bi (\S+)", text) if not c.startswith("-")} <= set(known)
    test_names = re.findall(r"^def (test_\w+)", read("tests/test_pbir.py"), re.MULTILINE)
    for expression in re.findall(r"-k (\w+)", text):
        assert any(expression in name for name in test_names), expression
    for variable in set(re.findall(r"\bLABTRACK_BI_\w+", text)):
        assert variable in read("tests/test_pbir.py")
    assert 'node-version: "22"' in text and "ruff format --check ." in text and "mypy src" in text


@pytest.mark.parametrize("relative", [*GUIDES, "docs/verification.md"])
def test_the_first_aid_lines_are_the_ones_of_the_schemas(relative: str) -> None:
    text = read(relative)
    for file, schema in SMALL_FILE_SCHEMAS.items():
        assert f'| `{file}` | `"$schema": "{BASE}{schema}"' in text, f"{relative}: the line of {file}"


# ---------------------------------------------------------------------------------------------------------------
# add-screenshots
# ---------------------------------------------------------------------------------------------------------------
def test_add_screenshots_fills_the_markers_of_both_readmes_and_can_be_repeated(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    names = ["README.md", "README.pt-BR.md"]
    for name in names:
        shutil.copyfile(ROOT / name, tmp_path / name)
    images = tmp_path / "docs" / "img"
    images.mkdir(parents=True)
    before = {n: (tmp_path / n).read_bytes() for n in names}
    run = ["--root", str(tmp_path), "add-screenshots"]

    assert cli.main(run) == 1  # none yet: it says the names to use, and changes nothing
    assert "docs/img/screenshot-overview.png" in capsys.readouterr().out
    assert {n: (tmp_path / n).read_bytes() for n in names} == before

    shots = [cli.screenshot_name(i, p.name) for i, p in enumerate(PAGES, start=1)]
    for name in shots[:2]:
        (images / name).write_bytes(b"\x89PNG")
    assert cli.main(run) == 0
    first = {n: (tmp_path / n).read_text(encoding="utf-8") for n in names}
    for name, word in (("README.md", "Page"), ("README.pt-BR.md", "Página")):
        old, new = before[name].decode("utf-8"), first[name]
        assert new.count(cli.START) == 1 and new.count(cli.END) == 1
        assert new.split(cli.START)[0] == old.split(cli.START)[0] and new.split(cli.END)[1] == old.split(cli.END)[1]
        inside = new.split(cli.START)[1].split(cli.END)[0]
        assert re.findall(r"!\[[^\]]*\]\(([^)]+)\)", inside) == [f"docs/img/{s}" for s in shots[:2]]
        assert f"**{word} 1: {PAGES[0].name}**" in inside and f"**{word} 3" not in inside
        assert "\r" not in new

    assert cli.main(run) == 0  # again: the same text
    assert {n: (tmp_path / n).read_text(encoding="utf-8") for n in names} == first

    for name in shots[2:]:
        (images / name).write_bytes(b"\x89PNG")
    assert cli.main(run) == 0
    for name in names:
        inside = (tmp_path / name).read_text(encoding="utf-8").split(cli.START)[1].split(cli.END)[0]
        assert len(re.findall(r"!\[", inside)) == len(PAGES)
