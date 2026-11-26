# Verification

What was checked, how, with what result, and what could **not** be checked. The results are those of version 0.1.0.
Every command in this file can be run again (the one exception is marked); on Linux and macOS write `python3` where this
file writes `py`.

## In one table

| What | How | Result |
|---|---|---|
| The expected numbers (13 tables, every measure) | two independent routes: [`src/labtrack_bi/engine.py`](../src/labtrack_bi/engine.py), a hand-written second version of the 46 measures that reads the CSV files, against SQL written from the definitions of the measures and run on the database that the files came from ([`tools/crosscheck_sql.py`](../tools/crosscheck_sql.py)) | 0 differences |
| Every generated file | `py -m labtrack_bi check`, and the tests, compare each one byte by byte with what the specification produces | up to date |
| The tests | `py -m pytest` | 289 passed on Python 3.10, 3.12 and 3.13 (Linux), with the schema tests switched on; without the clone of the schemas, 285 passed and 4 were skipped |
| The Power Query (nine queries) | the parser and the language services that Microsoft publishes for Visual Studio Code ([`tools/`](../tools/README.md)), and a smaller linter in Python that runs with the tests | 0 queries with problems |
| The JSON files of the report | Microsoft's published schemas ([json-schemas](https://github.com/microsoft/json-schemas)) | the 7 files that carry a `$schema` are valid; see "Three small files" below for the others |
| The colours of the theme | a palette validator (lightness band, chroma, distance between neighbours for colour-blind readers, contrast), light mode, surface `#fcfcfb`; I ran it once with the `dataviz` skill of Claude, so it is **not** in this repository and you cannot repeat it from here | passes every check; one contrast **warning**, kept on purpose (see [design.md](design.md#colours)) |
| Style and types | `ruff check`, `ruff format --check`, `mypy` in strict mode on `src` | clean |
| A checkout with Windows line endings | a clone with `core.autocrlf=true`, then the tests and `check` | 289 passed, `ok` |
| The wheel | `py -m build --wheel`, installed in a clean environment | installs, `--version` runs, the resource files are inside |
| The zip of the repository | extracted names and path lengths checked for what Windows refuses (reserved names, characters, case collisions, long paths) and every text file checked for LF | no problem |

## The numbers, worked out twice

`docs/expected-numbers.md` says what Power BI must show. Two routes lead to it, and they share nothing but the data:

1. **The engine.** `engine.py` is a plain Python version of each of the 46 measures, written from the definitions in
   [model.md](model.md) and the notes in [design.md](design.md#the-measures), reading the eight CSV files. It makes the
   expected numbers and the check queries of `model/check.dax` are written to match them.
2. **SQL.** `tools/crosscheck_sql.py` asks PostgreSQL the same thing: one query per grain (session, recording, trial),
   grouped the way each check query groups, written from the definitions of the measures and **not** from the engine.
   The database is labtrack-db at version 0.1.0 with the `medium` seed, the one that the CSV files were exported from.

All 13 tables agree, to the last digit that the tests compare (relative difference below 1e-9). That says that the
engine and the SQL read the definitions the same way and that the CSV files are the export of that database. It does
**not** say that Power BI will show the same: DAX has its own rules for filters and blanks, and no DAX engine ran here.
That is what Phase A of the [build guide](build-guide.md) is for, and the first thing it asks is to run the 13 queries.

```console
py -m pip install "psycopg[binary]"
py tools/crosscheck_sql.py --dsn "host=localhost user=postgres password=postgres dbname=labtrack"
```

(`labtrack migrate` and `labtrack seed --scale medium`, in the labtrack-db repository, make that database.)

## What the tests cover

`py -m pytest` runs 289 tests (4 of them need the clone of the schemas, see the end of this file), in a few seconds and
without Power BI, a database or a network:

* **The data**: checksums, row counts, every header accounted for, UTF-8 and LF, unique keys, every foreign key with its
  row, and a recount from the CSV files of the numbers that the story of the data depends on.
* **The measures**: every DAX measure and every check query goes through a linter (balanced delimiters, known
  functions, measures that exist, no cycle), has a description and a format string, and appears in `measures.dax`.
* **The model**: the TMDL files parse back into the tables, columns, sort columns, partitions, relationships and
  measures of the specification, and `check-model` finds a difference, a changed query, a missing table.
* **The report**: the four pages, the theme, the small files, stable identifiers, and `check-report` (against a report
  written the way Desktop writes one, made from the specification) finds a missing visual, a wrong field, a wrong
  type, a moved visual. With the clone of the schemas, every JSON file that has a `$schema` is valid, and the three
  that have none break no rule of the schemas but that one.
* **The drawings**: well-formed SVG, no title cut, no visual outside the page or on top of another.
* **The documentation**: the numbers of the READMEs and of the guides are those of the specification and of the data
  (the tables, the counts in the prose, the numbers that the engine works out), the two languages have the same shape,
  every link, image and file name that a text mentions exists, every command that a document names exists with the
  options it uses, the commands to type are written with `py`, and `add-screenshots` fills both READMEs and can be run
  again.

## What could not be checked

* **Power BI Desktop never opened this project.** It only runs on Windows, and there is none here. The shape of every
  project file was copied from projects that Desktop itself saved ([pbi_file_formats](https://github.com/alisonpezzott/pbi_file_formats)),
  and the report and model files pass Microsoft's schemas, but "valid" is not "opened". If Desktop refuses the project,
  write down its version and the message ([build guide](build-guide.md#if-the-project-does-not-open)).
* **The Power Query was parsed, never run.** Only Power Query itself reads the CSV files. In particular I assumed that
  an empty CSV cell becomes `null`; the `Table.ReplaceValue` step makes the queries right either way, but the refresh
  is the test.
* **The DAX was never run by a DAX engine.** The 46 measures were linted and re-implemented, not executed. A difference
  between a number of `check.dax` and `expected-numbers.md` in Phase A is a bug of the model, or of my reading of DAX.
* **The wireframes are drawings made from the specification**, not screenshots of Power BI.
* **The workflow of the CI was not run on GitHub** when I wrote this. I ran each of its steps by hand: the tests on
  three Python versions, lint, format, types, the schema test, the check of the Power Query, the build of the wheel,
  and a clone with Windows line endings. The Windows runners are the one thing that I could only imitate.

### Three small files

The schemas of Microsoft list `$schema` as a required property of `labtrack.pbip`, of `labtrack.Report/definition.pbir`
and of `labtrack.SemanticModel/definition.pbism`. The generator leaves it out, because the sample projects that Power BI
Desktop saved have none in these three files ([`tests/test_pbir.py`](../tests/test_pbir.py)). A test shows that this
is the only thing the schemas object to: with the line added, each file is valid. If Desktop ever complains about one of
them, add the line, followed by a comma, as the first property:

| File | The line |
|---|---|
| `labtrack.pbip` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json"` |
| `labtrack.Report/definition.pbir` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json"` |
| `labtrack.SemanticModel/definition.pbism` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json"` |

The two `.platform` files carry a `$schema` whose definition (`gitIntegration/platformProperties/2.0.0`) is not in the
public clone of json-schemas, so they were not validated; they copy the shape of the sample projects.

## Run it again

```console
py -m pip install -e ".[dev]"
py -m pytest                                  # the tests
py -m ruff check .                            # style
py -m ruff format --check .
py -m mypy src                                # types
py -m labtrack_bi check                       # the generated files are up to date

cd tools
npm ci
npm run check-m                               # the Power Query, with Microsoft's parser (needs Node 18 or newer)
```

The schema test is skipped unless `LABTRACK_BI_SCHEMAS` points to a clone of
[microsoft/json-schemas](https://github.com/microsoft/json-schemas):

```console
git clone --depth 1 https://github.com/microsoft/json-schemas ../json-schemas
set LABTRACK_BI_SCHEMAS=..\json-schemas        # PowerShell: $env:LABTRACK_BI_SCHEMAS = "..\json-schemas"
py -m pytest tests/test_pbir.py -k schemas
```
