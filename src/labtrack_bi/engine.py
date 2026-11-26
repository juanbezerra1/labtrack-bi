"""The measures of the model worked out in Python, with a small copy of the filter context of Power BI.

This is not a DAX engine. It is the same 46 measures written a second time, by hand, with sets: a filter on a column of a
table keeps the rows that match; the filter of a dimension reaches the fact tables through the relationships, one way
only (Study, Participant, Researcher and Calendar filter Session; Session and Device filter Recording; Recording filters
Trial); CALCULATE replaces the filter of the column it names; REMOVEFILTERS and FILTER(ALL(table)) clear a table. The
numbers it gives are the numbers that Power BI must show: docs/expected-numbers.md is made from them.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import date
from functools import cached_property
from typing import Any

from .data import Data, Row

Allowed = Iterable[Any]
Value = float | int | date | None


class Index:
    """The lookups that follow the relationships."""

    def __init__(self, data: Data) -> None:
        self.data = data
        self.study = {r["Study Key"]: r for r in data["Study"]}
        self.participant = {r["Participant Key"]: r for r in data["Participant"]}
        self.researcher = {r["Researcher Key"]: r for r in data["Researcher"]}
        self.device = {r["Device Key"]: r for r in data["Device"]}
        self.calendar = {r["Date"]: r for r in data["Calendar"]}
        self.session = {r["Session Key"]: r for r in data["Session"]}
        self.recording = {r["Recording Key"]: r for r in data["Recording"]}
        self.dates = sorted(self.calendar)


def _passes(row: Row, rules: Mapping[str, frozenset[Any]]) -> bool:
    return all(row[column] in allowed for column, allowed in rules.items())


class Ctx:
    """A filter context: {"Table.Column": allowed values}. `dates` replaces the filter of the Calendar when it is set."""

    def __init__(self, index: Index, filters: Mapping[str, frozenset[Any]] | None = None, dates: frozenset[date] | None = None) -> None:
        self.index = index
        self.filters: dict[str, frozenset[Any]] = dict(filters or {})
        self.dates = dates

    # --- CALCULATE and friends -------------------------------------------------------------------------------
    def calc_columns(self, filters: Mapping[str, Allowed]) -> Ctx:
        merged = dict(self.filters)
        for key, allowed in filters.items():
            merged[key] = frozenset(allowed)
        return Ctx(self.index, merged, self.dates)

    def remove_filters(self, table: str) -> Ctx:
        """REMOVEFILTERS(table)."""
        kept = {k: v for k, v in self.filters.items() if not k.startswith(table + ".")}
        return Ctx(self.index, kept, None if table == "Calendar" else self.dates)

    def with_dates(self, dates: Iterable[date]) -> Ctx:
        """CALCULATE(..., <a table of dates>) on a marked date table: the dates replace every filter of the Calendar."""
        kept = {k: v for k, v in self.filters.items() if not k.startswith("Calendar.")}
        return Ctx(self.index, kept, frozenset(dates))

    # --- the rows that pass -----------------------------------------------------------------------------------
    def _rules(self, table: str) -> dict[str, frozenset[Any]]:
        prefix = table + "."
        return {k[len(prefix) :]: v for k, v in self.filters.items() if k.startswith(prefix)}

    @cached_property
    def calendar_dates(self) -> frozenset[date]:
        if self.dates is not None:
            return self.dates
        rules = self._rules("Calendar")
        return frozenset(d for d, row in self.index.calendar.items() if _passes(row, rules))

    @cached_property
    def studies(self) -> list[Row]:
        rules = self._rules("Study")
        return [r for r in self.index.data["Study"] if _passes(r, rules)]

    @cached_property
    def sessions(self) -> list[Row]:
        ix = self.index
        study = {r["Study Key"] for r in self.studies}
        participants = _keys(ix.data["Participant"], "Participant Key", self._rules("Participant"))
        researchers = _keys(ix.data["Researcher"], "Researcher Key", self._rules("Researcher"))
        own = self._rules("Session")
        dates = self.calendar_dates
        return [
            r
            for r in ix.data["Session"]
            if r["Study Key"] in study
            and r["Participant Key"] in participants
            and r["Researcher Key"] in researchers
            and r["Session Date"] in dates
            and _passes(r, own)
        ]

    @cached_property
    def recordings(self) -> list[Row]:
        session_keys = {r["Session Key"] for r in self.sessions}
        devices = _keys(self.index.data["Device"], "Device Key", self._rules("Device"))
        own = self._rules("Recording")
        return [
            r for r in self.index.data["Recording"] if r["Session Key"] in session_keys and r["Device Key"] in devices and _passes(r, own)
        ]

    @cached_property
    def trials(self) -> list[Row]:
        recording_keys = {r["Recording Key"] for r in self.recordings}
        own = self._rules("Trial")
        return [r for r in self.index.data["Trial"] if r["Recording Key"] in recording_keys and _passes(r, own)]


def _keys(rows: list[Row], key: str, rules: Mapping[str, frozenset[Any]]) -> set[Any]:
    return {r[key] for r in rows if _passes(r, rules)}


# ---------------------------------------------------------------------------------------------------------------
# DAX arithmetic: BLANK is None; a missing term counts as zero in + and -, and DIVIDE gives BLANK for a zero or blank
# denominator or a blank numerator.
# ---------------------------------------------------------------------------------------------------------------
def count(n: int) -> int | None:
    """COUNTROWS and DISTINCTCOUNT give BLANK, not 0, when there is nothing to count."""
    return n or None


def total(values: list[float]) -> float | None:
    return sum(values) if values else None


def average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def sub(a: float | None, b: float | None) -> float | None:
    return None if a is None and b is None else (a or 0) - (b or 0)


def divide(a: float | None, b: float | None) -> float | None:
    return None if a is None or not b else a / b


def _num(values: Iterable[Any]) -> list[float]:
    return [v for v in values if v is not None]


# ---------------------------------------------------------------------------------------------------------------
# the measures, in the order of the model
# ---------------------------------------------------------------------------------------------------------------
Measure = Callable[[Ctx], Any]
M: dict[str, Measure] = {}


def measure(name: str) -> Callable[[Measure], Measure]:
    def register(fn: Measure) -> Measure:
        M[name] = fn
        return fn

    return register


def status(c: Ctx, label: str) -> Ctx:
    return c.calc_columns({"Session.Status": [label]})


@measure("Sessions")
def _sessions(c: Ctx) -> Any:
    return count(len(c.sessions))


@measure("Participants Enrolled")
def _enrolled(c: Ctx) -> Any:
    return count(len({r["Participant Key"] for r in c.sessions}))


@measure("Participants Attended")
def _attended(c: Ctx) -> Any:
    return _enrolled(status(c, "Completed"))


@measure("Recordings")
def _recordings(c: Ctx) -> Any:
    return count(len(c.recordings))


@measure("Trials")
def _trials(c: Ctx) -> Any:
    return count(len(c.trials))


@measure("Hours Recorded")
def _hours(c: Ctx) -> Any:
    return divide(total(_num(r["Duration Seconds"] for r in c.recordings)), 3600)


@measure("Data Volume GB")
def _volume(c: Ctx) -> Any:
    return divide(total(_num(r["Size MB"] for r in c.recordings)), 1024)


@measure("Devices Used")
def _devices(c: Ctx) -> Any:
    return count(len({r["Device Key"] for r in c.recordings}))


@measure("Sessions Completed")
def _completed(c: Ctx) -> Any:
    return _sessions(status(c, "Completed"))


@measure("Sessions Cancelled")
def _cancelled(c: Ctx) -> Any:
    return _sessions(status(c, "Cancelled"))


@measure("Sessions No Show")
def _no_show(c: Ctx) -> Any:
    return _sessions(status(c, "No Show"))


@measure("Sessions Scheduled")
def _scheduled(c: Ctx) -> Any:
    return _sessions(status(c, "Scheduled"))


@measure("Sessions Closed")
def _closed(c: Ctx) -> Any:
    return sub(_sessions(c), _scheduled(c))


@measure("Completion Rate")
def _completion(c: Ctx) -> Any:
    return divide(_completed(c), _closed(c))


@measure("No Show Rate")
def _no_show_rate(c: Ctx) -> Any:
    return divide(_no_show(c), _closed(c))


@measure("Cancellation Rate")
def _cancellation(c: Ctx) -> Any:
    return divide(_cancelled(c), _closed(c))


@measure("Avg Session Minutes")
def _avg_minutes(c: Ctx) -> Any:
    return average(_num(r["Duration Minutes"] for r in status(c, "Completed").sessions))


@measure("Last Completed Session Date")
def _last_completed(c: Ctx) -> Any:
    days = [r["Session Date"] for r in status(c, "Completed").sessions]
    return max(days) if days else None


@measure("Sessions YTD")
def _ytd(c: Ctx) -> Any:
    """TOTALYTD: from 1 January of the year of the last date in the context up to that date."""
    if not c.calendar_dates:
        return None
    last = max(c.calendar_dates)
    return _sessions(c.with_dates(d for d in c.index.dates if d.year == last.year and d <= last))


def _same_period_last_year(c: Ctx) -> list[date]:
    shifted = []
    for d in c.calendar_dates:
        try:
            shifted.append(d.replace(year=d.year - 1))
        except ValueError:  # 29 February -> 28 February
            shifted.append(d.replace(year=d.year - 1, day=28))
    return [d for d in shifted if d in c.index.calendar]


@measure("Sessions Previous Year")
def _previous_year(c: Ctx) -> Any:
    return _sessions(c.with_dates(_same_period_last_year(c)))


@measure("Sessions YoY")
def _yoy(c: Ctx) -> Any:
    previous = _previous_year(c)
    return divide(sub(_sessions(c), previous), previous)


def _running(c: Ctx, inner: Measure) -> Any:
    """VAR LastDay = ... REMOVEFILTERS(Calendar); IF(MIN(date) <= LastDay, CALCULATE(inner, FILTER(ALL(Calendar), date <= MAX(date))))."""
    if not c.calendar_dates:
        return None
    last_day = _last_completed(c.remove_filters("Calendar"))
    if last_day is None or min(c.calendar_dates) > last_day:
        return None
    this_day = max(c.calendar_dates)
    return inner(c.with_dates(d for d in c.index.dates if d <= this_day))


@measure("Completed Sessions Running Total")
def _running_sessions(c: Ctx) -> Any:
    return _running(c, _completed)


@measure("Participants Attended Running Total")
def _running_participants(c: Ctx) -> Any:
    return _running(c, _attended)


@measure("Target N")
def _target(c: Ctx) -> Any:
    return total(_num(r["Target N"] for r in c.studies))


@measure("Recruitment Progress")
def _progress(c: Ctx) -> Any:
    return divide(_attended(c), _target(c))


@measure("Participants Withdrawn")
def _withdrawn(c: Ctx) -> Any:
    return _enrolled(c.calc_columns({"Participant.Is Withdrawn": [True]}))


@measure("Withdrawal Rate")
def _withdrawal(c: Ctx) -> Any:
    return divide(_withdrawn(c), _enrolled(c))


@measure("Visit Retention")
def _retention(c: Ctx) -> Any:
    if len({r["Visit No"] for r in c.sessions}) != 1:  # HASONEVALUE(Session[Visit No])
        return None
    return divide(_attended(c), _attended(c.calc_columns({"Session.Visit No": [1]})))


def qc(c: Ctx, label: str) -> Ctx:
    return c.calc_columns({"Recording.QC": [label]})


@measure("Recordings Passed QC")
def _passed(c: Ctx) -> Any:
    return _recordings(qc(c, "Passed"))


@measure("QC Pass Rate")
def _pass_rate(c: Ctx) -> Any:
    return divide(_passed(c), sub(_recordings(c), _recordings(qc(c, "Pending"))))


@measure("Uncalibrated Recordings")
def _uncalibrated(c: Ctx) -> Any:
    return _recordings(c.calc_columns({"Recording.Device Calibrated": [False]}))


@measure("Uncalibrated Rate")
def _uncalibrated_rate(c: Ctx) -> Any:
    return divide(_uncalibrated(c), _recordings(c))


@measure("Valid Trials")
def _valid(c: Ctx) -> Any:
    return _trials(c.calc_columns({"Trial.Valid": [True]}))


@measure("Rejected Trials")
def _rejected(c: Ctx) -> Any:
    return _trials(c.calc_columns({"Trial.Valid": [False]}))


@measure("Trial Rejection Rate")
def _rejection(c: Ctx) -> Any:
    return divide(_rejected(c), _trials(c))


@measure("Avg Trials per Recording")
def _trials_per_recording(c: Ctx) -> Any:
    return divide(_trials(c), _recordings(c))


def valid_trials(c: Ctx) -> Ctx:
    return c.calc_columns({"Trial.Valid": [True]})


@measure("Mean Force CV")
def _mean_cv(c: Ctx) -> Any:
    return average(_num(r["Force CV"] for r in valid_trials(c).trials))


def feedback(c: Ctx, label: str) -> Ctx:
    return c.calc_columns({"Trial.Feedback": [label]})


@measure("Mean Force CV Feedback On")
def _cv_on(c: Ctx) -> Any:
    return _mean_cv(feedback(c, "On"))


@measure("Mean Force CV Feedback Off")
def _cv_off(c: Ctx) -> Any:
    return _mean_cv(feedback(c, "Off"))


@measure("Feedback Effect on Force CV")
def _effect(c: Ctx) -> Any:
    return sub(_cv_on(c), _cv_off(c))


@measure("Mean MDF")
def _mean_mdf(c: Ctx) -> Any:
    return average(_num(r["MDF"] for r in valid_trials(c).trials))


@measure("Mean RMS")
def _mean_rms(c: Ctx) -> Any:
    return average(_num(r["RMS"] for r in valid_trials(c).trials))


@measure("Mean Alpha Power")
def _mean_alpha(c: Ctx) -> Any:
    return average(_num(r["Alpha Power"] for r in valid_trials(c).trials))


def phase(c: Ctx, label: str) -> Ctx:
    return c.calc_columns({"Trial.Fatigue Phase": [label]})


@measure("MDF Change After Fatigue")
def _mdf_change(c: Ctx) -> Any:
    return sub(_mean_mdf(phase(c, "Post")), _mean_mdf(phase(c, "Pre")))


@measure("RMS Change After Fatigue")
def _rms_change(c: Ctx) -> Any:
    return sub(_mean_rms(phase(c, "Post")), _mean_rms(phase(c, "Pre")))


@measure("Alpha Change Large vs Small Stimulus")
def _alpha_change(c: Ctx) -> Any:
    def size(label: str) -> Any:
        return _mean_alpha(c.calc_columns({"Trial.Stimulus Size": [label]}))

    return sub(size("Large"), size("Small"))


def evaluate(c: Ctx, names: Iterable[str]) -> dict[str, Any]:
    return {name: M[name](c) for name in names}


def whole(data: Data) -> Ctx:
    return Ctx(Index(data))


__all__ = ["Ctx", "Index", "M", "evaluate", "whole"]
