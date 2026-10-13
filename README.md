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
```

`report` writes a single HTML file. It has teacher, room, class, year and
student timetables, and an issues list. Open it in any browser.

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
2. Editing: move a lesson, change a room or teacher, or move a student, with
   live clash checks, then export.
3. Line builder: build elective lines from student subject choices.
4. Solver (OR-Tools CP-SAT) to place classes in periods and rooms.
