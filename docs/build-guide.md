# Build guide

What you have: the data, a model that is already written (tables, relationships, 46 measures), the theme, and four
empty pages. What you build: the 46 visuals, following [report-spec.md](report-spec.md). Phase A takes about half an
hour; Phase B takes a few hours. Também em português: [build-guide.pt-BR.md](build-guide.pt-BR.md).

## What you need

* A Windows computer with **Power BI Desktop**, the regular one (Microsoft Store or the installer from
  powerbi.microsoft.com). The "optimized for Report Server" edition cannot open projects.
* This folder, **all of it**, somewhere that **OneDrive does not sync**. `C:\labtrack-bi` is the easiest place: the
  model looks for the data in `C:\labtrack-bi\data` by default. Do not open `labtrack.pbip` from inside the zip:
  Power BI needs the folders that sit next to it. Either right-click the zip and choose Extract All, or, if you have
  Git, run `git clone https://github.com/juanbezerra1/labtrack-bi C:\labtrack-bi`.
* Python 3.10 or newer, **only for the checks** (`check-model`, `check-report`). The report itself does not need
  Python. In a terminal in this folder, once: `py -m pip install -e .`. From then on every command of this guide is
  `py -m labtrack_bi <command>`; if the Scripts folder of Python is on your PATH, `labtrack-bi <command>` does the same.
* The names of the menus below are the English ones. If your Power BI is in another language, the buttons are the same
  but the words differ; to follow this guide word for word, change the language in File > Options and settings >
  Options > Regional Settings > Application language, and restart.

Since September 2026 the project format (`.pbip`) is generally available in Power BI Desktop and PBIR is the default
report format, so there is nothing to turn on. Desktop still saves `.pbix` files by default, but a project you opened
as `labtrack.pbip` is saved back as a project. In an older release turn the options on first: File > Options and
settings > Options > Preview features: "Power BI Project (.pbip) save option", "Store semantic model using TMDL
format" and "Store reports using enhanced metadata format (PBIR)"; restart Desktop.

## Phase A: open the project and check the numbers

1. **Open `labtrack.pbip`** (double-click it, or File > Open report > Browse this device). Desktop shows the four
   pages, empty, and the tables of the model; the tables hold no rows until you refresh.
2. **Point the model to the data**, unless the folder is `C:\labtrack-bi`: Home > Transform data > Edit parameters,
   type the full path of the `data` folder in `DataFolder` (for example `D:\work\labtrack-bi\data`), OK, and
   Close & Apply if Desktop asks.
3. **Refresh**: Home > Refresh. Eight queries load, with these rows:

   | Table | Rows | Table | Rows |
   |---|---:|---|---:|
   | Calendar | 2,192 | Session | 909 |
   | Study | 3 | Recording | 1,634 |
   | Participant | 200 | Trial | 45,806 |
   | Researcher | 12 | Device | 24 |

   The Table view (second icon of the left bar) shows the number of rows of the selected table at the bottom.
4. **Look at the model**: Model view (third icon). It must look like [img/model.svg](img/model.svg): seven
   relationships, each many-to-one with the arrow towards the one side, and a table called `Measures` with no
   relationships and 46 measures in six folders.
5. **Check the numbers**: DAX query view (fourth icon). Open `model/check.dax` in any text editor, copy **one** query
   (every line from `EVALUATE` to the blank line before the next comment), paste it in the DAX query view and press
   Run. Compare the result with the table of the same number in [expected-numbers.md](expected-numbers.md). Do all 13.
   The ones that matter most are 1 (every measure), 4 (running totals by month) and 13 (the three effects). A
   difference in the last digit may be rounding; a different number is a bug, in the model or in my reading of Power BI,
   and I want to know which query it was and what it returned.
6. **Save** (Ctrl+S). From this moment the project files belong to Power BI Desktop: it rewrites them in its own way.
   Do not run `py -m labtrack_bi build --reset-project` unless you want to throw your work away (it keeps a `.backup`
   copy of the old folders, but you would lose the visuals in the new ones).
7. In a terminal in this folder: `py -m labtrack_bi check-model`. It reads the model that Desktop saved and says whether
   it still means what [model.md](model.md) says. Its last line should be `ok: the model says what the spec says`.

### If the project does not open

Desktop is the one reader I could not test with here, so this can happen. Write down the version (Help > About) and the
exact message, and send them to me; I will fix the generator.

**First thing to try.** Three small files lack a line that Microsoft's published schemas list as required (the sample
projects that Desktop itself saves do not have it either; see [verification.md](verification.md#three-small-files)).
If the message mentions a schema, a version or a property that it does not know, add the line as the first property of
the file (the comma at its end is part of it), save, and open the project again:

| File | The line to add |
|---|---|
| `labtrack.pbip` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",` |
| `labtrack.Report/definition.pbir` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",` |
| `labtrack.SemanticModel/definition.pbism` | `"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",` |

If that does not help, you can build the same model by hand (nine queries to paste, seven relationships, 46 measures),
which is slow but works:

1. Open a new blank report. Home > Transform data > New source > Blank query > Advanced editor. Paste
   `model/powerquery/DataFolder.pq` (the last line; correct the path) and name the query `DataFolder`.
2. Do the same for each of the other eight files in `model/powerquery/`, naming each query as the file is named
   (`Calendar`, `Study`, ...). Close & Apply.
3. Mark `Calendar` as the date table (Table tools > Mark as date table, column `Date`), and make the seven relationships
   of [model.md](model.md#relationships) in Model view (drag from the many side to the one side; leave the others as
   Power BI suggests: many-to-one, single direction).
4. Create the table `Measures` and paste each block of `model/measures.dax`, as the first lines of that file explain.
5. Go on with step 5 above. The report is the same from there.

## Phase B: build the report

### The loop

For each page, in the order of [report-spec.md](report-spec.md): build the visuals of the list, one by one; save;
run `py -m labtrack_bi check-report`; fix what it lists; look at the page next to its wireframe in `docs/img/`. The
check only reads the file that Desktop saved. It compares, for every visual, the type, the title, the position (it allows 8
pixels), and the fields in each well. It is the proof that you did what the spec says, nothing more: whether the page
looks good is for your eyes.

```console
PS C:\labtrack-bi> py -m labtrack_bi check-report
```

It prints the errors first (a visual that is missing, a field in the wrong well), then the warnings (a position that is
more than 8 pixels away, a title that is not the one of the spec, a visual that the spec does not list), and ends with
the number of visuals of the spec that it found with the right type and fields. It exits with an error only while there
are errors; warnings do not fail it. A page that you have not started yet is listed as missing: that is expected.

### Order of work on a page

1. The text box with the title, then the slicers, then the cards: they are the easy visuals and they fix the
   position of everything else.
2. The charts. 3. The table.
4. Set the Title, the position and the alt text of each visual **as you go**. It is much slower to come back to
   all the visuals at the end.

Colours come from the theme `LabTrack`, already applied to the report (View > Themes). Do not colour anything by hand:
the palette of the theme was checked for readers who do not see all colours ([design.md](design.md#colours)).

### How to do each thing

**Add a visual with its fields.** Click an empty place of the page, click the icon of the type in the Visualizations
pane (hold the pointer over it to read the name), and drag the fields from the Data pane to the wells that the Fields
column names (X-axis, Y-axis, Legend, Values, Tooltips). `Table[Column]` is a column of that table; `[Name]` is a measure,
and every measure is in the table `Measures`. For a card, a slicer and a table, the well is called Fields, Field and
Columns in the spec; in the pane it may be called Data or Values.

**Title, position, size, alt text.** Select the visual, then Format visual (the paint roller) > General tab:

* *Title*: turn it on and type the text of the Title column. The checker finds your visual by this text first.
  For a text box, the Title column is the text inside the box.
* *Properties*: Position (horizontal, vertical) and Size (width, height) take the four numbers of the Position column.
* *Alt text*: one sentence about what the visual shows.

**Copy a visual.** Ctrl+C, Ctrl+V pastes the copy on the same position; change the field and the title. The six cards
of page 1 are one card made once and pasted five times.

**Slicer.** Slicer icon, the column in Field. Format visual > Visual > Slicer settings > Options > Style: Dropdown or
Tile, as the Notes column says. If the tiles do not fit in one row, set the orientation to horizontal.

**Data labels, legend, axis.** Format visual > Visual > Data labels, Legend, X axis, Y axis. The Notes column says when
the labels are on. A chart with two or more series always keeps its legend.

**Sort.** The `...` at the top right of a chart > Sort axis > the measure, then `...` > Sort descending.

**Filter a visual.** With the visual selected, the Filters pane shows "Filters on this visual". Drag the column there.
*Basic filtering* has a list of tick boxes (untick `(Blank)` to leave the blanks out); *Advanced filtering* has
"is less than or equal to 4" and the like; *Top N* takes the number, the "By value" measure, and then Apply filter.
The notes of the spec say which column and which values.

**Table.** Format visual > Visual > Totals turns the totals row on. Data bars: Format visual > Visual > Cell elements,
choose the column in "Apply settings to", turn on Data bars.

**Text box.** Home > Text box (or Insert > Text box). Type the text and format it as the Notes column says.

### The four pages

* **Page 1, Overview** (13 visuals). Six headline cards, two charts of sessions, a running total and a table of the
  three studies. The charts by month are filtered to the years 2024 to 2026: the calendar goes from 2023 to 2028 and the
  sessions go from March 2024 to December 2026.
* **Page 2, Recruitment** (13). The chart of visits is filtered to visits 1 to 4, because every study plans four
  visits and the higher numbers are extra visits.
* **Page 3, Data quality** (12). The chart of QC results has four series (passed, flagged, rejected, pending), so its
  legend stays on. The two bar charts on the right have a filter each (blank reasons out, top 8 devices).
* **Page 4, Findings** (8). Three effects planted in the data. The text box at the top says that this is synthetic data:
  keep it, because the page shows how a report is made, and its numbers are not evidence of anything.

### When the page is done

1. Save (Ctrl+S) and run `py -m labtrack_bi check-report`. Aim for no error and no warning.
2. **Screenshots.** For each page, show it at its real size (View > Page view > Actual size, if your screen is large
   enough), take a picture of the canvas only (Windows: Win+Shift+S) and save it as a PNG with these names, in `docs/img/`:

   ```text
   docs/img/screenshot-overview.png
   docs/img/screenshot-recruitment.png
   docs/img/screenshot-data-quality.png
   docs/img/screenshot-findings.png
   ```

   Then `py -m labtrack_bi add-screenshots` puts the ones that exist into `README.md` and `README.pt-BR.md`, between
   the two `screenshots` comments. You can run it again when you add the others.
3. Close Desktop, and look at `git status`-style changes before you commit: the project folders hold only text files,
   and `.pbi/localSettings.json` and `.pbi/cache.abf` (the cache of the data; large) are in `.gitignore`.

## When something is off

| What you see | Probable cause | What to do |
|---|---|---|
| Desktop says the file is not supported or cannot be opened | Report Server edition, or an old release with the project options off | Install the regular Desktop, or turn on the three preview options above |
| Desktop says `ReportDefinition: Required artifact is missing in '...\labtrack.Report\definition.pbir'` | The folders `labtrack.Report` and `labtrack.SemanticModel` are not next to `labtrack.pbip`. The usual cause is opening the file from inside the zip, where Windows unpacks only that one file | Close Desktop. Extract the whole zip (right-click > Extract All) or `git clone` the repository, and open the `labtrack.pbip` of that folder |
| The tables are empty | The data was not loaded yet | Home > Refresh |
| The refresh says it cannot find a file or a folder | `DataFolder` points to the wrong place | Home > Transform data > Edit parameters; the folder must contain `dim_date.csv` |
| The refresh says access to the path is denied | The folder is in OneDrive, or in a place that Windows protects | Move the repository to `C:\labtrack-bi` |
| A number of `check.dax` differs from `expected-numbers.md` | A bug in the model, or the data folder is not the one of this repository | Compare `data/SHA256SUMS` with the files; if they match, send me the query and the result |
| The bar "Apply external changes" shows up | A file of the project was changed while Desktop had it open (for example by `py -m labtrack_bi build`) | Choose Apply, or close without saving; do not run `build` with Desktop open |
| `check-report` says a visual is missing and you built it | Another type of visual, another field in a well, or a title that is not the one of the spec | Read the message: it names what it expected and the nearest visual it found |
| `check-report` says "extra visual" | A visual that the spec does not list (for example one that Desktop made when you dropped a field on the empty page) | Delete it, or ignore the warning if you added it on purpose |

## After Desktop has saved the project

`py -m labtrack_bi build` writes the files that are derived from `src/labtrack_bi/spec.py` (the Power Query and DAX
files, the documents, the drawings) and writes the project (`labtrack.pbip` and its two folders) only the first time.
From the first save in Desktop the project is Desktop's; `py -m labtrack_bi check` stops comparing it byte by byte and
says so, and
`check-model` and `check-report` compare what it means. If you change `spec.py`, change the project by hand in Desktop
too, or use `build --reset-project` to start the project again from the spec (the old folders stay as `.backup`).
