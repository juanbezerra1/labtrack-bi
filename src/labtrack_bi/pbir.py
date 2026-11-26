"""The report half of the Power BI Project: the files of `labtrack.Report` and the `.pbip` that opens everything.

The report is made with four empty pages, one per page of the spec (1280 x 720) and a custom theme. The visuals are not
written here on purpose: they are built in Power BI Desktop by following docs/report-spec.md (see the README for why).
The shape of every file was copied from a project that Power BI Desktop itself saved.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from importlib import resources

from .spec import PAGE_HEIGHT, PAGE_WIDTH, PAGES, PROJECT, Page
from .tmdl import NAMESPACE

SCHEMAS = "https://developer.microsoft.com/json-schemas/fabric"
BASE_THEME = "CY24SU10"
CUSTOM_THEME_FILE = "LabTrack.json"
REPORT_VERSION_AT_IMPORT = "5.61"

SEMANTIC_MODEL_FOLDER = f"{PROJECT}.SemanticModel"
REPORT_FOLDER = f"{PROJECT}.Report"

# The palette of the dataviz skill, validated for light mode (see docs/design.md): eight categorical colors in a fixed order.
PALETTE = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948")
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
GOOD, WARNING, CRITICAL = "#0ca30c", "#fab219", "#d03b3b"
SEQUENTIAL = ("#cde2fb", "#2a78d6", "#184f95")


def dumps(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def page_id(page: Page) -> str:
    """Twenty hexadecimal characters, the way Power BI names a page folder; the same page always gets the same name."""
    return hashlib.sha1(f"labtrack-bi/page/{page.name}".encode()).hexdigest()[:20]


def logical_id(kind: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"labtrack-bi/logical-id/{kind}"))


def pbip() -> str:
    return dumps(
        {
            "version": "1.0",
            "artifacts": [{"report": {"path": REPORT_FOLDER}}],
            "settings": {"enableAutoRecovery": True},
        }
    )


def platform(kind: str) -> str:
    return dumps(
        {
            "$schema": f"{SCHEMAS}/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": kind, "displayName": PROJECT},
            "config": {"version": "2.0", "logicalId": logical_id(kind)},
        }
    )


def pbism() -> str:
    return dumps({"version": "4.1", "settings": {}})


def editor_settings() -> str:
    return dumps(
        {
            "version": "1.0",
            "autodetectRelationships": True,
            "parallelQueryLoading": True,
            "relationshipImportEnabled": True,
            "shouldNotifyUserOfNameConflictResolution": True,
        }
    )


def pbir() -> str:
    return dumps({"version": "4.0", "datasetReference": {"byPath": {"path": f"../{SEMANTIC_MODEL_FOLDER}"}}})


def version_json() -> str:
    return dumps({"$schema": f"{SCHEMAS}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"})


def report_json() -> str:
    return dumps(
        {
            "$schema": f"{SCHEMAS}/item/report/definition/report/1.2.0/schema.json",
            "themeCollection": {
                "baseTheme": {"name": BASE_THEME, "reportVersionAtImport": REPORT_VERSION_AT_IMPORT, "type": "SharedResources"},
                "customTheme": {
                    "name": CUSTOM_THEME_FILE,
                    "reportVersionAtImport": REPORT_VERSION_AT_IMPORT,
                    "type": "RegisteredResources",
                },
            },
            "layoutOptimization": "None",
            "resourcePackages": [
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": [{"name": CUSTOM_THEME_FILE, "path": CUSTOM_THEME_FILE, "type": "CustomTheme"}],
                },
                {
                    "name": "SharedResources",
                    "type": "SharedResources",
                    "items": [{"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}],
                },
            ],
            "settings": {
                "useStylableVisualContainerHeader": True,
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "useEnhancedTooltips": True,
                "useDefaultAggregateDisplayName": True,
            },
            "slowDataSourceSettings": {
                "isCrossHighlightingDisabled": False,
                "isSlicerSelectionsButtonEnabled": False,
                "isFilterSelectionsButtonEnabled": False,
                "isFieldWellButtonEnabled": False,
                "isApplyAllButtonEnabled": False,
            },
        }
    )


def pages_json() -> str:
    ids = [page_id(p) for p in PAGES]
    return dumps(
        {"$schema": f"{SCHEMAS}/item/report/definition/pagesMetadata/1.0.0/schema.json", "pageOrder": ids, "activePageName": ids[0]}
    )


def page_json(page: Page) -> str:
    return dumps(
        {
            "$schema": f"{SCHEMAS}/item/report/definition/page/1.3.0/schema.json",
            "name": page_id(page),
            "displayName": page.name,
            "displayOption": "FitToPage",
            "height": PAGE_HEIGHT,
            "width": PAGE_WIDTH,
        }
    )


def theme_json() -> str:
    text = {"fontFace": "Segoe UI"}
    return dumps(
        {
            "name": "LabTrack",
            "dataColors": list(PALETTE),
            "bad": CRITICAL,
            "neutral": WARNING,
            "good": GOOD,
            "minimum": SEQUENTIAL[0],
            "center": SEQUENTIAL[1],
            "maximum": SEQUENTIAL[2],
            "foreground": INK,
            "foregroundNeutralSecondary": INK_SECONDARY,
            "backgroundLight": "#f1f0ee",
            "foregroundNeutralTertiary": "#c9c8c4",
            "backgroundNeutral": "#e6e5e1",
            "textClasses": {
                "label": {"color": INK, **text, "fontSize": 10},
                "callout": {"color": INK, **text, "fontSize": 24},
                "title": {"color": INK, **text, "fontSize": 12},
                "header": {"color": INK_SECONDARY, **text, "fontSize": 10},
            },
            "visualStyles": {
                "*": {
                    "*": {
                        "border": [{"show": False}],
                        "visualHeader": [{"foreground": {"solid": {"color": INK_SECONDARY}}}],
                    }
                },
                "page": {"*": {"background": [{"color": {"solid": {"color": SURFACE}}, "transparency": 0}]}},
            },
        }
    )


def base_theme_bytes() -> bytes:
    """The base theme that Power BI ships (CY24SU10). The report names it, so the project carries a copy of it."""
    return resources.files("labtrack_bi").joinpath("resources").joinpath(f"{BASE_THEME}.json").read_bytes()


def report_files() -> dict[str, str]:
    """Path (relative to the .Report folder) -> text. The base theme is binary-safe JSON and is added by the generator."""
    files = {
        ".platform": platform("Report"),
        "definition.pbir": pbir(),
        "definition/version.json": version_json(),
        "definition/report.json": report_json(),
        "definition/pages/pages.json": pages_json(),
        f"StaticResources/RegisteredResources/{CUSTOM_THEME_FILE}": theme_json(),
    }
    for page in PAGES:
        files[f"definition/pages/{page_id(page)}/page.json"] = page_json(page)
    return files
