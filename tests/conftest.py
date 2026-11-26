"""Shared paths and fixtures for the tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from labtrack_bi import generate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def data_dir() -> Path:
    return ROOT / "data"


@pytest.fixture(scope="session")
def generated(root: Path) -> dict[str, bytes]:
    """Every generated file, made once for the whole run of the tests (it takes a few seconds)."""
    return generate.files(root)


@pytest.fixture(scope="session")
def pristine(root: Path, generated: dict[str, bytes]) -> bool:
    """True while the project folders are exactly what `labtrack-bi build` writes. Once Power BI Desktop has saved
    the project they are not, and the tests marked `seed` (which read the files of the generator byte by byte) skip."""
    return generate.project_state(root, generated) == "pristine"


@pytest.fixture(autouse=True)
def _seed_tests_need_the_pristine_project(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("seed") and not request.getfixturevalue("pristine"):
        pytest.skip(
            "labtrack.pbip was saved by Power BI Desktop: the files of the generator are no longer compared "
            "byte by byte (see `labtrack-bi check-model`)"
        )
