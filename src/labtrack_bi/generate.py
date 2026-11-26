"""Makes every generated file of the repository, writes them, and checks that they are up to date.

Two kinds of file:

* the DERIVED files (the Power Query and DAX files in model/, the documents in docs/, the drawings): they are always
  written again from the spec and always compared byte by byte;
* the PROJECT (labtrack.pbip and the two folders next to it): written once. From the first time you save in Power BI
  Desktop it is Desktop's, which rewrites the files its own way, so `build` leaves it alone (unless you ask for
  `--reset-project`) and `check` no longer compares it byte by byte; `check-model` compares what the files say.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

from . import dax, docs, expected, mcode, pbir, tmdl, wireframe
from .spec import PROJECT, TABLES

DATA_DIR = "data"
PBIP = f"{PROJECT}.pbip"
PROJECT_FOLDERS = (pbir.SEMANTIC_MODEL_FOLDER, pbir.REPORT_FOLDER)
LOCAL_ONLY = (".pbi/localSettings.json", ".pbi/cache.abf")  # Desktop makes them on each computer; Git ignores them


def files(root: Path) -> dict[str, bytes]:
    """Path (relative to the repository, with /) -> content of every file that `build` writes."""
    text: dict[str, str] = {PBIP: pbir.pbip()}
    model = pbir.SEMANTIC_MODEL_FOLDER
    text[f"{model}/.platform"] = pbir.platform("SemanticModel")
    text[f"{model}/definition.pbism"] = pbir.pbism()
    text[f"{model}/.pbi/editorSettings.json"] = pbir.editor_settings()
    for path, content in tmdl.semantic_model_files().items():
        text[f"{model}/{path}"] = content
    for path, content in pbir.report_files().items():
        text[f"{pbir.REPORT_FOLDER}/{path}"] = content
    for table in TABLES:
        text[f"model/powerquery/{table.name}.pq"] = mcode.pq_file(table)
    text["model/powerquery/DataFolder.pq"] = mcode.parameter_file()
    text["model/measures.dax"] = dax.measures_file()
    text["model/check.dax"] = expected.check_file()
    text["docs/model.md"] = docs.model_markdown()
    text["docs/report-spec.md"] = docs.report_markdown()
    text["docs/expected-numbers.md"] = expected.expected_markdown(root / DATA_DIR)
    text["docs/expected-numbers.json"] = expected.expected_json(root / DATA_DIR)
    text.update(wireframe.svg_files(root / DATA_DIR))
    out = {path: content.encode("utf-8") for path, content in text.items()}
    out[f"{pbir.REPORT_FOLDER}/StaticResources/SharedResources/BaseThemes/{pbir.BASE_THEME}.json"] = pbir.base_theme_bytes()
    return out


def is_project_path(path: str) -> bool:
    return path == PBIP or path.startswith(tuple(f"{folder}/" for folder in PROJECT_FOLDERS))


def _existing_project_files(root: Path) -> set[str]:
    found = {PBIP} if (root / PBIP).is_file() else set()
    for folder in PROJECT_FOLDERS:
        base = root / folder
        if base.is_dir():
            found |= {p.relative_to(root).as_posix() for p in base.rglob("*") if p.is_file()}
    return {p for p in found if not p.endswith(LOCAL_ONLY)}


def project_state(root: Path, made: dict[str, bytes]) -> str:
    """'missing' (there is no project), 'pristine' (exactly the files that `build` writes) or 'saved' (anything
    else: Power BI Desktop has saved it, or someone edited the files)."""
    wanted = {p: c for p, c in made.items() if is_project_path(p)}
    have = _existing_project_files(root)
    if not have:
        return "missing"
    if have == set(wanted) and all((root / p).read_bytes() == c for p, c in wanted.items()):
        return "pristine"
    return "saved"


@dataclass
class Built:
    written: list[str] = field(default_factory=list)
    project: str = "missing"  # the state of the project before the build
    kept: bool = False  # True: the project was Desktop's and was left alone
    backups: list[str] = field(default_factory=list)


def _backup(root: Path, folder: str) -> str:
    source = root / folder
    n = 0
    while True:
        target = root / f"{folder}.backup{'' if n == 0 else n}"
        if not target.exists():
            shutil.move(str(source), str(target))
            return target.name
        n += 1


def build(root: Path, reset_project: bool = False) -> Built:
    """Writes the generated files (LF line endings, UTF-8)."""
    made = files(root)
    state = project_state(root, made)
    result = Built(project=state)
    write_project = state != "saved" or reset_project
    if state == "saved" and reset_project:
        for folder in PROJECT_FOLDERS:
            if (root / folder).is_dir():
                result.backups.append(_backup(root, folder))
        if (root / PBIP).exists():
            (root / PBIP).unlink()
    result.kept = not write_project
    for path, content in sorted(made.items()):
        if is_project_path(path) and not write_project:
            continue
        target = root / path
        if not target.exists() or target.read_bytes() != content:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            result.written.append(path)
    return result


@dataclass
class Checked:
    problems: list[str]
    project: str


def check(root: Path) -> Checked:
    """The derived files that are missing or different from what `build` would write. The project is compared byte
    by byte only while it is pristine."""
    made = files(root)
    state = project_state(root, made)
    problems = []
    for path, content in sorted(made.items()):
        if is_project_path(path) and state == "saved":
            continue
        target = root / path
        if not target.exists():
            problems.append(f"missing: {path}")
        elif target.read_bytes() != content:
            problems.append(f"out of date: {path}")
    return Checked(problems, state)
