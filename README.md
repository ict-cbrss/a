# Timetable tools for TASS

A custom timetabling tool to replace Timetabler V10 (Timetabling Solutions).
It works with the two CSV files Timetabler exports for TASS to import
(`TTable.txt` and `SCourse.txt`). No TASS API is used.

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
python -m tt pdf    data/TTable.txt data/SCourse.txt -o data/pdf   # PDFs of every print sheet (needs playwright)
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
lesson of the same class. Lessons can be placed on any day or period the
config describes (or, without a config, any in the original file).

### Print view

The **Print** tab lays the timetable out like the A3 master timetable
printouts: one sheet per main lesson block, rows are day × year, columns are
the real periods (Main Lesson spans TASS P3+P4). Pick a year for a class
timetable, or leave "All years" for the master. **Print** uses the browser's
print dialog (A3 for timetables, A4 for duty sheets); "Save as PDF" there
gives a file. The sheet reflects any unsaved edits and says so in its footer.

Printing only works with the file open directly in a browser (double-click
it). Inside an embedded preview, such as the Claude app's file panel, the
Print button explains this instead.

### PDFs without a print dialog

`python -m tt pdf data/TTable.txt data/SCourse.txt -o data/pdf` writes
every print sheet as a PDF: `master-timetable.pdf`, one `class-N-timetable.pdf`
per year, `yard-duty-roster.pdf`, and one `duties-CODE.pdf` per teacher.
`-w dutysheets` (or `master`, `years`, `roster`) limits it to some sheets.
It needs `pip install playwright` and a Chromium (`playwright install
chromium`, or point `PLAYWRIGHT_CHROMIUM` at one). The per-teacher PDFs are
what an emailing step would attach.

## School configuration (`config/`)

`report` reads `config/` if it exists (`-c` to point elsewhere):

- **school.json**: the cycle. `blocks` map TASS days to main lesson blocks
  (days 1–5 = ML1, 6–10 = ML2, 11–15 = ML3), `weekdays` name the days within
  a block, `periods` name the TASS period numbers and give their times (one
  entry may cover several numbers), `year_order` is the print order.
- **classnames.csv**: `code,name,block`. Display name for each TASS class
  code; `block` is blank for all blocks, or a block number when the name
  changes per block (main lessons). Names are Timetabler's own, from its
  Class Names report, which also lists Year 11 and classes defined but not
  running this term (0 periods); they are included so they can be added in
  the editor by code.
- **curriculum.csv**: the class information plan (Timetabler [7A]): per
  year and group (line), the group's periods per cycle, doubles and
  cross-year group number (`mrcg`), and each class's code, name, student
  count, teacher, room and seats. Edited in the **Classes** tab; replace
  this file with the tab's download to keep changes. `check` uses it to
  warn when a class is timetabled for a different number of periods than
  planned, and it is the input the solver will build from.
- **duties.csv**: the yard duty roster (`day,block,weekday,slot,duty,
  teacher`), first taken from Timetabler's Yard Duties report. Edited in the
  **Duties** tab; replace this file with the tab's download to keep changes.
  Duties are stand-alone: they are not part of the TASS export.
- **teachers.csv**: duty settings per teacher
  (`code,name,email,max_duties,no_duties,away_days`): a cap on duties per
  cycle, whether they do duties at all, and the cycle days they are away
  (semicolon-separated day numbers; first taken from the "U" cells of the
  Yard Duties report). Name and email are for the duty sheets and for
  emailing them. Edited in the **Teachers** tab; replace this file with the
  tab's download to keep changes.
- **rooms.csv**: `code,name,seats,unavailable`. Seats give a warning when
  a class is bigger than its room; `unavailable` lists periods the room
  can't be used (`day:period;day:period`). Edited in the **Rooms** tab.
- `duty_slots` in **school.json** lists the times of day a duty can fall
  in, and which TASS periods clash with each (Before School ↔ P1 Morning
  Class, After School ↔ P9). `doubles` lists the consecutive period pairs
  that count as a double lesson (not across a break); edited in the
  **Settings** tab.
- `unavailable` in **curriculum.csv** (per group) and **teachers.csv** hold
  periods a group or teacher can't use, in the same `day:period` form.

### Duty builder (Duties tab)

A grid of duties (rows, grouped by time of day) × days of the cycle, with
a teacher dropdown in each cell. Red cells are problems: the teacher is away
that day, already has another duty at that time, or teaches a clashing
period. Orange cells are unassigned. The table on the right shows each
teacher's duties and lessons per cycle, so loads can be balanced. **Add
duty** adds a row; ✕ removes one; **Auto-fill** gives every empty cell to the
free teacher with the fewest duties. Teacher view shows each teacher's
duties under their grid, Print has a "Yard duty roster" sheet, and
**Download duties.csv** saves the roster.

### Class information (Classes tab)

Timetabler's [7A] screen: pick a year, and each column is a group (line)
of classes that run at the same time, with the group's periods per cycle,
doubles and cross-year group number at the top and its classes below, each
with teacher, room, seats and student count. Edit in place; ◀ ▶ reorder
groups (they are re-lettered A, B, C… like Timetabler), ✕ deletes a group
or removes a class, "Add class…" adds one to a group, **Add group** starts
a new column. The total periods against the cycle is shown. The table on
the right compares each teacher's planned periods (from the groups) with
what is timetabled. This is the plan only: it does not move lessons.
**Download curriculum.csv** saves it.

### Rooms, teacher limits, group availability, doubles

Timetabler's [5], [4A]/[1E], [13B] and [1C] in four small screens:

- **Rooms** tab: name, seats (with the biggest class planned into the room
  beside it), periods used, and a **Periods** button that opens a grid of
  the cycle to tick periods the room can't be used. Grey cells already
  have a lesson, so a red grey cell is a clash with the current timetable.
- **Teachers** tab gains **Max periods** (current load shown beside it),
  **Min off/day**, **Max consec.** and a **Periods** button for periods the
  teacher can't teach.
- **Classes** tab: each group header has an **Unavail** button for periods
  the group may not use (e.g. Year 12 only after school).
- **Settings** tab: tick which consecutive period pairs are doubles.

All of these produce Issues when the current timetable breaks them
(teacher/room/group in an unavailable period, class bigger than its room,
teacher over max periods, under minimum periods off, or over max
consecutive), and they are the constraints the solver will honour.

The **Teachers** tab holds each teacher's duty settings (name, email, max
duties, no duties, days away as tick boxes per cycle day). The builder marks
a teacher ✗ for a cell when they are away, do no duties, already have a
duty then, teach a clashing period, or would go over their cap; auto-fill
skips them. Print has **Duty sheets (one per teacher)**: an A4 page per
teacher with their duties per block and day, for all teachers or one.

TASS period numbers map to the school day as: P1 Morning Class (before MC,
used some days) · P2 Morning Circle 9:00 · P3+P4 Main Lesson 9:10–10:40 ·
P5–P8 Periods 1–4 · P9 After School (Year 12).

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
- **Period count**: a class has more or fewer periods per cycle than
  `curriculum.csv` plans (warning; needs the config).

## Roadmap

Mapped against Timetabler V10's Timetable Development tasks; the full
task-by-task comparison is in `docs/timetabler-reference.md`.

Done: read/check/export the TASS files (Quick Export); Edit Timetable [14];
Check Timetable [16]; master, class and yard duty prints [17, 18, 24];
yard duty allocation with availability, caps and auto-fill [15]; teacher
duty settings [4A part]; cycle parameters [1B/1C part]; class information
as data [7A].

Next, in order:

1. ✅ **Class Information editor** [7A, 7E] (Classes tab).
2. ✅ **Small config screens**: rooms with seats [5]; teacher max periods,
   unavailable periods, periods off per day [4A, 1E]; periods a group may
   not use [13B]; which period pairs count as doubles [1C].
3. **Construct Timetable** [12, 13]: the solver (OR-Tools CP-SAT) with
   pinned/locked groups, a lookahead view of which periods stay feasible,
   spread rules [1D], and a check of spread and days off [13J].
4. **Remaining prints**: teacher, room and student timetables, class lists,
   teacher loads, statistics, free teachers/rooms on the master.
5. Student subject choices and line building (Student Options module) - on
   hold.
6. Publish to a web daily organiser - via the staff portal, later.

Skipped on purpose (big-school features): faculties, bands, RURs (room
pools), meetings, multiple sites, FTE loads.
