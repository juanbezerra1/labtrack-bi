# The data

Eight CSV files, **all synthetic**: no person, no device and no recording of this lab is real. They are the export of
the `medium` size of [labtrack-db](https://github.com/juanbezerra1/labtrack-db) (version 0.1.0, migrations 0001 to 0013),
taken as they are, with the seed's default "today" of 2026-10-31:

```bash
labtrack migrate
labtrack seed --scale medium
labtrack export --out data
```

The generator is deterministic, so the same commands give the same bytes on any machine.

| File | Rows | Columns | What a row is | Table of the model |
|---|---:|---:|---|---|
| `dim_date.csv` | 2,192 | 10 | a calendar day, 2023-01-01 to 2028-12-31 | `Calendar` |
| `dim_study.csv` | 3 | 7 | a study | `Study` |
| `dim_participant.csv` | 200 | 8 | a participant | `Participant` |
| `dim_researcher.csv` | 12 | 5 | a researcher | `Researcher` |
| `dim_device.csv` | 24 | 7 | a device | `Device` |
| `fact_session.csv` | 909 | 13 | a session | `Session` |
| `fact_recording.csv` | 1,634 | 13 | a recording | `Recording` |
| `fact_trial.csv` | 45,806 | 17 | a trial | `Trial` |

The model does not import every column. `fact_session.csv` loses `n_recordings` and `hours_recorded`; `fact_recording.csv`
loses `date_key`, `n_trials` and `n_valid_trials`; `fact_trial.csv` loses `session_key`, `date_key` and `modality`. Each of
them can be worked out from the other tables, and keeping them would give two answers to one question (a count that is
a column, and the same count that is a measure). The columns that are kept, with their new names and types, are in
[`docs/model.md`](../docs/model.md).

## Format

* UTF-8, `LF` line endings, a comma between the values, a header in the first line.
* `true` and `false` for booleans, an empty cell for `NULL`, dates as `2026-10-31`, times as `2026-10-31 08:10:00`
  (local time of the lab, without a time zone).
* Decimal point, never a comma; no thousands separator. The Power Query of the model asks for the culture `en-US`, so a
  Brazilian Windows reads them right.
* Codes are in lower case with underscores (`no_show`, `electrode_noise`); the model turns them into labels
  (`No Show`).

## Checking the files

`SHA256SUMS` has the checksum of every file, in the format that `sha256sum -c` reads:

```bash
cd data
sha256sum -c SHA256SUMS
```

In PowerShell, `Get-FileHash -Algorithm SHA256 fact_trial.csv` prints the same hash as the line of that file. A test
(`tests/test_data.py`) checks the checksums, the headers, the row counts, the line endings and the keys (none repeated,
none empty, every foreign key has its row), and counts the headline numbers again straight from the files, so a file
that was edited by hand, or saved by Excel, is found.

Do not open and save these files in Excel: it may change the dates, the line endings and the empty cells, and the
checksums will no longer match.
