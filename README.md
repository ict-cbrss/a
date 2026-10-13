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
python -m tt solve  data/TTable.txt data/SCourse.txt -o data/solved -t 120   # construct a timetable from the plan (needs ortools)
python -m tt next-term timetable/TTable.txt "Term 1 2027" -s data/SCourse.txt -r end-of-year   # plan next term in next/
python -m tt start-term next                                   # when the term starts: make next/ the current term
python -m tt rollover data/TTable.txt data/SCourse.txt -o data/rolled --advance 11 --leave 12   # students up a year, on its own
python -m tt backup  data/TTable.txt data/SCourse.txt -o data/backups    # one zip of timetable, students and config
python -m tt restore data/backups/backup-term-4-2026-20261013-0900.zip -o data/restored
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

### Files menu: TASS files, students, versions, backups, save as

**Files ▾** (top right) works without the command line or the repo:

- **Open TTable.txt / Open SCourse.txt** replaces the timetable or the
  enrolments with a file exported from TASS or Timetabler. This is how the
  cloud-built page gets its students: open it, load SCourse.txt from your
  computer, and the Student view and student-clash check work; the student
  data stays in your browser and only leaves it through Export SCourse.txt.
- **Add students from a TASS list** reads a CSV with a header row naming a
  student code, a name (or surname and given names) and a year column, as
  TASS's student export does. Each new student is enrolled in the classes
  that three quarters or more of their year already take; a year with no
  students yet (the new Year 7) gets every class of that year, so remove the
  half-year groups they are not in from the Student view. Students already
  on the page are skipped.
- **Save a version…** keeps a named copy of everything on the page in the
  browser; restore, download (.json) or delete it from the list. One is
  saved automatically before each Reset. Restoring is itself an undoable
  edit.
- **Download a backup (.json) / Open a backup** moves the whole state to a
  file and back, between browsers or computers.
- **Save as a copy of this page (.html)** writes a new editor file with the
  current state as its starting point: a clean baseline for "what if"
  work, or a dated copy to keep.

Every edit, including these, goes through Undo/Redo and the Changes list.

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

### Construct Timetable (the solver)

`python -m tt solve` is Timetabler's [12]/[13] step: it places every group
(line) from `curriculum.csv` into periods of the cycle with OR-Tools CP-SAT
(`pip install ortools`). Rules it keeps: a year is in one line per slot; no
teacher or room in two lines at once; teacher, room and group unavailable
periods and teacher days away; the doubles each group needs (on the pairs
marked in Settings); at most two lessons of a group per day (the main lesson
is two periods); teachers' minimum periods off per day and maximum
consecutive lessons; periods reserved for certain years
(`restricted_periods` in school.json, e.g. after school for Year 12 only).

**Locked** groups (tick in the Classes tab, or the Construct tab) keep
exactly the slots they have in the current `TTable.txt`. For everything
else the solver prefers the current timetable where it still fits, so a
re-solve moves as little as possible. Classes with no room in the plan use
the room they mostly have in the current timetable, avoiding rooms already
taken in their line. The output is a new `TTable.txt` (plus a copy of
SCourse.txt) in `solved/`, with a list of which lines moved and the result
of `check`. If no timetable satisfies the plan, it says which plan rows
contradict each other, or retries with one rule family dropped at a time
(doubles, spread, teacher limits, availability) and reports which one made
it feasible.

The **Construct** tab in the editor lists the lines with their classes,
periods, teachers, rooms and how many periods they currently have, with a
lock tick per line (Lock all / Unlock all). Click a line to see where it
could go: green cells are free of clashes with locked lines, unavailability
and restricted periods; red cells say why not; bold dots mark where it is
now. This is a static lookahead; the solver does the full search.

### Running it in the cloud

Nothing needs installing on a laptop. `.github/workflows/timetable.yml` is
a GitHub Actions workflow: Actions → **Build timetable** → Run workflow. It
checks `timetable/TTable.txt` (the current timetable, kept in the repo; it
holds class, teacher and room codes, no student data), runs the solver
unless told not to, builds the editor page and all PDFs, and publishes them
as a downloadable artifact. To run a cycle: edit the plan and settings in
the editor, download the CSVs into `config/`, commit (GitHub's web upload
works), run the workflow, download the artifact, import `TTable.txt` into
TASS.

`SCourse.txt` has student names, so it stays out of the repository; the
cloud build's student views are empty and it can't check student clashes.
Run `python -m tt check` with both files wherever SCourse.txt is kept for
that, or, later, the staff portal can hold it.

### Next term and rollover

The live timetable is `timetable/TTable.txt` with its settings in `config/`.
To get the coming term ready before this one ends, plan it in a separate
folder so nothing live changes:

```sh
python -m tt next-term timetable/TTable.txt "Term 1 2027" -s data/SCourse.txt -r end-of-year
```

This creates `next/` with a copy of `config/` (term renamed), `TTable.txt`
(a copy to start from), `SCourse.txt` with the students moved up a year, and
`rollover-report.txt`. Edit and solve there (`-c next/config`, or the
workflow's **plan: next** option), commit `next/TTable.txt` and
`next/config/`, and on the first day of term:

```sh
python -m tt start-term next
```

which copies `next/TTable.txt` to `timetable/` and `next/config/` to
`config/`, keeps the old ones in `archive/<old term>/`, and leaves `next/`
for you to delete. Import `next/TTable.txt` and `next/SCourse.txt` into
TASS. `SCourse.txt` and `rollover-report.txt` are ignored by git everywhere
because they hold student names.

**Backups.** Every committed `timetable/TTable.txt` and `config/` is in git
history, `start-term` files each finished term under `archive/`, and the
editor keeps versions in the browser. `python -m tt backup` zips the
timetable, the student file and `config/` into one dated file for anything
git does not hold (the student file, work between commits); `python -m tt
restore` unpacks it into a folder. `backups/` is ignored by git.

**Rollover** (`-r`, or `python -m tt rollover` on its own) moves students
between year groups. The two moments in the year (NSW: Year 12 starts in
Term 4):

| Preset | When | What moves |
| --- | --- | --- |
| `end-of-year` | Term 4 → Term 1 | Years 7–11 move up one; Year 12 stays (their HSC year runs to Term 3). The new Year 7 comes from TASS later. |
| `into-term4` | Term 3 → Term 4 | Year 12 leaves; Year 11 becomes Year 12. |

Class codes carry the year (`C07E_1` is Year 7 English), so a student's
classes are remapped: a class that three quarters or more of the year takes
is a *core* class, and the cohort swaps its year's core classes for the next
year's (Year 7 Geography and Year 8 History are different subjects, so a
code match isn't needed). Cross-year classes (`E9/10Ar_1`) are kept while
the class still takes the student's new year. Anything else is matched by
code (`C07VAB_1` → `C08VAB_2`); when no match exists the enrolment is
dropped and the report lists the class and its students so they can be
placed by hand. A year with no classes in the timetable yet (Year 11 after
an end-of-year roll) is reported once: build its classes in Class plan,
construct, then allocate students. `curriculum.csv`'s student counts are
refreshed from the rolled file.

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
  count, teacher, room and seats. Edited in the **Class plan** tab; replace
  this file with the tab's download to keep changes. `check` uses it to
  warn when a class is timetabled for a different number of periods than
  planned, and it is the input the solver will build from.
- **duties.csv**: the yard duty roster (`day,block,weekday,slot,duty,
  teacher`), first taken from Timetabler's Yard Duties report. Edited in the
  **Duty roster** tab; replace this file with the tab's download to keep changes.
  Duties are stand-alone: they are not part of the TASS export.
- **teachers.csv**: duty settings per teacher
  (`code,name,email,max_duties,no_duties,away_days`): a cap on duties per
  cycle, whether they do duties at all, and the cycle days they are away
  (semicolon-separated day numbers; first taken from the "U" cells of the
  Yard Duties report). Name and email are for the duty sheets and for
  emailing them. Edited in the **Teacher settings** tab; replace this file with the
  tab's download to keep changes.
- **rooms.csv**: `code,name,seats,unavailable`. Seats give a warning when
  a class is bigger than its room; `unavailable` lists periods the room
  can't be used (`day:period;day:period`). Edited in the **Room settings** tab.
- `duty_slots` in **school.json** lists the times of day a duty can fall
  in, and which TASS periods clash with each (Before School ↔ P1 Morning
  Class, After School ↔ P9). `doubles` lists the consecutive period pairs
  that count as a double lesson (not across a break); edited in the
  **Doubles** tab.
- `unavailable` in **curriculum.csv** (per group) and **teachers.csv** hold
  periods a group or teacher can't use, in the same `day:period` form.

### Duty builder (Duty roster tab)

A grid of duties (rows, grouped by time of day) × days of the cycle, with
a teacher dropdown in each cell. Red cells are problems: the teacher is away
that day, already has another duty at that time, or teaches a clashing
period. Orange cells are unassigned. The table on the right shows each
teacher's duties and lessons per cycle, so loads can be balanced. **Add
duty** adds a row; ✕ removes one; **Auto-fill** gives every empty cell to the
free teacher with the fewest duties. Teacher view shows each teacher's
duties under their grid, Print has a "Yard duty roster" sheet, and
**Download duties.csv** saves the roster.

### Class information (Class plan tab)

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

- **Room settings** tab: name, seats (with the biggest class planned into the room
  beside it), periods used, and a **Periods** button that opens a grid of
  the cycle to tick periods the room can't be used. Grey cells already
  have a lesson, so a red grey cell is a clash with the current timetable.
- **Teacher settings** tab gains **Max periods** (current load shown beside it),
  **Min off/day**, **Max consec.** and a **Periods** button for periods the
  teacher can't teach.
- **Class plan** tab: each group header has an **Unavail** button for periods
  the group may not use (e.g. Year 12 only after school).
- **Doubles** tab: tick which consecutive period pairs are doubles.

All of these produce Issues when the current timetable breaks them
(teacher/room/group in an unavailable period, class bigger than its room,
teacher over max periods, under minimum periods off, or over max
consecutive), and they are the constraints the solver will honour.

The **Teacher settings** tab holds each teacher's duty settings (name, email, max
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
3. ✅ **Construct Timetable** [12, 13]: solver with locked groups, a
   lookahead view, spread and teacher-limit rules, cloud workflow.
4. ✅ **Next term and rollover**: plan the coming term in `next/`, move
   students up a year, make it current with an archive of the old term.
5. **Remaining prints**: teacher, room and student timetables, class lists,
   teacher loads, statistics, free teachers/rooms on the master.
6. Student subject choices and line building (Student Options module) - on
   hold.
7. Publish to a web daily organiser - via the staff portal, later.

Skipped on purpose (big-school features): faculties, bands, RURs (room
pools), meetings, multiple sites, FTE loads.
