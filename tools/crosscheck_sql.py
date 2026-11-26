"""Every number of docs/expected-numbers (made by src/labtrack_bi/engine.py from the CSV files) against SQL on the
database that the CSV files were exported from. The SQL below is written from the definitions of the measures, not from
engine.py, so the two routes only agree if both read the definitions the same way.

It needs a PostgreSQL with labtrack-db (version 0.1.0, migrations 0001 to 0013) seeded with `--scale medium`, and psycopg:

    labtrack migrate && labtrack seed --scale medium           # in the labtrack-db repository
    py -m pip install "psycopg[binary]"
    py tools/crosscheck_sql.py --dsn "host=localhost user=postgres password=postgres dbname=labtrack"

It prints one line per table of expected numbers and exits with 1 if any number differs. It is not part of the tests
(they cannot assume a database); `docs/verification.md` says what it found.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from datetime import date
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from labtrack_bi import expected  # noqa: E402

SESSION = (
    "bi.fact_session s JOIN bi.dim_study st ON st.study_key = s.study_key "
    "JOIN bi.dim_participant p ON p.participant_key = s.participant_key"
)
RECORDING = (
    "bi.fact_recording r JOIN bi.fact_session s ON s.session_key = r.session_key "
    "JOIN bi.dim_study st ON st.study_key = s.study_key JOIN bi.dim_device d ON d.device_key = r.device_key"
)
TRIAL = (
    "bi.fact_trial t JOIN bi.fact_recording r ON r.recording_key = t.recording_key "
    "JOIN bi.fact_session s ON s.session_key = r.session_key JOIN bi.dim_study st ON st.study_key = s.study_key "
    "JOIN bi.dim_device d ON d.device_key = r.device_key"
)

AGG = {
    "session": {
        "sessions": "count(*)",
        "enrolled": "count(DISTINCT s.participant_key)",
        "attended": "count(DISTINCT s.participant_key) FILTER (WHERE s.status = 'completed')",
        "completed": "count(*) FILTER (WHERE s.status = 'completed')",
        "cancelled": "count(*) FILTER (WHERE s.status = 'cancelled')",
        "no_show": "count(*) FILTER (WHERE s.status = 'no_show')",
        "scheduled": "count(*) FILTER (WHERE s.status = 'scheduled')",
        "avg_minutes": "avg(s.duration_min) FILTER (WHERE s.status = 'completed')",
        "withdrawn": "count(DISTINCT s.participant_key) FILTER (WHERE p.is_withdrawn)",
    },
    "recording": {
        "recordings": "count(*)",
        "seconds": "sum(r.duration_s)",
        "mb": "sum(r.size_mb)",
        "devices": "count(DISTINCT r.device_key)",
        "passed": "count(*) FILTER (WHERE r.qc = 'passed')",
        "pending": "count(*) FILTER (WHERE r.qc = 'pending')",
        "uncal": "count(*) FILTER (WHERE NOT r.device_calibrated)",
    },
    "trial": {
        "trials": "count(*)",
        "valid": "count(*) FILTER (WHERE t.valid)",
        "rejected": "count(*) FILTER (WHERE NOT t.valid)",
        "cv": "avg(t.force_cv_pct) FILTER (WHERE t.valid)",
        "cv_on": "avg(t.force_cv_pct) FILTER (WHERE t.valid AND t.condition LIKE '%\\_fb')",
        "cv_off": "avg(t.force_cv_pct) FILTER (WHERE t.valid AND t.condition LIKE '%\\_nofb')",
        "mdf": "avg(t.mdf_hz) FILTER (WHERE t.valid)",
        "rms": "avg(t.rms_mean_uv) FILTER (WHERE t.valid)",
        "alpha": "avg(t.alpha_power_uv2) FILTER (WHERE t.valid)",
        "mdf_post": "avg(t.mdf_hz) FILTER (WHERE t.valid AND t.condition = 'fatigue_post')",
        "mdf_pre": "avg(t.mdf_hz) FILTER (WHERE t.valid AND t.condition = 'fatigue_pre')",
        "rms_post": "avg(t.rms_mean_uv) FILTER (WHERE t.valid AND t.condition = 'fatigue_post')",
        "rms_pre": "avg(t.rms_mean_uv) FILTER (WHERE t.valid AND t.condition = 'fatigue_pre')",
        "alpha_large": "avg(t.alpha_power_uv2) FILTER (WHERE t.valid AND t.condition = 'stimulus_large')",
        "alpha_small": "avg(t.alpha_power_uv2) FILTER (WHERE t.valid AND t.condition = 'stimulus_small')",
    },
}
FROM = {"session": SESSION, "recording": RECORDING, "trial": TRIAL}


def num(x):
    return None if x is None else float(x)


def div(a, b):
    return None if a is None or not b else a / b


def sub(a, b):
    return None if a is None and b is None else (a or 0) - (b or 0)


def zero_none(n):
    return n or None


def label(text):
    if text is None:
        return None
    return " ".join(w[:1].upper() + w[1:].lower() for w in text.replace("_", " ").split(" "))


def run(cur, grain, groups, where="TRUE"):
    cols = ", ".join(f"{g} AS g{i}" for i, g in enumerate(groups))
    aggs = ", ".join(f"{sql} AS {name}" for name, sql in AGG[grain].items())
    group_by = f"GROUP BY {', '.join(str(i + 1) for i in range(len(groups)))}" if groups else ""
    cur.execute(f"SELECT {cols + ', ' if groups else ''}{aggs} FROM {FROM[grain]} WHERE {where} {group_by}")
    names = [d.name for d in cur.description]
    out = {}
    for row in cur.fetchall():
        rec = dict(zip(names, row, strict=True))
        key = tuple(rec[f"g{i}"] for i in range(len(groups)))
        out[key] = {k: num(v) for k, v in rec.items() if not k.startswith("g")}
    return out


def measures_from(a):
    """The measures, from the aggregates of a group (a is a merged dict)."""
    g = a.get
    closed = sub(zero_none(int(g("sessions") or 0)), zero_none(int(g("scheduled") or 0)))
    m = {
        "Sessions": zero_none(int(g("sessions") or 0)) if "sessions" in a else None,
        "Participants Enrolled": zero_none(int(g("enrolled") or 0)),
        "Participants Attended": zero_none(int(g("attended") or 0)),
        "Recordings": zero_none(int(g("recordings") or 0)),
        "Trials": zero_none(int(g("trials") or 0)),
        "Hours Recorded": div(g("seconds"), 3600),
        "Data Volume GB": div(g("mb"), 1024),
        "Devices Used": zero_none(int(g("devices") or 0)),
        "Sessions Completed": zero_none(int(g("completed") or 0)),
        "Sessions Cancelled": zero_none(int(g("cancelled") or 0)),
        "Sessions No Show": zero_none(int(g("no_show") or 0)),
        "Sessions Scheduled": zero_none(int(g("scheduled") or 0)),
        "Sessions Closed": closed,
        "Avg Session Minutes": g("avg_minutes"),
        "Participants Withdrawn": zero_none(int(g("withdrawn") or 0)),
        "Recordings Passed QC": zero_none(int(g("passed") or 0)),
        "Uncalibrated Recordings": zero_none(int(g("uncal") or 0)),
        "Valid Trials": zero_none(int(g("valid") or 0)),
        "Rejected Trials": zero_none(int(g("rejected") or 0)),
        "Mean Force CV": g("cv"),
        "Mean Force CV Feedback On": g("cv_on"),
        "Mean Force CV Feedback Off": g("cv_off"),
        "Mean MDF": g("mdf"),
        "Mean RMS": g("rms"),
        "Mean Alpha Power": g("alpha"),
        "Target N": g("target"),
    }
    m["Completion Rate"] = div(m["Sessions Completed"], closed)
    m["No Show Rate"] = div(m["Sessions No Show"], closed)
    m["Cancellation Rate"] = div(m["Sessions Cancelled"], closed)
    m["Recruitment Progress"] = div(m["Participants Attended"], m["Target N"])
    m["Withdrawal Rate"] = div(m["Participants Withdrawn"], m["Participants Enrolled"])
    m["QC Pass Rate"] = div(m["Recordings Passed QC"], sub(m["Recordings"], zero_none(int(g("pending") or 0))))
    m["Uncalibrated Rate"] = div(m["Uncalibrated Recordings"], m["Recordings"])
    m["Trial Rejection Rate"] = div(m["Rejected Trials"], m["Trials"])
    m["Avg Trials per Recording"] = div(m["Trials"], m["Recordings"])
    m["Feedback Effect on Force CV"] = sub(m["Mean Force CV Feedback On"], m["Mean Force CV Feedback Off"])
    m["MDF Change After Fatigue"] = sub(g("mdf_post"), g("mdf_pre"))
    m["RMS Change After Fatigue"] = sub(g("rms_post"), g("rms_pre"))
    m["Alpha Change Large vs Small Stimulus"] = sub(g("alpha_large"), g("alpha_small"))
    return m


def merged(cur, groups_by_grain, where_by_grain=None):
    """{group key: aggregates of all three grains merged}; groups_by_grain: grain -> list of SQL group expressions
    (None = the grain does not take part in this check)."""
    result: dict[tuple, dict] = {}
    for grain, groups in groups_by_grain.items():
        if groups is None:
            continue
        where = (where_by_grain or {}).get(grain, "TRUE")
        for key, agg in run(cur, grain, groups, where).items():
            result.setdefault(key, {}).update(agg)
    return result


def compare(check, sql_groups, label_fn, extra=None, skip=()):
    engine_rows = expected.rows_of(check, ENGINE_BASE)
    names = check.measures
    ng = len(check.groups)
    engine = {tuple(r[:ng]): r[ng:] for r in engine_rows}
    sql = {}
    for key, agg in sql_groups.items():
        m = measures_from({**agg, **(extra(key) if extra else {})})
        k = label_fn(key)
        vals = [m.get(n, "MISSING") if n not in skip else None for n in names]
        if any(v == "MISSING" for v in vals):
            raise SystemExit(
                f"{check.id}: the SQL side has no formula for {[n for n, v in zip(names, vals, strict=True) if v == 'MISSING']}"
            )
        if any(v is not None for v in vals):
            sql[k] = vals
    bad = 0
    for k in sorted(set(engine) | set(sql), key=lambda x: tuple("" if v is None else str(v) for v in x)):
        a, b = engine.get(k), sql.get(k)
        if a is None or b is None:
            print(f"  {check.id} {k}: only on one side: engine={a} sql={b}")
            bad += 1
            continue
        for n, x, y in zip(names, a, b, strict=True):
            if n in skip:
                continue
            same = (x is None and y is None) or (
                x is not None and y is not None and math.isclose(float(x), float(y), rel_tol=1e-9, abs_tol=1e-9)
            )
            if not same:
                print(f"  {check.id} {k} {n}: engine={x} sql={y}")
                bad += 1
    print(f"{'OK  ' if not bad else 'FAIL'} {check.id}: {len(engine)} rows, {len(names)} measures")
    return bad


def main(argv: list[str] | None = None) -> int:
    global ENGINE_BASE
    parser = argparse.ArgumentParser(description="Compares docs/expected-numbers with SQL on the database the CSV files came from.")
    parser.add_argument(
        "--dsn", default=os.environ.get("LABTRACK_DSN"), help="the connection string of the labtrack-db database (or set LABTRACK_DSN)"
    )
    args = parser.parse_args(argv)
    if not args.dsn:
        parser.error("give --dsn or set LABTRACK_DSN")
    dsn = args.dsn
    from labtrack_bi import data as datamod
    from labtrack_bi import engine

    ENGINE_BASE = engine.whole(datamod.load(ROOT / "data"))
    bad = 0
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT study_code, sum(target_n) FROM bi.dim_study GROUP BY 1")
        targets = {k: float(v) for k, v in cur.fetchall()}
        cur.execute("SELECT sum(target_n) FROM bi.dim_study")
        total_target = float(cur.fetchone()[0])

        # overall
        c = expected.check_by_id("overall")
        agg = merged(cur, {"session": [], "recording": [], "trial": []})
        # running totals / last date at the end of everything
        cur.execute("SELECT count(*), count(DISTINCT participant_key), max(date_key) FROM bi.fact_session WHERE status = 'completed'")
        n_done, n_att, last = cur.fetchone()
        base = measures_from({**agg[()], "target": total_target})
        base["Last Completed Session Date"] = last
        base["Visit Retention"] = None
        base["Completed Sessions Running Total"] = n_done
        base["Participants Attended Running Total"] = n_att
        engine_row = dict(zip(c.measures, expected.rows_of(c, ENGINE_BASE)[0], strict=True))
        for n in c.measures:
            x, y = engine_row[n], base.get(n, "MISSING")
            if y == "MISSING":
                print("  overall: SQL side lacks", n)
                bad += 1
                continue
            if isinstance(x, date) or isinstance(y, date):
                same = x == y
            else:
                same = (x is None and y is None) or (
                    x is not None and y is not None and math.isclose(float(x), float(y), rel_tol=1e-9, abs_tol=1e-9)
                )
            if not same:
                print(f"  overall {n}: engine={x} sql={y}")
                bad += 1
        print(f"{'OK  ' if not bad else 'FAIL'} overall: {len(c.measures)} measures")

        # by study
        study = {"session": ["st.study_code"], "recording": ["st.study_code"], "trial": ["st.study_code"]}
        bad += compare(expected.check_by_id("by_study"), merged(cur, study), lambda k: k, lambda k: {"target": targets[k[0]]})

        # by year (time intelligence) from the session grain
        yr = run(cur, "session", ["extract(year FROM s.date_key)::int"])
        years = {k[0]: v for k, v in yr.items()}

        def year_measures(y):
            cur_n = years.get(y, {}).get("sessions")
            prev = years.get(y - 1, {}).get("sessions")
            return {
                "Sessions": cur_n,
                "Sessions Completed": years.get(y, {}).get("completed"),
                "Sessions YTD": cur_n,
                "Sessions Previous Year": prev,
                "Sessions YoY": div(sub(cur_n, prev), prev),
            }

        c = expected.check_by_id("by_year")
        eng = {r[0]: r[1:] for r in expected.rows_of(c, ENGINE_BASE)}
        n_bad = 0
        for y in range(2023, 2029):
            vals = [year_measures(y)[m] for m in c.measures]
            vals = [
                zero_none(int(v))
                if isinstance(v, float) and m in ("Sessions", "Sessions Completed", "Sessions YTD", "Sessions Previous Year")
                else v
                for m, v in zip(c.measures, vals, strict=True)
            ]
            sql_row = vals if any(v is not None for v in vals) else None
            e = eng.get(y)
            if (e is None) != (sql_row is None):
                print("  by_year", y, "only one side", e, sql_row)
                n_bad += 1
                continue
            if e is None:
                continue
            for m, x, v in zip(c.measures, e, sql_row, strict=True):
                if not ((x is None and v is None) or (x is not None and v is not None and math.isclose(float(x), float(v), rel_tol=1e-9))):
                    print("  by_year", y, m, x, v)
                    n_bad += 1
        print(f"{'OK  ' if not n_bad else 'FAIL'} by_year")
        bad += n_bad

        # by month: running totals computed with window functions over the month ends
        c = expected.check_by_id("by_month")
        cur.execute("""
            WITH months AS (
              SELECT to_char(m, 'YYYY-MM') AS ym, (m + interval '1 month' - interval '1 day')::date AS last_day, m::date AS first_day
              FROM generate_series('2023-01-01'::date, '2028-12-01'::date, interval '1 month') AS m)
            SELECT ym,
                   (SELECT count(*) FROM bi.fact_session s WHERE s.status = 'completed' AND s.date_key BETWEEN first_day AND last_day) AS completed,
                   (SELECT count(*) FROM bi.fact_session s WHERE s.status = 'completed' AND s.date_key <= last_day) AS running,
                   (SELECT count(DISTINCT participant_key) FROM bi.fact_session s WHERE s.status = 'completed' AND s.date_key <= last_day) AS att_running,
                   (SELECT max(date_key) FROM bi.fact_session WHERE status = 'completed') AS last_completed,
                   first_day,
                   (SELECT count(*) FROM bi.fact_session s WHERE s.date_key BETWEEN make_date(extract(year FROM first_day)::int, 1, 1) AND last_day) AS ytd
            FROM months ORDER BY 1""")
        sql_month = {}
        for ym, completed, running, att_running, last_completed, first_day, ytd in cur.fetchall():
            blank_run = first_day > last_completed
            vals = [
                zero_none(completed),
                None if blank_run else zero_none(running),
                None if blank_run else zero_none(att_running),
                zero_none(ytd),
            ]
            if any(v is not None for v in vals):
                sql_month[ym] = vals
        eng = {r[0]: r[1:] for r in expected.rows_of(c, ENGINE_BASE)}
        n_bad = 0
        for k in sorted(set(eng) | set(sql_month)):
            if k not in eng or k not in sql_month:
                print("  by_month only one side", k, eng.get(k), sql_month.get(k))
                n_bad += 1
            elif list(eng[k]) != list(sql_month[k]):
                print("  by_month", k, eng[k], sql_month[k])
                n_bad += 1
        print(f"{'OK  ' if not n_bad else 'FAIL'} by_month: {len(eng)} months")
        bad += n_bad

        # by status / visit / age and sex (session grain)

        def sess(groups):
            return merged(cur, {"session": groups, "recording": None, "trial": None})

        bad += compare(expected.check_by_id("by_status"), sess(["s.status"]), lambda k: (label(k[0]),))
        bad += compare(expected.check_by_id("by_visit"), sess(["s.visit_no"]), lambda k: (k[0],), None, skip=("Visit Retention",))
        # retention: attended at visit v over attended at visit 1
        c = expected.check_by_id("by_visit")
        att = {k[0]: v["attended"] for k, v in sess(["s.visit_no"]).items()}
        for row in expected.rows_of(c, ENGINE_BASE):
            v, a, r = row
            want = att[v] / att[1]
            if not math.isclose(r, want, rel_tol=1e-9):
                print("  by_visit retention", v, r, want)
                bad += 1
        age = (
            "CASE WHEN extract(year FROM p.consent_signed_on) - p.birth_year < 30 THEN 'Under 30' "
            "WHEN extract(year FROM p.consent_signed_on) - p.birth_year < 45 THEN '30-44' "
            "WHEN extract(year FROM p.consent_signed_on) - p.birth_year < 60 THEN '45-59' ELSE '60+' END"
        )
        bad += compare(expected.check_by_id("by_age_sex"), sess([age, "p.sex"]), lambda k: k)

        # data quality

        def rec(groups):
            return merged(cur, {"session": None, "recording": groups, "trial": groups}, None)

        mod = {"emg": "EMG", "eeg": "EEG", "force": "Force"}
        bad += compare(expected.check_by_id("by_modality"), rec(["r.modality"]), lambda k: (mod[k[0]],))
        bad += compare(
            expected.check_by_id("by_qc"), merged(cur, {"session": None, "recording": ["r.qc"], "trial": None}), lambda k: (label(k[0]),)
        )
        bad += compare(
            expected.check_by_id("by_reason"),
            merged(cur, {"session": None, "recording": None, "trial": ["t.reject_reason"]}),
            lambda k: (label(k[0]),),
        )
        bad += compare(
            expected.check_by_id("by_device"), merged(cur, {"session": None, "recording": ["d.serial_no"], "trial": None}), lambda k: k
        )

        # findings
        c = expected.check_by_id("findings")
        agg = merged(cur, {"session": None, "recording": None, "trial": []})[()]
        base = measures_from(agg)
        engine_row = dict(zip(c.measures, expected.rows_of(c, ENGINE_BASE)[0], strict=True))
        for n in c.measures:
            if not math.isclose(engine_row[n], base[n], rel_tol=1e-9):
                print("  findings", n, engine_row[n], base[n])
                bad += 1
        print("OK   findings" if not bad else "FAIL findings (see above)")

        # feedback by group, study FFB-01
        c = expected.check_by_id("feedback_by_group")
        grp = merged(cur, {"session": None, "recording": None, "trial": ["s.group_label"]}, {"trial": "st.study_code = 'FFB-01'"})
        bad += compare(c, grp, lambda k: (label(k[0]),))
    print("TOTAL MISMATCHES:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
