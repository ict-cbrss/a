# Timetable tools for TASS

A custom timetabling tool to replace Timetabler V10. It works only with the
CSV files TASS imports (`TTable.txt` and `SCourse.txt`). No TASS API is used.

**Phase 1 (this code):** read the TASS import files, check them for clashes,
view them, and write them back byte-for-byte so TASS imports them exactly as
before. Python 3.10+, standard library only.

## Usage

Put the exported files in `data/`. This folder is git-ignored so student data
is never committed.

```
python -m tt check  data/TTable.txt data/SCourse.txt          # list clashes (exit 1 if errors)
python -m tt report data/TTable.txt data/SCourse.txt -o data/timetable.html
python -m tt export data/TTable.txt data/SCourse.txt -o data/out   # files ready for TASS import
python -m unittest                                             # tests (synthetic data only)
PLAYWRIGHT_CHROMIUM=/path/to/chromium python -m unittest       # also runs the browser tests (pip install playwright)
```

`report` writes a single HTML file: the editor. Open it in any browser.

## Editor

Teacher, room, class, year and student timetables, an issues list, and a
list of your changes. Clashing cells are red.

- **Drag a lesson** to another cell to move it (every teacher row of that
  class in that slot moves with it).
- **Click a lesson** to change its slot, room or teachers, or delete it.
  Tick "every period of this class" to change the room or teachers everywhere.
- **Click an empty cell** to add a lesson; room and teachers are prefilled
  from the class's other lessons.
- **Student view** lists the student's classes with a dropdown to move them
  to another class, a Remove button, and an Add box. **Class view** does the
  same per class.
- **Undo / Redo** (also Ctrl+Z / Ctrl+Y). **Reset** discards all edits.
- Clash checks run after every edit; the Issues count updates live.
- Edits are kept in the browser (localStorage) so a reload doesn't lose
  them, but they are not written anywhere else.
- **Download TTable.txt / SCourse.txt** save the edited files in the TASS
  import format. With no edits they are byte-identical to the originals.

New lessons copy their grid columns (TTable columns 7–9) from an existing
lesson of the same class. Lessons can only be placed on days and periods
that appear in the original file.

### Print view

The **Print** tab lays the timetable out like the A3 master timetable
printouts: one sheet per main lesson block, rows are day × year, columns are
the real periods (Main Lesson spans TASS P3+P4). Pick a year for a class
timetable, or leave "All years" for the master. **Print** uses the browser's
print dialog (A3 landscape); "Save as PDF" there gives a file. The sheet
reflects any unsaved edits and says so in its footer.

## School configuration (`config/`)

`report` reads `config/` if it exists (`-c` to point elsewhere):

- **school.json**: the cycle. `blocks` map TASS days to main lesson blocks
  (days 1–5 = ML1, 6–10 = ML2, 11–15 = ML3), `weekdays` name the days within
  a block, `periods` name the TASS period numbers and give their times (one
  entry may cover several numbers), `year_order` is the print order.
- **classnames.csv**: `code,name,block`. Display name for each TASS class
  code; `block` is blank for all blocks, or a block number when the name
  changes per block (main lessons). Names are Timetabler's own, from its
  Class Details report; Year 11 is listed for terms that have it.
- **curriculum.csv**: Timetabler's Class Details report as a table: per
  year and line group, periods per cycle, doubles, class code and name,
  student count, teacher, room, seats. Not used yet; it is the input the
  line builder and solver will need.

TASS period numbers map to the school day as: P2 Morning Circle 9:00 ·
P3+P4 Main Lesson 9:10–10:40 · P5–P8 Periods 1–4 · P9 After School (Year 12).

None of these files contain student data, so they are committed.

## File formats

Both files are headerless, unquoted CSV with CRLF line endings.

**TTable.txt**: one row per class, per teacher, per slot.

| # | Field | Example | Notes |
|---|-------|---------|-------|
| 1 | Day | `1`–`15` | 15-day (3-week) cycle |
| 2 | Period | `2`–`9` | |
| 3 | Year | `12` | |
| 4 | Class code | `C12Phy_1` | |
| 5 | Room | `SLab` | |
| 6 | Teacher | `AH` | A class with several teachers has one row each |
| 7 | Grid column | `2` | Column (sub-line) in the Timetabler grid |
| 8 | Block start | `1` | First column of the line the class sits in |
| 9 | Block end | `3` | Last column of that line |

**SCourse.txt**: one row per student, per class.

| # | Field | Example | Notes |
|---|-------|---------|-------|
| 1 | Student ID | `100192` | |
| 2 | Name | | |
| 3 | Year | `10` | |
| 4 | Class code | `C10Geo_1` | Must exist in TTable |
| 5 | ? | `NS` / `F` / `M` | Meaning to confirm |
| 6 | ? | `Athens` / `Crete` | Meaning to confirm (house?) |
| 7 | ? | blank | |
| 8 | Form | `10` | |

Field meanings marked "?" and columns 7–9 of TTable were inferred from a
sample export. Confirm them against the TASS import documentation.

## Checks

- **Teacher clash**: a teacher has two different classes in one slot.
- **Room clash**: a room has two different classes in one slot. Team
  teaching, where one class has several teachers in the same room, is not a clash.
- **Student clash**: a student is enrolled in two classes that meet in one slot.
- **Unknown class**: an enrolment names a class that is not in the timetable.
- **Empty class**: a class is timetabled but has no students (warning).

## Roadmap

1. ✅ Read, check, view and re-export the TASS import files.
2. ✅ Editing with live clash checks, then export.
2b. ✅ Real day/period labels, class names, printable master and class timetables.
3. Line builder: build elective lines from student subject choices.
4. Solver (OR-Tools CP-SAT) to place classes in periods and rooms.
