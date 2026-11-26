"""The command line: `labtrack-bi build | check | expected | add-screenshots`."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import __version__, expected, generate, model_check, report_check
from .spec import PAGES
from .wireframe import page_file_name

START, END = "<!-- screenshots:start -->", "<!-- screenshots:end -->"
README_TEXT = {"README.md": ("Screenshots of the report", "page"), "README.pt-BR.md": ("Capturas de tela do relatório", "página")}


def run_hint(command: str) -> str:
    """How to type a subcommand where the person is: `py -m labtrack_bi build` on Windows, `python3 -m labtrack_bi build`
    elsewhere. The shorter `labtrack-bi build` only works when the Scripts folder of Python is on the PATH."""
    return f"{'py' if sys.platform == 'win32' else 'python3'} -m labtrack_bi {command}"


def find_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / "labtrack.pbip").exists() or (folder / "pyproject.toml").exists() and (folder / "src" / "labtrack_bi").exists():
            return folder
    return start


def screenshot_name(number: int, page_name: str) -> str:
    return "screenshot-" + page_file_name(number, next(p for p in PAGES if p.name == page_name)).split("-", 2)[2].replace(".svg", ".png")


def add_screenshots(root: Path) -> int:
    """Puts the screenshots that exist in docs/img/ into the two READMEs, between the markers."""
    found = [(i, p) for i, p in enumerate(PAGES, start=1) if (root / "docs" / "img" / screenshot_name(i, p.name)).exists()]
    if not found:
        print("No screenshots: save one PNG per page in docs/img/ with the names:")
        for i, p in enumerate(PAGES, start=1):
            print(f"  docs/img/{screenshot_name(i, p.name)}")
        return 1
    for readme, (heading, word) in README_TEXT.items():
        path = root / readme
        text = path.read_text(encoding="utf-8")
        block = "\n".join(
            f"**{word.capitalize()} {i}: {p.name}**\n\n![{p.name}](docs/img/{screenshot_name(i, p.name)})\n" for i, p in found
        )
        match = re.search(re.escape(START) + ".*?" + re.escape(END), text, re.DOTALL)
        if match is None:
            print(f"{readme}: the markers {START} and {END} are missing")
            return 1
        replaced = text[: match.start()] + f"{START}\n{block}\n{END}" + text[match.end() :]
        path.write_text(replaced, encoding="utf-8", newline="\n")
        print(f"{readme}: {len(found)} screenshot(s) added under '{heading}'")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="labtrack-bi", description="Builds the files of the Power BI project from the spec.")
    parser.add_argument("--version", action="version", version=f"labtrack-bi {__version__}")
    parser.add_argument("--root", type=Path, default=None, help="the repository folder (default: found from the current folder)")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="write the generated files (the project only the first time)")
    build.add_argument(
        "--reset-project",
        action="store_true",
        help="write the project again over the one saved by Power BI Desktop (the old folders are kept as .backup)",
    )
    sub.add_parser("check", help="fail if a generated file is missing or out of date")
    sub.add_parser("expected", help="print the expected numbers as Markdown")
    sub.add_parser("add-screenshots", help="put the screenshots of docs/img/ into the READMEs")
    check_model = sub.add_parser("check-model", help="compare the model saved in the project with the spec")
    check_model.add_argument("model", nargs="?", type=Path, default=None, help="the model folder (default: labtrack.SemanticModel)")
    check_report = sub.add_parser("check-report", help="compare the report saved by Power BI Desktop with the spec")
    check_report.add_argument("report", nargs="?", type=Path, default=None, help="the report folder (default: labtrack.Report)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = (args.root or find_root(Path.cwd())).resolve()
    if args.command == "build":
        built = generate.build(root, reset_project=args.reset_project)
        for backup in built.backups:
            print(f"kept the old folder as {backup}")
        print(f"{len(built.written)} file(s) written" if built.written else "everything was already up to date")
        for path in built.written:
            print(f"  {path}")
        if built.kept:
            print(
                "labtrack.pbip was saved by Power BI Desktop: it was left as it is. "
                f"`{run_hint('check-model')}` compares it with the spec; `{run_hint('build --reset-project')}` writes it again."
            )
        return 0
    if args.command == "check":
        checked = generate.check(root)
        for problem in checked.problems:
            print(problem)
        if checked.project == "saved":
            print(f"labtrack.pbip: saved by Power BI Desktop, not compared byte by byte (see `{run_hint('check-model')}`)")
        print("ok" if not checked.problems else f"{len(checked.problems)} problem(s): run `{run_hint('build')}`")
        return 1 if checked.problems else 0
    if args.command == "check-model":
        folder = args.model or root / "labtrack.SemanticModel"
        problems = model_check.check_model(folder)
        for problem in problems:
            print(problem)
        print("ok: the model says what the spec says" if not problems else f"{len(problems)} difference(s) from the spec")
        return 1 if problems else 0
    if args.command == "expected":
        sys.stdout.write(expected.expected_markdown(root / generate.DATA_DIR))
        return 0
    if args.command == "check-report":
        folder = args.report or root / "labtrack.Report"
        try:
            result = report_check.check_report(folder)
        except (FileNotFoundError, ValueError) as error:
            print(error)
            return 2
        print(report_check.format_result(result))
        return 0 if result.ok else 1
    return add_screenshots(root)


if __name__ == "__main__":
    sys.exit(main())
