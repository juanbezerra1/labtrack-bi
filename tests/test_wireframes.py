"""The drawings of the model and of the pages."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from labtrack_bi import wireframe
from labtrack_bi.spec import PAGE_HEIGHT, PAGE_WIDTH, PAGES, TABLES


def test_every_drawing_is_well_formed_svg(root: Path) -> None:
    files = sorted((root / "docs" / "img").glob("*.svg"))
    assert len(files) == 1 + len(PAGES)
    for path in files:
        tree = ET.parse(path)
        assert tree.getroot().tag == "{http://www.w3.org/2000/svg}svg", path.name
        assert tree.getroot().find("{http://www.w3.org/2000/svg}title") is not None, path.name


def test_no_title_is_cut_in_the_drawings() -> None:
    """The drawing shortens a title that does not fit; a title that is shortened here is too long for the visual."""
    for page in PAGES:
        for v in page.visuals:
            width = v.w - 24
            if v.kind == "slicer":
                assert wireframe._fit(f"Slicer: {v.title}", width) == f"Slicer: {v.title}", (page.name, v.title)
            else:
                assert wireframe._fit(v.title, width, 18 if v.kind == "textbox" else 11) == v.title, (page.name, v.title)


def test_the_visuals_are_inside_the_page_and_do_not_overlap() -> None:
    for page in PAGES:
        boxes = [(v.x, v.y, v.x + v.w, v.y + v.h, v.title) for v in page.visuals]
        for x0, y0, x1, y1, title in boxes:
            assert 0 <= x0 < x1 <= PAGE_WIDTH and 0 <= y0 < y1 <= PAGE_HEIGHT, (page.name, title)
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                overlap = min(a[2], b[2]) - max(a[0], b[0]) > 0 and min(a[3], b[3]) - max(a[1], b[1]) > 0
                assert not overlap, (page.name, a[4], b[4])


def test_the_model_drawing_names_every_table_and_every_relationship(root: Path) -> None:
    text = (root / "docs/img/model.svg").read_text(encoding="utf-8")
    for table in TABLES:
        assert f">{table.name}</text>" in text
    assert len(re.findall(r"<polygon ", text)) == 7  # one arrow per relationship
    assert text.count(">1</text>") == 7 and text.count(">*</text>") == 7


def test_the_drawings_cover_the_whole_spec_of_a_page(root: Path) -> None:
    for number, page in enumerate(PAGES, start=1):
        text = (root / "docs" / "img" / f"wireframe-{wireframe.page_file_name(number, page)}").read_text(encoding="utf-8")
        assert text.count('r="10" fill="#2a78d6"') == len(page.visuals)  # one numbered badge per visual
