"""Drawings of the model and of the four report pages, as SVG, made from the spec.

They are wireframes, not screenshots: boxes where the visuals go, with the fields in each. They tell you where to put
what while you build the report; the README says plainly that the real screenshots come from Power BI Desktop.
"""

from __future__ import annotations

import math
from html import escape
from pathlib import Path

from .data import load
from .pbir import INK, INK_SECONDARY, PALETTE, SURFACE
from .spec import KIND_LABELS, PAGE_HEIGHT, PAGE_WIDTH, PAGES, RELATIONSHIPS, TABLES, Page, Visual

FONT = 'font-family="Segoe UI, Helvetica, Arial, sans-serif"'
LINE = "#c9c8c4"
FILL = {"slicer": "#eef4fc", "card": "#ffffff", "textbox": SURFACE, "table": "#ffffff"}
CHAR = 6.1  # width of one character at 11 px, a little generous


def _fit(text: str, width: float, size: float = 11) -> str:
    limit = max(int((width - 16) / (CHAR * size / 11)), 4)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _wrap(text: str, width: float, size: float = 11) -> list[str]:
    limit = max(int((width - 16) / (CHAR * size / 11)), 8)
    lines: list[str] = []
    line = ""
    for word in text.split(" "):
        if len(line) + len(word) + 1 > limit and line:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def _text(x: float, y: float, text: str, size: float = 11, weight: str = "400", fill: str = INK, anchor: str = "start") -> str:
    return (
        f'<text x="{x:.0f}" y="{y:.0f}" {FONT} font-size="{size}" font-weight="{weight}" fill="{fill}" '
        f'text-anchor="{anchor}">{escape(text)}</text>'
    )


def _visual(number: int, v: Visual) -> str:
    out = [f'<rect x="{v.x}" y="{v.y}" width="{v.w}" height="{v.h}" rx="6" fill="{FILL.get(v.kind, "#ffffff")}" stroke="{LINE}"/>']
    if v.kind == "card":
        out.append(_text(v.x + 10, v.y + 24, _fit(v.title, v.w - 24), 12, "600"))
        out.append(_text(v.x + 10, v.y + 44, "Card", 10, "400", INK_SECONDARY))
        out.append(_text(v.x + 10, v.y + 68, "123", 20, "600", PALETTE[0]))
    elif v.kind == "slicer":
        out.append(_text(v.x + 10, v.y + 18, _fit(f"Slicer: {v.title}", v.w - 24), 11, "600"))
        out.append(_text(v.x + 10, v.y + 34, _fit(", ".join(f for _, fs in v.fields for f in fs), v.w - 24), 10, "400", INK_SECONDARY))
    elif v.kind == "textbox":
        out.append(_text(v.x + 10, v.y + 28, _fit(v.title, v.w - 24), 18, "600"))
    else:
        out.append(_text(v.x + 10, v.y + 20, _fit(v.title, v.w - 24), 12, "600"))
        out.append(_text(v.x + 10, v.y + 36, KIND_LABELS[v.kind], 10, "400", INK_SECONDARY))
        y = v.y + 56
        for well, fields in v.fields:
            for line in _wrap(f"{well}: {', '.join(fields)}", v.w - 8, 10):
                if y > v.y + v.h - 8:
                    break
                out.append(_text(v.x + 10, y, line, 10, "400", INK))
                y += 14
        _glyph(out, v)
    out.append(f'<circle cx="{v.x + v.w - 14}" cy="{v.y + 14}" r="10" fill="{PALETTE[0]}"/>')
    out.append(_text(v.x + v.w - 14, v.y + 18, str(number), 11, "600", "#ffffff", "middle"))
    return "\n".join(out)


def _glyph(out: list[str], v: Visual) -> None:
    """A faint sketch of the chart in the lower right corner of the box."""
    gx, gy, gw, gh = v.x + v.w - 130, v.y + v.h - 70, 110, 56
    if v.w < 260 or v.h < 150:
        return
    if v.kind in ("clusteredColumn", "stackedColumn"):
        for i, h in enumerate((22, 36, 28, 44, 32)):
            out.append(f'<rect x="{gx + 4 + i * 21}" y="{gy + gh - h}" width="14" height="{h}" fill="{PALETTE[0]}" opacity="0.25"/>')
    elif v.kind == "clusteredBar":
        for i, w in enumerate((90, 66, 50, 30)):
            out.append(f'<rect x="{gx}" y="{gy + 4 + i * 13}" width="{w}" height="9" fill="{PALETTE[0]}" opacity="0.25"/>')
    elif v.kind == "line":
        out.append(
            f'<polyline points="{gx},{gy + 48} {gx + 28},{gy + 36} {gx + 56},{gy + 30} {gx + 84},{gy + 16} {gx + 110},{gy + 6}" '
            f'fill="none" stroke="{PALETTE[0]}" stroke-width="2" opacity="0.35"/>'
        )
    elif v.kind == "table":
        for i in range(5):
            out.append(f'<line x1="{gx}" y1="{gy + 6 + i * 12}" x2="{gx + gw}" y2="{gy + 6 + i * 12}" stroke="{LINE}"/>')


def page_svg(page: Page) -> str:
    body = "\n".join(_visual(i, v) for i, v in enumerate(page.visuals, start=1))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {PAGE_WIDTH} {PAGE_HEIGHT}" width="{PAGE_WIDTH}" height="{PAGE_HEIGHT}" '
        f'role="img" aria-label="Wireframe of the page {escape(page.name)}">\n'
        f"<title>Wireframe of the page {escape(page.name)}</title>\n"
        f'<rect width="{PAGE_WIDTH}" height="{PAGE_HEIGHT}" fill="{SURFACE}"/>\n{body}\n</svg>\n'
    )


# ---------------------------------------------------------------------------------------------------------------
# the model
# ---------------------------------------------------------------------------------------------------------------
POSITION = {
    "Calendar": (30, 30),
    "Study": (290, 30),
    "Participant": (550, 30),
    "Researcher": (810, 30),
    "Session": (420, 290),
    "Trial": (30, 520),
    "Recording": (420, 520),
    "Device": (810, 520),
}
BOX_W = 230
MODEL_WIDTH, MODEL_HEIGHT = 1070, 740
ARROW = 9


def _box_height(rows: int) -> int:
    return 50 + 16 * rows


def _connector(x1: float, y1: float, x2: float, y2: float) -> list[str]:
    """A line from the side with one row (x1, y1) to the side with many rows (x2, y2): an arrow head says where
    the filter goes, and the marks 1 and * sit on opposite sides of the line, away from the boxes."""
    length = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / length, (y2 - y1) / length
    nx, ny = -uy, ux
    if ny < 0 or (ny == 0 and nx < 0):
        nx, ny = -nx, -ny
    tip = (x2, y2)
    base = (x2 - ARROW * ux, y2 - ARROW * uy)
    wing = ARROW * 0.45
    head = (
        f"{tip[0]:.1f},{tip[1]:.1f} {base[0] + wing * nx:.1f},{base[1] + wing * ny:.1f} {base[0] - wing * nx:.1f},{base[1] - wing * ny:.1f}"
    )
    return [
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{base[0]:.1f}" y2="{base[1]:.1f}" stroke="{INK_SECONDARY}" stroke-width="1.5"/>',
        f'<polygon points="{head}" fill="{INK_SECONDARY}"/>',
        _text(x1 + 24 * ux + 12 * nx, y1 + 24 * uy + 12 * ny + 4, "1", 12, "600", INK_SECONDARY, "middle"),
        _text(x2 - 26 * ux - 12 * nx, y2 - 26 * uy - 12 * ny + 6, "*", 16, "600", INK_SECONDARY, "middle"),
    ]


def model_svg(folder: Path) -> str:
    data = load(folder)
    boxes: dict[str, tuple[int, int, int, int]] = {}
    shapes: list[str] = []
    for table in TABLES:
        x, y = POSITION[table.name]
        visible = [c.name for c in table.columns if not c.hidden][:6]
        h = _box_height(len(visible) + 1)
        boxes[table.name] = (x, y, BOX_W, h)
        kind = "fact" if table.name in ("Session", "Recording", "Trial") else "dimension"
        shapes.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="{h}" rx="6" fill="#ffffff" stroke="{LINE}"/>')
        shapes.append(f'<rect x="{x}" y="{y}" width="{BOX_W}" height="30" rx="6" fill="{PALETTE[0] if kind == "fact" else "#eef4fc"}"/>')
        shapes.append(_text(x + 10, y + 20, table.name, 13, "600", "#ffffff" if kind == "fact" else INK))
        shapes.append(
            _text(
                x + BOX_W - 10, y + 20, f"{len(data[table.name]):,} rows", 10, "400", "#ffffff" if kind == "fact" else INK_SECONDARY, "end"
            )
        )
        for i, name in enumerate(visible):
            shapes.append(_text(x + 10, y + 50 + i * 16, name, 11, "400", INK))
        if len([c for c in table.columns if not c.hidden]) > 6:
            shapes.append(_text(x + 10, y + 50 + len(visible) * 16, "...", 11, "400", INK_SECONDARY))
    dimensions = ["Calendar", "Study", "Participant", "Researcher"]
    lines: list[str] = []
    x1 = y1 = x2 = y2 = 0.0
    for r in RELATIONSHIPS:
        many, one = r.many.split(".")[0], r.one.split(".")[0]
        mx, my, mw, mh = boxes[many]
        ox, oy, ow, oh = boxes[one]
        if many == "Session":  # four dimensions, each one on its own spot of the top edge of Session
            x1, y1 = ox + ow / 2, oy + oh
            x2, y2 = mx + 35 + dimensions.index(one) * 53, my
        elif one == "Session":  # straight down, Session to Recording
            x1, y1, x2, y2 = ox + ow / 2, oy + oh, mx + mw / 2, my
        elif one == "Device":  # to the left, Device to Recording
            x1, y1, x2, y2 = ox, oy + oh / 2, mx + mw, my + mh / 2
        else:  # to the left, Recording to Trial
            x1, y1, x2, y2 = ox, oy + oh / 2, mx + mw, my + mh / 2
        lines.extend(_connector(x1, y1, x2, y2))
    note = _text(
        30,
        MODEL_HEIGHT - 26,
        "1 = the side with one row (the dimension), * = the side with many rows. "
        "The arrow shows where the filter goes: from 1 to *, never back.",
        11,
        "400",
        INK_SECONDARY,
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {MODEL_WIDTH} {MODEL_HEIGHT}" width="{MODEL_WIDTH}" height="{MODEL_HEIGHT}" '
        f'role="img" aria-label="The model: four dimensions filter Session; Session and Device filter Recording; '
        f'Recording filters Trial">\n'
        f'<title>The model of labtrack-bi</title>\n<rect width="{MODEL_WIDTH}" height="{MODEL_HEIGHT}" fill="{SURFACE}"/>\n'
        + "\n".join(lines)
        + "\n"
        + "\n".join(shapes)
        + f"\n{note}\n</svg>\n"
    )


def page_file_name(number: int, page: Page) -> str:
    return f"page-{number}-{page.name.lower().replace(' ', '-')}.svg"


def svg_files(folder: Path) -> dict[str, str]:
    files = {"docs/img/model.svg": model_svg(folder)}
    for number, page in enumerate(PAGES, start=1):
        files[f"docs/img/wireframe-{page_file_name(number, page)}"] = page_svg(page)
    return files
