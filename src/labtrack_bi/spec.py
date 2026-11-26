"""The one description of the Power BI project: tables, columns, relationships, measures and report pages.

Everything else is made from this file: the semantic model (TMDL), the Power Query files, the DAX file, the
documents in docs/ and the wireframes. The tests read the files that were made and compare them with what this module
produces, so nothing can drift. To change the model, change it here and run `labtrack-bi build`.
"""

from __future__ import annotations

from dataclasses import dataclass

DATA_FOLDER_DEFAULT = "C:\\labtrack-bi\\data"  # what the DataFolder parameter holds in the repository
PROJECT = "labtrack"  # names the .pbip file and its two folders
MEASURES_TABLE = "Measures"

# value -> label, for the columns that are codes in the database. The same maps are written into Power Query.
VALUE_MAPS: dict[str, dict[str, str]] = {
    "modality": {"emg": "EMG", "eeg": "EEG", "force": "Force"},
    "device_kind": {
        "dynamometer": "Dynamometer",
        "eeg_amplifier": "EEG amplifier",
        "emg_amplifier": "EMG amplifier",
        "stimulator": "Stimulator",
    },
    "role": {"pi": "PI", "postdoc": "Postdoc", "phd": "PhD", "msc": "MSc", "technician": "Technician"},
}

DTYPES = {"string", "int64", "double", "date", "datetime", "boolean"}


@dataclass(frozen=True)
class Column:
    """A column of the model.

    `source` is the header in the CSV file; a column without one is made in Power Query by the expression `m`, which
    may use [csv_header] of the source columns and the [Name] of the derived columns made before it.
    `transform` is "label" (code_like -> Code Like) or a key of VALUE_MAPS."""

    name: str
    dtype: str
    source: str | None = None
    m: str | None = None
    transform: str | None = None
    hidden: bool = False
    key: bool = False
    fmt: str | None = None
    sort_by: str | None = None
    desc: str = ""

    def __post_init__(self) -> None:
        assert self.dtype in DTYPES, self.name
        assert (self.source is None) != (self.m is None), f"{self.name}: a column has a source or an expression"
        assert self.transform in (None, "label", *VALUE_MAPS), self.name


@dataclass(frozen=True)
class Table:
    name: str
    csv: str  # file name without .csv
    columns: tuple[Column, ...]
    drop: tuple[str, ...] = ()  # CSV headers that are not imported
    desc: str = ""
    date_table: bool = False

    def source_headers(self) -> list[str]:
        """The headers of the CSV file, in order, as this table accounts for them (kept or dropped)."""
        return [c.source for c in self.columns if c.source] + list(self.drop)


@dataclass(frozen=True)
class Relationship:
    many: str  # "Table.Column", the side with many rows (the fact)
    one: str  # "Table.Column", the side with one row (the dimension)


@dataclass(frozen=True)
class Measure:
    name: str
    dax: str
    fmt: str
    folder: str
    desc: str


# ---------------------------------------------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------------------------------------------
def _key(name: str, source: str, desc: str = "") -> Column:
    return Column(name, "int64", source, hidden=True, fmt="0", desc=desc)


CALENDAR = Table(
    "Calendar",
    "dim_date",
    desc="One row per calendar day from 2023 to 2028, so that time intelligence has no gaps. Marked as the date table.",
    date_table=True,
    columns=(
        Column("Date", "date", "date_key", key=True, fmt="Short Date", desc="The day. The key of the table."),
        Column("Year", "int64", "year", fmt="0"),
        Column("Quarter", "int64", "quarter", fmt="0"),
        Column("Year-Quarter", "string", m='Text.From([year]) & " Q" & Text.From([quarter])', desc="For example 2025 Q3."),
        Column("Month No", "int64", "month_no", hidden=True, fmt="0", desc="Orders the month names."),
        Column("Year-Month", "string", "year_month", desc="For example 2025-03. Sorts correctly as text."),
        Column("Month", "string", "month_name", sort_by="Month No"),
        Column("Month Start", "date", "month_start", fmt="Short Date"),
        Column("ISO Weekday", "int64", "iso_weekday", hidden=True, fmt="0", desc="1 = Monday ... 7 = Sunday."),
        Column("Weekday", "string", "weekday_name", sort_by="ISO Weekday"),
        Column("Is Weekend", "boolean", "is_weekend"),
    ),
)

STUDY = Table(
    "Study",
    "dim_study",
    desc="The studies of the lab (bi.dim_study).",
    columns=(
        _key("Study Key", "study_key"),
        Column("Study Code", "string", "study_code", desc="Short stable code such as FFB-01."),
        Column("Study Title", "string", "title"),
        Column("Started On", "date", "started_on", fmt="Short Date"),
        Column("Ended On", "date", "ended_on", fmt="Short Date", desc="Empty while the study is open."),
        Column("Planned Visits", "int64", "planned_visits", fmt="0"),
        Column(
            "Target N",
            "int64",
            "target_n",
            hidden=True,
            fmt="0",
            desc="How many participants the study aims to enroll. Hidden: use the measure [Target N].",
        ),
    ),
)

PARTICIPANT = Table(
    "Participant",
    "dim_participant",
    desc="Pseudonymised participants (bi.dim_participant), plus age columns made here.",
    columns=(
        _key("Participant Key", "participant_key"),
        Column("Participant Code", "string", "participant_code"),
        Column("Birth Year", "int64", "birth_year", fmt="0"),
        Column("Sex", "string", "sex"),
        Column("Dominant Hand", "string", "dominant_hand", transform="label"),
        Column("Consent Date", "date", "consent_signed_on", fmt="Short Date"),
        Column("Withdrawn On", "date", "withdrawn_on", fmt="Short Date"),
        Column("Is Withdrawn", "boolean", "is_withdrawn"),
        Column("Status", "string", m='if [is_withdrawn] then "Withdrawn" else "Active"'),
        Column(
            "Age at Consent",
            "int64",
            m="Date.Year([consent_signed_on]) - [birth_year]",
            fmt="0",
            desc="Year of the consent minus birth year.",
        ),
        Column(
            "Age Band",
            "string",
            sort_by="Age Band Order",
            m='if [Age at Consent] < 30 then "Under 30" else if [Age at Consent] < 45 then "30-44" '
            'else if [Age at Consent] < 60 then "45-59" else "60+"',
        ),
        Column(
            "Age Band Order",
            "int64",
            hidden=True,
            fmt="0",
            m="if [Age at Consent] < 30 then 1 else if [Age at Consent] < 45 then 2 else if [Age at Consent] < 60 then 3 else 4",
        ),
    ),
)

RESEARCHER = Table(
    "Researcher",
    "dim_researcher",
    desc="The people who run sessions (bi.dim_researcher).",
    columns=(
        _key("Researcher Key", "researcher_key"),
        Column("Researcher", "string", "full_name"),
        Column("Role", "string", "role", transform="role"),
        Column("Hired On", "date", "hired_on", fmt="Short Date"),
        Column("Left On", "date", "left_on", fmt="Short Date"),
    ),
)

DEVICE = Table(
    "Device",
    "dim_device",
    desc="Amplifiers, dynamometers and stimulators (bi.dim_device).",
    columns=(
        _key("Device Key", "device_key"),
        Column("Kind", "string", "kind", transform="device_kind"),
        Column("Model", "string", "model"),
        Column("Serial No", "string", "serial_no"),
        Column("Home Room", "string", "home_room"),
        Column("Acquired On", "date", "acquired_on", fmt="Short Date"),
        Column("Retired On", "date", "retired_on", fmt="Short Date"),
    ),
)

SESSION = Table(
    "Session",
    "fact_session",
    desc="One row per session (bi.fact_session). Its recordings are counted from the Recording table, so the two "
    "pre-computed columns n_recordings and hours_recorded are not imported.",
    drop=("n_recordings", "hours_recorded"),
    columns=(
        _key("Session Key", "session_key"),
        Column("Session Date", "date", "date_key", fmt="Short Date", desc="The lab's calendar day of the session."),
        _key("Study Key", "study_key"),
        _key("Participant Key", "participant_key"),
        _key("Researcher Key", "researcher_key"),
        Column("Group", "string", "group_label", transform="label", desc="Control or intervention."),
        Column("Visit No", "int64", "visit_no", fmt="0"),
        Column("Room", "string", "room"),
        Column(
            "Status", "string", "status", transform="label", desc="Completed, Cancelled, No Show or Scheduled (a session in the future)."
        ),
        Column("Duration Minutes", "int64", "duration_min", fmt="0"),
        Column("Starts At", "datetime", "starts_local", fmt="General Date"),
    ),
)

RECORDING = Table(
    "Recording",
    "fact_recording",
    desc="One row per recording (bi.fact_recording). The date comes through Session; the trial counts are counted from "
    "the Trial table, so date_key, n_trials and n_valid_trials are not imported.",
    drop=("date_key", "n_trials", "n_valid_trials"),
    columns=(
        _key("Recording Key", "recording_key"),
        _key("Session Key", "session_key"),
        _key("Device Key", "device_key"),
        Column("Modality", "string", "modality", transform="modality"),
        Column("Sampling Rate Hz", "int64", "sampling_rate_hz", fmt="#,0"),
        Column("Channels", "int64", "n_channels", fmt="0"),
        Column("Duration Seconds", "double", "duration_s", fmt="#,0.0"),
        Column("Size MB", "double", "size_mb", fmt="#,0.00"),
        Column("QC", "string", "qc", transform="label", desc="Quality-control result: Passed, Flagged, Rejected or Pending."),
        Column(
            "Device Calibrated",
            "boolean",
            "device_calibrated",
            desc="False when the device had no valid passed calibration on the day of the recording.",
        ),
        Column("Calibration", "string", m='if [device_calibrated] then "Calibrated" else "Not calibrated"'),
    ),
)

TRIAL = Table(
    "Trial",
    "fact_trial",
    desc="One row per trial (bi.fact_trial). The session, the date and the modality come through Recording, so "
    "session_key, date_key and modality are not imported. The factors of the condition are split into columns here.",
    drop=("session_key", "date_key", "modality"),
    columns=(
        _key("Trial Key", "trial_key"),
        _key("Recording Key", "recording_key"),
        Column("Condition", "string", "condition", desc="For example hold_40_fb: hold at 40 percent of maximum force, feedback on."),
        Column("Trial No", "int64", "trial_no", fmt="0"),
        Column("Onset Seconds", "double", "onset_s", fmt="0.000"),
        Column("Duration Seconds", "double", "duration_s", fmt="0.000"),
        Column("Valid", "boolean", "valid", desc="False when the trial was rejected in review."),
        Column("Validity", "string", m='if [valid] then "Valid" else "Rejected"'),
        Column("Reject Reason", "string", "reject_reason", transform="label"),
        Column(
            "Feedback",
            "string",
            desc="On or Off for the force-feedback trials; empty for the others.",
            m='if Text.EndsWith([condition], "_nofb") then "Off" else if Text.EndsWith([condition], "_fb") then "On" else null',
        ),
        Column(
            "Hold Level",
            "int64",
            fmt="0",
            desc="Percent of maximum force of a hold trial; empty for the others.",
            m='if Text.StartsWith([condition], "hold_") then Int64.From(Number.FromText(Text.Middle([condition], 5, 2))) else null',
        ),
        Column(
            "Fatigue Phase",
            "string",
            desc="Pre or Post the fatiguing task; empty outside EMG-03.",
            m='if Text.StartsWith([condition], "fatigue_") then (if Text.EndsWith([condition], "_post") then "Post" else "Pre") else null',
        ),
        Column(
            "Stimulus Size",
            "string",
            desc="Small or Large visual stimulus; empty outside EEG-02.",
            m='if Text.StartsWith([condition], "stimulus_") then '
            '(if Text.EndsWith([condition], "_large") then "Large" else "Small") else null',
        ),
        Column("RMS", "double", "rms_mean_uv", fmt="0.00", desc="EMG: root mean square amplitude in microvolts, mean of the channels."),
        Column("MNF", "double", "mnf_hz", fmt="0.00", desc="EMG: mean frequency of the spectrum in hertz, mean of the channels."),
        Column("MDF", "double", "mdf_hz", fmt="0.00", desc="EMG: median frequency of the spectrum in hertz, mean of the channels."),
        Column(
            "Alpha Power",
            "double",
            "alpha_power_uv2",
            fmt="0.00",
            desc="EEG: band power at 8 to 13 Hz in microvolts squared, mean of the channels.",
        ),
        Column("Peak Force", "double", "peak_force_n", fmt="0.0", desc="Force: the highest force of the trial in newtons."),
        Column(
            "Force CV",
            "double",
            "force_cv_pct",
            fmt="0.000",
            desc="Force: coefficient of variation of the force in the hold phase, in percent. Lower is steadier.",
        ),
    ),
)

TABLES: tuple[Table, ...] = (CALENDAR, STUDY, PARTICIPANT, RESEARCHER, DEVICE, SESSION, RECORDING, TRIAL)

RELATIONSHIPS: tuple[Relationship, ...] = (
    Relationship("Session.Session Date", "Calendar.Date"),
    Relationship("Session.Study Key", "Study.Study Key"),
    Relationship("Session.Participant Key", "Participant.Participant Key"),
    Relationship("Session.Researcher Key", "Researcher.Researcher Key"),
    Relationship("Recording.Session Key", "Session.Session Key"),
    Relationship("Recording.Device Key", "Device.Device Key"),
    Relationship("Trial.Recording Key", "Recording.Recording Key"),
)

# ---------------------------------------------------------------------------------------------------------------
# measures
# ---------------------------------------------------------------------------------------------------------------
INT = "#,0"
PCT = "0.0%"


def _m(name: str, dax: str, fmt: str, folder: str, desc: str) -> Measure:
    return Measure(name, dax.strip("\n"), fmt, folder, desc)


MEASURES: tuple[Measure, ...] = (
    # ---- counts -------------------------------------------------------------------------------------
    _m("Sessions", "COUNTROWS(Session)", INT, "1 Counts", "Sessions in the current filter, whatever their status."),
    _m(
        "Participants Enrolled",
        "DISTINCTCOUNT(Session[Participant Key])",
        INT,
        "1 Counts",
        "Participants with at least one session booked in the current filter.",
    ),
    _m(
        "Participants Attended",
        'CALCULATE(DISTINCTCOUNT(Session[Participant Key]), Session[Status] = "Completed")',
        INT,
        "1 Counts",
        "Participants with at least one completed session. Not additive across studies: one person can be in two.",
    ),
    _m("Recordings", "COUNTROWS(Recording)", INT, "1 Counts", "Recordings in the current filter."),
    _m("Trials", "COUNTROWS(Trial)", INT, "1 Counts", "Trials in the current filter, valid or rejected."),
    _m("Hours Recorded", "DIVIDE(SUM(Recording[Duration Seconds]), 3600)", "#,0.0", "1 Counts", "Total recording time in hours."),
    _m("Data Volume GB", "DIVIDE(SUM(Recording[Size MB]), 1024)", "#,0.00", "1 Counts", "Total size of the recording files in gigabytes."),
    _m("Devices Used", "DISTINCTCOUNT(Recording[Device Key])", INT, "1 Counts", "Devices that made at least one recording."),
    # ---- sessions -----------------------------------------------------------------------------------
    _m("Sessions Completed", 'CALCULATE([Sessions], Session[Status] = "Completed")', INT, "2 Sessions", "Sessions that took place."),
    _m("Sessions Cancelled", 'CALCULATE([Sessions], Session[Status] = "Cancelled")', INT, "2 Sessions", "Sessions cancelled."),
    _m(
        "Sessions No Show",
        'CALCULATE([Sessions], Session[Status] = "No Show")',
        INT,
        "2 Sessions",
        "Sessions where the participant did not come.",
    ),
    _m("Sessions Scheduled", 'CALCULATE([Sessions], Session[Status] = "Scheduled")', INT, "2 Sessions", "Sessions still in the future."),
    _m(
        "Sessions Closed",
        "[Sessions] - [Sessions Scheduled]",
        INT,
        "2 Sessions",
        "Sessions whose day has passed: completed, cancelled or no show.",
    ),
    _m("Completion Rate", "DIVIDE([Sessions Completed], [Sessions Closed])", PCT, "2 Sessions", "Completed sessions over closed sessions."),
    _m("No Show Rate", "DIVIDE([Sessions No Show], [Sessions Closed])", PCT, "2 Sessions", "No-show sessions over closed sessions."),
    _m(
        "Cancellation Rate",
        "DIVIDE([Sessions Cancelled], [Sessions Closed])",
        PCT,
        "2 Sessions",
        "Cancelled sessions over closed sessions.",
    ),
    _m(
        "Avg Session Minutes",
        'CALCULATE(AVERAGE(Session[Duration Minutes]), Session[Status] = "Completed")',
        "0.0",
        "2 Sessions",
        "Mean length of a completed session, in minutes.",
    ),
    # ---- time ---------------------------------------------------------------------------------------
    _m(
        "Last Completed Session Date",
        'CALCULATE(MAX(Session[Session Date]), Session[Status] = "Completed")',
        "Short Date",
        "3 Time",
        "The day of the latest completed session in the current filter.",
    ),
    _m("Sessions YTD", "TOTALYTD([Sessions], 'Calendar'[Date])", INT, "3 Time", "Sessions from 1 January to the end of the period."),
    _m(
        "Sessions Previous Year",
        "CALCULATE([Sessions], SAMEPERIODLASTYEAR('Calendar'[Date]))",
        INT,
        "3 Time",
        "Sessions in the same period one year earlier.",
    ),
    _m(
        "Sessions YoY",
        "DIVIDE([Sessions] - [Sessions Previous Year], [Sessions Previous Year])",
        PCT,
        "3 Time",
        "Change of the number of sessions against the same period one year earlier.",
    ),
    _m(
        "Completed Sessions Running Total",
        """
VAR LastDay = CALCULATE([Last Completed Session Date], REMOVEFILTERS('Calendar'))
VAR ThisDay = MAX('Calendar'[Date])
RETURN
    IF(
        MIN('Calendar'[Date]) <= LastDay,
        CALCULATE([Sessions Completed], FILTER(ALL('Calendar'), 'Calendar'[Date] <= ThisDay))
    )""",
        INT,
        "3 Time",
        "Completed sessions from the start up to the end of the period; blank after the last completed session.",
    ),
    _m(
        "Participants Attended Running Total",
        """
VAR LastDay = CALCULATE([Last Completed Session Date], REMOVEFILTERS('Calendar'))
VAR ThisDay = MAX('Calendar'[Date])
RETURN
    IF(
        MIN('Calendar'[Date]) <= LastDay,
        CALCULATE([Participants Attended], FILTER(ALL('Calendar'), 'Calendar'[Date] <= ThisDay))
    )""",
        INT,
        "3 Time",
        "Participants who had attended by the end of the period; blank after the last completed session.",
    ),
    # ---- recruitment --------------------------------------------------------------------------------
    _m("Target N", "SUM(Study[Target N])", INT, "4 Recruitment", "The number of participants the studies aim to enroll."),
    _m(
        "Recruitment Progress",
        "DIVIDE([Participants Attended], [Target N])",
        PCT,
        "4 Recruitment",
        "Participants who attended over the target.",
    ),
    _m(
        "Participants Withdrawn",
        "CALCULATE(DISTINCTCOUNT(Session[Participant Key]), Participant[Is Withdrawn] = TRUE())",
        INT,
        "4 Recruitment",
        "Participants with a session in the filter who later withdrew consent.",
    ),
    _m("Withdrawal Rate", "DIVIDE([Participants Withdrawn], [Participants Enrolled])", PCT, "4 Recruitment", "Withdrawn over enrolled."),
    _m(
        "Visit Retention",
        """
IF(
    HASONEVALUE(Session[Visit No]),
    DIVIDE([Participants Attended], CALCULATE([Participants Attended], Session[Visit No] = 1))
)""",
        PCT,
        "4 Recruitment",
        "Participants who attended this visit over those who attended visit 1. "
        "Blank unless one visit is selected: put Visit No on the axis.",
    ),
    # ---- quality ------------------------------------------------------------------------------------
    _m(
        "Recordings Passed QC",
        'CALCULATE([Recordings], Recording[QC] = "Passed")',
        INT,
        "5 Quality",
        "Recordings that passed quality control.",
    ),
    _m(
        "QC Pass Rate",
        'DIVIDE([Recordings Passed QC], [Recordings] - CALCULATE([Recordings], Recording[QC] = "Pending"))',
        PCT,
        "5 Quality",
        "Passed over recordings already reviewed (pending ones are left out).",
    ),
    _m(
        "Uncalibrated Recordings",
        "CALCULATE([Recordings], Recording[Device Calibrated] = FALSE())",
        INT,
        "5 Quality",
        "Recordings made with a device that had no valid passed calibration that day.",
    ),
    _m(
        "Uncalibrated Rate", "DIVIDE([Uncalibrated Recordings], [Recordings])", PCT, "5 Quality", "Uncalibrated recordings over recordings."
    ),
    _m("Valid Trials", "CALCULATE([Trials], Trial[Valid] = TRUE())", INT, "5 Quality", "Trials that were not rejected."),
    _m("Rejected Trials", "CALCULATE([Trials], Trial[Valid] = FALSE())", INT, "5 Quality", "Trials rejected in review."),
    _m("Trial Rejection Rate", "DIVIDE([Rejected Trials], [Trials])", PCT, "5 Quality", "Rejected trials over trials."),
    _m("Avg Trials per Recording", "DIVIDE([Trials], [Recordings])", "0.0", "5 Quality", "Trials divided by recordings."),
    # ---- findings (valid trials only) ---------------------------------------------------------------
    _m(
        "Mean Force CV",
        "CALCULATE(AVERAGE(Trial[Force CV]), Trial[Valid] = TRUE())",
        "0.000",
        "6 Findings",
        "Mean coefficient of variation of the force over valid force trials, in percent.",
    ),
    _m(
        "Mean Force CV Feedback On",
        'CALCULATE([Mean Force CV], Trial[Feedback] = "On")',
        "0.000",
        "6 Findings",
        "Mean force CV in trials with the feedback on.",
    ),
    _m(
        "Mean Force CV Feedback Off",
        'CALCULATE([Mean Force CV], Trial[Feedback] = "Off")',
        "0.000",
        "6 Findings",
        "Mean force CV in trials with the feedback off.",
    ),
    _m(
        "Feedback Effect on Force CV",
        "[Mean Force CV Feedback On] - [Mean Force CV Feedback Off]",
        "0.000",
        "6 Findings",
        "Feedback on minus feedback off; negative means steadier force with the feedback.",
    ),
    _m(
        "Mean MDF",
        "CALCULATE(AVERAGE(Trial[MDF]), Trial[Valid] = TRUE())",
        "0.00",
        "6 Findings",
        "Mean median frequency of the EMG over valid trials, in hertz.",
    ),
    _m(
        "Mean RMS",
        "CALCULATE(AVERAGE(Trial[RMS]), Trial[Valid] = TRUE())",
        "0.00",
        "6 Findings",
        "Mean RMS amplitude of the EMG over valid trials, in microvolts.",
    ),
    _m(
        "Mean Alpha Power",
        "CALCULATE(AVERAGE(Trial[Alpha Power]), Trial[Valid] = TRUE())",
        "0.00",
        "6 Findings",
        "Mean alpha band power of the EEG over valid trials, in microvolts squared.",
    ),
    _m(
        "MDF Change After Fatigue",
        'CALCULATE([Mean MDF], Trial[Fatigue Phase] = "Post") - CALCULATE([Mean MDF], Trial[Fatigue Phase] = "Pre")',
        "0.00",
        "6 Findings",
        "Median frequency after the fatiguing task minus before it, in hertz.",
    ),
    _m(
        "RMS Change After Fatigue",
        'CALCULATE([Mean RMS], Trial[Fatigue Phase] = "Post") - CALCULATE([Mean RMS], Trial[Fatigue Phase] = "Pre")',
        "0.00",
        "6 Findings",
        "RMS amplitude after the fatiguing task minus before it, in microvolts.",
    ),
    _m(
        "Alpha Change Large vs Small Stimulus",
        'CALCULATE([Mean Alpha Power], Trial[Stimulus Size] = "Large") - CALCULATE([Mean Alpha Power], Trial[Stimulus Size] = "Small")',
        "0.00",
        "6 Findings",
        "Alpha power with the large stimulus minus the small one, in microvolts squared.",
    ),
)


def table_by_name(name: str) -> Table:
    return next(t for t in TABLES if t.name == name)


def measure_by_name(name: str) -> Measure:
    return next(m for m in MEASURES if m.name == name)


# ---------------------------------------------------------------------------------------------------------------
# report pages: what to build, visual by visual
# ---------------------------------------------------------------------------------------------------------------
PAGE_WIDTH, PAGE_HEIGHT = 1280, 720
VISUAL_KINDS = {"textbox", "slicer", "card", "stackedColumn", "clusteredColumn", "clusteredBar", "line", "table"}
KIND_LABELS = {
    "textbox": "Text box",
    "slicer": "Slicer",
    "card": "Card",
    "stackedColumn": "Stacked column chart",
    "clusteredColumn": "Clustered column chart",
    "clusteredBar": "Clustered bar chart",
    "line": "Line chart",
    "table": "Table",
}


@dataclass(frozen=True)
class Visual:
    kind: str
    title: str
    x: int
    y: int
    w: int
    h: int
    fields: tuple[tuple[str, tuple[str, ...]], ...] = ()  # (well, fields): "Table[Column]" or "[Measure]"
    notes: str = ""


@dataclass(frozen=True)
class Page:
    name: str
    purpose: str
    visuals: tuple[Visual, ...]


def _cards(names: tuple[str, ...], y: int, h: int, x0: int = 16, gap: int = 8, total: int = 1248) -> tuple[Visual, ...]:
    width = (total - gap * (len(names) - 1)) // len(names)
    return tuple(Visual("card", name, x0 + i * (width + gap), y, width, h, (("Fields", (f"[{name}]",)),)) for i, name in enumerate(names))


def _slicer(title: str, field: str, x: int, w: int, style: str) -> Visual:
    return Visual("slicer", title, x, 12, w, 44, (("Field", (field,)),), f"Style: {style}.")


def _title(text: str, note: str) -> Visual:
    return Visual("textbox", text, 16, 12, 640, 44, (), note)


PAGES: tuple[Page, ...] = (
    Page(
        "Overview",
        "How much work was done, how it ended, and how the three studies compare.",
        (
            _title("LabTrack - Overview", "Text box, 20 pt semibold. Add the sentence 'Synthetic data' under the title in 10 pt."),
            _slicer("Study", "Study[Study Code]", 700, 250, "Dropdown"),
            _slicer("Year", "Calendar[Year]", 960, 170, "Dropdown; select 2024, 2025 and 2026 or leave it empty"),
            *_cards(
                ("Participants Attended", "Sessions Completed", "Completion Rate", "Recordings", "Hours Recorded", "Trial Rejection Rate"),
                64,
                80,
            ),
            Visual(
                "stackedColumn",
                "Sessions by month and status",
                16,
                152,
                780,
                280,
                (("X-axis", ("Calendar[Year-Month]",)), ("Y-axis", ("[Sessions]",)), ("Legend", ("Session[Status]",))),
                "Filter the visual to Calendar[Year] 2024 to 2026. Turn the data labels off; keep the legend.",
            ),
            Visual(
                "clusteredBar",
                "Completed sessions by study",
                804,
                152,
                460,
                280,
                (("Y-axis", ("Study[Study Code]",)), ("X-axis", ("[Sessions Completed]",))),
                "Data labels on.",
            ),
            Visual(
                "line",
                "Completed sessions, cumulative",
                16,
                440,
                620,
                264,
                (("X-axis", ("Calendar[Year-Month]",)), ("Y-axis", ("[Completed Sessions Running Total]",))),
                "Filter the visual to Calendar[Year] 2024 to 2026. The line stops at the last completed session on purpose.",
            ),
            Visual(
                "table",
                "Study summary",
                644,
                440,
                620,
                264,
                (
                    (
                        "Columns",
                        (
                            "Study[Study Code]",
                            "[Participants Attended]",
                            "[Target N]",
                            "[Recruitment Progress]",
                            "[Sessions Completed]",
                            "[Completion Rate]",
                            "[Hours Recorded]",
                        ),
                    ),
                ),
                "Turn the totals row on. Participants Attended is not additive across studies, so the total is smaller than the sum.",
            ),
        ),
    ),
    Page(
        "Recruitment",
        "Who joined, how many came back for each visit, and how close each study is to its target.",
        (
            _title("LabTrack - Recruitment", "Text box, 20 pt semibold."),
            _slicer("Study", "Study[Study Code]", 700, 250, "Dropdown"),
            _slicer("Group", "Session[Group]", 960, 250, "Tile, horizontal (a row of buttons)"),
            *_cards(("Participants Attended", "Target N", "Recruitment Progress", "Participants Withdrawn", "Withdrawal Rate"), 64, 80),
            Visual(
                "line",
                "Participants who had attended, cumulative",
                16,
                152,
                620,
                280,
                (
                    ("X-axis", ("Calendar[Year-Month]",)),
                    ("Y-axis", ("[Participants Attended Running Total]",)),
                    ("Legend", ("Study[Study Code]",)),
                ),
                "Filter the visual to Calendar[Year] 2024 to 2026. Three lines, one per study; turn data labels on for the last point.",
            ),
            Visual(
                "clusteredColumn",
                "Participants at each visit",
                644,
                152,
                300,
                280,
                (("X-axis", ("Session[Visit No]",)), ("Y-axis", ("[Participants Attended]",)), ("Tooltips", ("[Visit Retention]",))),
                "Filter the visual to Visit No less than or equal to 4: every study plans four visits and the higher numbers are "
                "extra visits. Data labels on. The tooltip shows how many came back compared with visit 1.",
            ),
            Visual(
                "clusteredColumn",
                "Age band and sex",
                952,
                152,
                312,
                280,
                (("X-axis", ("Participant[Age Band]",)), ("Y-axis", ("[Participants Attended]",)), ("Legend", ("Participant[Sex]",))),
                "Data labels on (two series only).",
            ),
            Visual(
                "clusteredBar",
                "Participants by group",
                16,
                440,
                300,
                264,
                (("Y-axis", ("Session[Group]",)), ("X-axis", ("[Participants Attended]",))),
                "Data labels on.",
            ),
            Visual(
                "table",
                "Recruitment by study",
                324,
                440,
                940,
                264,
                (
                    (
                        "Columns",
                        (
                            "Study[Study Code]",
                            "Study[Study Title]",
                            "[Target N]",
                            "[Participants Attended]",
                            "[Recruitment Progress]",
                            "[Participants Withdrawn]",
                            "[Withdrawal Rate]",
                        ),
                    ),
                ),
                "Add data bars to Recruitment Progress (Format > Cell elements).",
            ),
        ),
    ),
    Page(
        "Data quality",
        "Where the data is weak: reviews that failed, trials rejected, and recordings made with devices that were not calibrated.",
        (
            _title("LabTrack - Data quality", "Text box, 20 pt semibold."),
            _slicer("Study", "Study[Study Code]", 700, 250, "Dropdown"),
            _slicer("Modality", "Recording[Modality]", 960, 304, "Tile, horizontal (a row of buttons)"),
            *_cards(("Recordings", "QC Pass Rate", "Trial Rejection Rate", "Uncalibrated Recordings", "Uncalibrated Rate"), 64, 80),
            Visual(
                "stackedColumn",
                "Recordings by month and QC result",
                16,
                152,
                620,
                280,
                (("X-axis", ("Calendar[Year-Month]",)), ("Y-axis", ("[Recordings]",)), ("Legend", ("Recording[QC]",))),
                "Filter the visual to Calendar[Year] 2024 to 2026. Four series: keep the legend visible.",
            ),
            Visual(
                "clusteredBar",
                "Rejected trials by reason",
                644,
                152,
                300,
                280,
                (("Y-axis", ("Trial[Reject Reason]",)), ("X-axis", ("[Rejected Trials]",))),
                "Sort by Rejected Trials, descending. Data labels on. Filter out the blank reason.",
            ),
            Visual(
                "clusteredBar",
                "Uncalibrated recordings by device",
                952,
                152,
                312,
                280,
                (("Y-axis", ("Device[Serial No]",)), ("X-axis", ("[Uncalibrated Recordings]",))),
                "Top N filter: top 8 by Uncalibrated Recordings, and keep only values above 0. Data labels on.",
            ),
            Visual(
                "table",
                "Devices",
                16,
                440,
                1248,
                264,
                (
                    (
                        "Columns",
                        (
                            "Device[Serial No]",
                            "Device[Kind]",
                            "[Recordings]",
                            "[Uncalibrated Recordings]",
                            "[Uncalibrated Rate]",
                            "[Trial Rejection Rate]",
                        ),
                    ),
                ),
                "Sort by Uncalibrated Rate, descending. Add data bars to Uncalibrated Rate.",
            ),
        ),
    ),
    Page(
        "Findings",
        "Three effects planted in the synthetic data, shown the way a real report would show them.",
        (
            Visual(
                "textbox",
                "Synthetic data",
                16,
                12,
                1248,
                44,
                (),
                "One line, 12 pt: 'Synthetic data with effects planted on purpose. This page shows the report, not scientific evidence.'",
            ),
            Visual(
                "clusteredColumn",
                "Force variability with and without feedback",
                16,
                64,
                620,
                300,
                (("X-axis", ("Trial[Feedback]",)), ("Y-axis", ("[Mean Force CV]",)), ("Legend", ("Session[Group]",))),
                "Filter the visual to Trial[Feedback] On and Off (not blank). Data labels on, 2 decimals. Lower is steadier.",
            ),
            Visual(
                "clusteredColumn",
                "EMG frequency, before and after fatigue",
                644,
                64,
                300,
                300,
                (("X-axis", ("Trial[Fatigue Phase]",)), ("Y-axis", ("[Mean MDF]",))),
                "Filter the visual to Fatigue Phase Pre and Post (not blank). Data labels on.",
            ),
            Visual(
                "clusteredColumn",
                "EMG amplitude, before and after fatigue",
                952,
                64,
                312,
                300,
                (("X-axis", ("Trial[Fatigue Phase]",)), ("Y-axis", ("[Mean RMS]",))),
                "Same filter as the visual to its left. Data labels on.",
            ),
            Visual(
                "clusteredColumn",
                "EEG alpha power by stimulus size",
                16,
                372,
                620,
                332,
                (("X-axis", ("Trial[Stimulus Size]",)), ("Y-axis", ("[Mean Alpha Power]",))),
                "Filter the visual to Stimulus Size Small and Large (not blank). Data labels on.",
            ),
            Visual(
                "table",
                "Force variability: feedback effect by group",
                644,
                372,
                620,
                180,
                (
                    (
                        "Columns",
                        ("Session[Group]", "[Mean Force CV Feedback On]", "[Mean Force CV Feedback Off]", "[Feedback Effect on Force CV]"),
                    ),
                ),
                "Filter the visual to Study FFB-01 (filter pane, not a slicer). Two rows: control and intervention.",
            ),
            *_cards(("MDF Change After Fatigue", "Alpha Change Large vs Small Stimulus"), 560, 144, x0=644, total=620),
        ),
    ),
)


def page_by_name(name: str) -> Page:
    return next(p for p in PAGES if p.name == name)
