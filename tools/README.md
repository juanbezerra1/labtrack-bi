# tools

Two checks that need more than the Python package: one needs Node, the other a PostgreSQL database. Neither runs with
the tests. [`../docs/verification.md`](../docs/verification.md) says what each one found.

## `check_m.cjs`: the Power Query

`check_m.cjs` checks the Power Query (M) of the model with the parser and the language services that Microsoft publishes
for Visual Studio Code. It reports syntax errors, unknown names, duplicate names and a wrong number of arguments in a
call to a library function, in every file of `model/powerquery/`.

```bash
cd tools
npm ci
npm run check-m
```

It needs Node 18 or newer. It never runs the queries: nothing here can, because only Power Query itself can read the data.
`labtrack-bi` has a smaller check of its own in Python (`src/labtrack_bi/mlint.py`), which runs with the tests; this one is
the second opinion, and CI runs it too.

The type of an argument is not checked on purpose: with Microsoft's library definitions the check reports "expected text but
got text" on correct code, which would bury the findings that matter.

`package-lock.json` pins the versions that were tested. The two packages are MIT licensed (see [`../NOTICE`](../NOTICE)).

## `crosscheck_sql.py`: the numbers, by a second route

`crosscheck_sql.py` asks PostgreSQL the questions of the 13 check queries and compares every answer with the expected
numbers of [`../docs/expected-numbers.md`](../docs/expected-numbers.md), which `src/labtrack_bi/engine.py` makes from the
CSV files. The SQL is written from the definitions of the measures and not from `engine.py`, so the two only agree if
both read the definitions the same way. It does not say what Power BI will show: no DAX engine is involved.

It needs the database that the CSV files were exported from: [labtrack-db](https://github.com/juanbezerra1/labtrack-db)
version 0.1.0, migrated and seeded with `labtrack seed --scale medium`. Then:

```bash
py -m pip install "psycopg[binary]"
py tools/crosscheck_sql.py --dsn "host=localhost user=postgres password=postgres dbname=labtrack"
```

(`LABTRACK_DSN` can hold the connection string instead of `--dsn`.) It prints one line per table of numbers, `OK` or
`FAIL`, and ends with the count of numbers that differ; the exit code is 1 if there is any.
