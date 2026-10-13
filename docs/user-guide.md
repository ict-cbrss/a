# Timetable Editor User Guide

## What this is

The Timetable Editor replaces Timetabler V10 for building and maintaining the
high school timetable. It is one web page (`timetable.html`) that opens in any
browser, plus a cloud build that runs the solver and makes the PDFs. Nothing is
installed on your computer.

It produces the same two files Timetabler did, `TTable.txt` and `SCourse.txt`,
so the TASS import is unchanged. Yard duties, teacher settings and the class
plan live alongside the timetable in the same page.

| Timetabler task | Where it is now |
| --- | --- |
| Class Information [7A] | **Class plan** tab |
| Teachers, Rooms, Period details [4A, 5, 1C] | **Teachers**, **Rooms**, **Doubles** tabs |
| Construct Timetable [12, 13] | **Construct** tab + the cloud build |
| Edit Timetable [14] | **Teacher / Room / Class / Year / Student** tabs |
| Check Timetable [16] | **Issues** tab |
| Yard duties [10, 15, 24] | **Duty roster** tab, duty sheets under **Print** |
| Master, class, teacher timetables [17–22] | **Print** tab and the PDFs |
| Quick Export to TASS | **Download TTable.txt / SCourse.txt** buttons |

## Getting started

Open `timetable.html` by double-clicking it. It must be opened directly in
Chrome, Edge or Safari; inside a preview panel (for example the Claude app's
file viewer) printing and some downloads are blocked.

The tabs across the top:

| Tab | What it shows |
| --- | --- |
| Home | Counts, errors, unsaved edits, and the term's steps with links. |
| Teacher, Room, Class, Year, Student | A timetable grid for one teacher, room, class, year or student. Pick who from the dropdown. This is where you edit the timetable. |
| Class plan | The plan: groups (lines) of classes per year, with periods, teachers and rooms. |
| Duty roster | The yard duty roster builder. |
| Teacher settings | Per-teacher settings: email, duty cap, days away, period limits. |
| Room settings | Rooms, seats and when a room can't be used. |
| Doubles | Which period pairs count as a double. |
| Construct | The lines the solver will place, locks, and where each line can go. |
| Issues | Every clash or broken rule, updated as you edit. |
| Changes | A plain-English list of every edit you've made. |
| Print | Master, class and duty sheets, and per-teacher duty sheets. |

**Saving.** Edits are kept in your browser until you press **Reset**, so you
can close the page and come back. They are not saved anywhere else. To keep
them for good, download the file that holds them and put it in the right place:

| Button | File | Where it goes |
| --- | --- | --- |
| Download TTable.txt / SCourse.txt | The timetable and enrolments | Import into TASS, and `TTable.txt` into the repo's `timetable/` folder |
| Download curriculum.csv | The class plan and locks | `config/` in the repo |
| Download teachers.csv, rooms.csv, duties.csv, school.json | Settings and the duty roster | `config/` in the repo |

**Undo / Redo** (also Ctrl+Z / Ctrl+Y) cover every kind of edit. The
**Changes** tab lists them all.

The day is laid out as: Morning Class (sometimes) · MC 9:00 · Main Lesson
9:10–10:40 (two periods) · Periods 1–4 · After School (Year 12 only). The
15-day cycle is three Main Lesson blocks of Mon–Fri.

## A term in steps

```
1. Set the plan  →  2. Save to GitHub  →  3. Build timetable  →  4. Review result
   (Classes,          (CSVs into            (cloud solver,         (editor +
    Teachers, Rooms)   config/)              ~2 minutes)            Issues tab)
                           ▲                                            │
                           └──── adjust plan, rebuild ◄──┐              ▼
7. Print and email  ◄─  6. Import into TASS  ◄───────  5. Hand edits
   (master, class,       (TTable.txt +                  (drag, click,
    duty sheets)          SCourse.txt)                   students)
```

Steps 1, 4, 5 and 7 happen in the editor; step 3 runs on GitHub. If the result
isn't right, change the plan or lock what should stay, and build again.

1. **Set the plan.** In **Class plan**, check each year's groups: periods,
   doubles, teacher, room. In **Teacher settings**, **Room settings** and **Doubles**, record
   days away, period limits, room seats and the double-period pairs. Lock any
   groups that must not move.
2. **Save to GitHub.** Download `curriculum.csv`, `teachers.csv`, `rooms.csv`
   and `school.json` and upload them into the repo's `config/` folder (GitHub's
   web page has an Upload files button). If the current timetable has changed,
   put the latest `TTable.txt` in `timetable/`.
3. **Build timetable.** On GitHub, open Actions, pick **Build timetable**,
   press Run workflow. About two minutes later a `timetable` artifact appears
   with the new editor page, the new `TTable.txt` and all PDFs.
4. **Review.** Open the editor from the artifact. The **Issues** tab should
   show no errors (student clashes can't be checked in the cloud; see
   Troubleshooting). **Changes** is empty because this is a fresh file.
5. **Hand edits.** Fix anything by hand in the timetable tabs, move students
   between classes in the **Student** or **Class** tab.
6. **Import into TASS.** Download `TTable.txt` and `SCourse.txt` and import
   them as you did with Timetabler's export.
7. **Print and email.** Use **Print** for the master, a year, the duty roster
   or per-teacher duty sheets, or take the PDFs from the artifact.

## Editing the timetable

Any of the Teacher, Room, Class, Year and Student tabs is a live grid of the
whole cycle: three Main Lesson blocks across, periods down. Red cells are
clashes.

| To do this | Do this |
| --- | --- |
| Move a lesson | Drag it to another cell. Every teacher row of that class in that period moves with it. |
| Change a lesson's room or teachers | Click it. Teachers are comma-separated (`AH, SC`); tick *every period of this class* to change all its lessons at once. |
| Add a lesson | Click an empty cell, choose the class. Room and teachers are prefilled from the class's other lessons. |
| Delete a lesson | Click it, then **Delete lesson**. |
| Move a student to another class | **Student** tab: pick the student, change the dropdown beside the class. **Remove** and **Add a class…** are there too. |
| See who is in a class | **Class** tab: the list under the grid, with Remove and Add. |
| Undo | **Undo** / **Redo**, or Ctrl+Z / Ctrl+Y. |
| Start again | **Reset** discards every edit and goes back to the loaded files. |

The **Issues** tab reruns after every edit. Errors stop a clean import;
warnings are worth a look:

| Issue | Meaning |
| --- | --- |
| Teacher clash / Room clash | Two different classes in one slot with the same teacher or room. Team teaching (one class, two teachers, one room) is not a clash. |
| Student clash | A student is enrolled in two classes that meet at the same time. |
| Unknown class | An enrolment names a class that isn't in the timetable. |
| Teacher / room / group unavailable | A lesson sits in a period that the Teachers, Rooms or Classes tab says can't be used. |
| Period count | A class has more or fewer periods than the plan says. |
| Room too small | More students than the room's seats. |
| Teacher load / off / consecutive | A teacher is over their max periods, under their min periods off a day, or over their max in a row. |
| Duty clash / duty load | From the Duties tab (see Yard duties). |
| Empty class, no teacher | Warnings: a timetabled class with no students, or a planned class with no teacher. |

When you're done, **Download TTable.txt** and **Download SCourse.txt**. With no
edits they are byte-for-byte the files you loaded, so TASS imports them exactly
as before.

## The plan: Class plan tab

The plan is what the solver builds from, and it is Timetabler's Class
Information screen laid out the same way. Pick a year; each column is a
**group** (a line): classes that run at the same time, for the same periods.

| Row | Meaning |
| --- | --- |
| Periods | How many periods per cycle the group needs. The total against the cycle (135) shows above the table. |
| Doubles | How many of those must be a double (two consecutive periods from the pairs ticked in **Settings**). |
| Cross-year | A number shared by groups in different years that run together, e.g. the 9/10 electives (1–4). Those groups are built as one line. |
| Locked | Tick to keep this group exactly where the current timetable has it when the solver runs. |
| Classes | Each class in the group with its teacher, room, seats and student count. |

- **Add class…** at the foot of a column adds any known class to that group;
  ✕ next to a class removes it.
- **Add group** starts a new column (it asks for the first class's code, e.g.
  `C09Geo_1`).
- ◀ ▶ move a group left or right; groups are re-lettered A, B, C… like
  Timetabler. ✕ in the header deletes the group.
- **Unavail** in a group header opens a grid to mark periods the group may not
  use (for example a Year 12 class that only runs after school, or a group tied
  to one Main Lesson block).

The table on the right compares each teacher's **planned** periods (from these
groups) with what is **timetabled**; orange means they differ. Classes with no
teacher show up in Issues.

Changing the plan does not move any lesson. It changes what the next build will
produce, and what Issues compares against.

**Download curriculum.csv** saves the plan; it goes in the repo's `config/`
folder.

## Settings: Teacher settings, Room settings, Doubles tabs

These hold the rules the solver obeys and the Issues tab checks. All three save
to files that go in `config/`.

**Teachers tab**, one row per teacher code:

| Column | Used for |
| --- | --- |
| Name, Email | Duty sheets and, later, emailing them. |
| Max duties, No duties | Yard duty cap per cycle; no duties keeps them off the roster. |
| Max periods | Teaching periods per cycle; the current load shows beside it. |
| Min off/day | Minimum free periods each day. |
| Max consec. | Longest run of back-to-back lessons allowed. |
| Periods | Opens a grid of the cycle to mark periods they can't teach. |
| Day tick boxes (ML1–ML3, Mo–Fr) | Days they are away. No lessons or duties go there. |

**Rooms tab**: name, seats (the biggest class planned into the room sits beside
it and turns red if it won't fit), periods used, and a **Periods** button for
when the room can't be used. **Add room** adds a code that TASS will see; rooms
in use can't be deleted.

**Settings tab**: tick which consecutive period pairs count as a double. Pairs
split by a break stay unticked. Currently Main Lesson P3+P4, Period 1+2 and
Period 2+3.

**The availability grid** is the same everywhere (teachers, rooms, groups):
click a cell to mark it unavailable (red). Grey dots are periods that already
have a lesson, so a red cell with ! is a clash with the current timetable.
Click a block name, a day or a period name to toggle the whole block, day or
row at once.

## Yard duties

Duties are built in the **Duty roster** tab and are stand-alone: they never go to
TASS. The tab starts with the roster loaded from `duties.csv`.

The grid has one row per duty, grouped by time of day (Before School, Recess,
Lunch 1, Lunch 2, After School), and one column per day of the cycle. Each cell
is a dropdown of teachers.

| Colour | Meaning |
| --- | --- |
| Red cell | A problem: the teacher is away that day, already has another duty at that time, teaches a clashing period (Before School vs a morning class, After School vs Year 12's after-school period), does no duties, or would go over their cap. Hover for the reason. Teachers who can't take a cell show ✗ in its dropdown. |
| Orange cell | Unassigned. |

- **Add duty** adds a row (choose the time of day, type the name). ✕ on a row
  removes it from every day.
- **Auto-fill empty duties** gives each empty cell to the free teacher with the
  fewest duties so far, honouring everything in the Teachers tab.
- The table on the right shows duties, max, lessons and days away per teacher,
  so loads can be balanced by eye.
- Each teacher's duties also appear under their grid in the **Teacher** tab.

**Download duties.csv** saves the roster into `config/`. To print: **Print** →
*Yard duty roster* (one A3 sheet per block) or *Duty sheets (one per teacher)*
(an A4 page each, all teachers or one). The cloud build also makes one
`duties-CODE.pdf` per teacher, ready to email.

## Construct: locks, lookahead and the cloud build

The solver places every group from the plan into the cycle. It runs on GitHub,
not in the editor; the **Construct** tab is where you prepare and preview.

**Rules the solver keeps:** a year is in one line per period; no teacher or
room in two lines at once; teacher, room and group unavailable periods and days
away; each group's doubles; at most two lessons of a group per day; teachers'
minimum periods off and maximum consecutive lessons; after school for Year 12
only.

**Construct tab:**

- One row per line (a group, or cross-year groups joined, e.g. `10E+9E`): its
  classes, periods, doubles, teachers, rooms and how many periods it has now
  (orange if that differs from the plan).
- **Lock** keeps a line exactly where the current timetable has it. **Lock
  all** / **Unlock all** for the lot. Locks are the same ticks as in the
  Classes tab and save into `curriculum.csv`.
- Click a line to see **where it can go**: green cells are free, red cells say
  why not (a locked line, someone away, a reserved period), dots show where it
  is now. This is a quick check; the solver does the full search.

**A good first run:** lock everything, unlock one year, build, and compare.
Unlocked lines are placed where they are now whenever that still works, so a
build moves as little as it can.

**Running a build (GitHub):**

1. Make sure `config/` holds your latest downloads and `timetable/TTable.txt`
   is the current timetable.
2. Open the repository on GitHub → **Actions** → **Build timetable** → **Run
   workflow**. Leave *Run the solver* ticked; untick it to only rebuild the
   editor and PDFs. *Seconds the solver may search* defaults to 120.
3. Wait for the green tick, open the run, and download the **timetable**
   artifact. It contains `timetable.html` (the editor loaded with the result),
   `TTable.txt` for TASS, and a `pdf/` folder.
4. The run's log says how many placements stayed put and which lines got new
   periods, then the result of the checks.

If the plan can't be satisfied, the log says why: either two rows in the plan
contradict each other (named), or it tells you which rule it had to drop
(doubles, spread, teacher limits, availability) to find a timetable. Fix the
plan and run again.

## Next term and the end-of-year rollover

The live timetable and settings stay where they are while you build the
next one. Whoever runs the commands (ICT, or the cloud build) starts a
planning folder:

```
python -m tt next-term timetable/TTable.txt "Term 1 2027" -s data/SCourse.txt -r end-of-year
```

You get `next/` holding a copy of the settings with the new term name, a
copy of the timetable to start from, the students moved up a year, and
`rollover-report.txt`. Open the editor built from that folder (or run the
cloud build with **plan: next**) and work there: change the class plan,
construct, fix clashes, print. The current term is untouched.

On the first day of the new term, `python -m tt start-term next` makes it
current and files the old term under `archive/`. Import the new TTable.txt
and SCourse.txt into TASS then.

**What the rollover does.** Year 7 to 11 students move up one year; Year 12
stay (their HSC year runs into Term 3). Use `-r into-term4` between Term 3
and Term 4 instead: Year 12 leave and Year 11 become Year 12. Each student's
classes follow their cohort: the classes almost everyone in the year takes
are swapped for the next year's; cross-year electives (E9/10) are kept;
half-year groups are matched by code. The report lists every class whose
students could not be placed and any year group that has no classes in the
timetable yet (Year 11 after the end-of-year roll, until its courses are
planned). The new Year 7 arrives from TASS, not from this tool.

## Files: loading from TASS, versions, backups, save as

The **Files ▾** menu at the top right needs nothing but the page itself.

| Item | What it does |
| --- | --- |
| Open TTable.txt | Replace the timetable with a file from TASS or Timetabler. |
| Open SCourse.txt | Replace the enrolments. The cloud build has no students; load them here from your computer. They stay in your browser. |
| Add students from a TASS list | A CSV with student code, name (or surname and given names) and year columns. New students join the classes most of their year take; a brand-new year group gets every class of that year, so remove the half-year groups they are not in. Students already on the page are skipped. |
| Save a version… | Name the current state and keep it in the browser. Restore, download or delete it from the list. One is kept for you before every Reset. |
| Download a backup / Open a backup | The whole page's state as a .json file, to keep or to carry to another computer. |
| Save as a copy of this page | A new editor .html with the current state built in: a clean starting point for a what-if, or a dated copy to keep. |

Restoring a version or a backup is an ordinary edit: Undo takes you back.

## Ask Gemini

The **Ask Gemini** tab is a helper for the human-shaped questions; the
checker and the solver still do the exact work. Paste your Google AI Studio
key once (it stays in your browser), ask in plain words, or use the quick
buttons: explain the issues, suggest fixes, who is free.

When Gemini suggests moves, the page tests them first and shows each as ok
or why it can't be done, with the error count before and after. **Apply**
makes them one undoable edit. Student names are not sent unless you tick
**Include student names**.

## Printing and PDFs

The **Print** tab lays out the sheets the school is used to:

| Sheet | Layout |
| --- | --- |
| All years (master) | The master timetable: one A3 page per Main Lesson block, days × years down, periods across, room and teacher beside each class. |
| Year N | The same for one year, as the Class 12 printout. |
| Yard duty roster | Duties down, Mon–Fri across, one sheet per block. |
| Duty sheets (one per teacher) | An A4 page per teacher: their duties per block and day, days away marked. Pick one teacher or all. |

Pick a block or leave *All blocks*, then **Print**. In the browser's print
dialog choose *Save as PDF* for a file. The sheet includes any unsaved edits
and says so in its footer.

The cloud build makes every PDF without a print dialog: `master-timetable.pdf`,
`class-N-timetable.pdf` per year, `yard-duty-roster.pdf` and `duties-CODE.pdf`
per teacher, all in the artifact's `pdf/` folder.

## Troubleshooting and FAQ

| Problem | What to do |
| --- | --- |
| Print does nothing | The page is open inside a preview panel. Save the file and double-click it so it opens in Chrome, Edge or Safari. |
| My edits vanished | Edits live in the browser that made them. A different browser or computer, or pressing **Reset**, starts from the loaded files. Download the files you need before switching. |
| The Student tab is empty in the cloud build | `SCourse.txt` has student names, so it is kept out of GitHub. Load the cloud `TTable.txt` and your own `SCourse.txt` on a computer to see students and student clashes, or wait for the staff portal. |
| A class shows its code instead of a name | Add it to `config/classnames.csv` (code, name, and a block number only if the name changes per block). |
| The solver says INFEASIBLE | Read the named problems first (two classes in one group wanting the same room or teacher). Then loosen: fewer doubles, fewer locks, fewer unavailable periods. The log says which rule it had to drop. |
| A lesson sits in a period someone is away | That's flagged in Issues as *unavailable*. Move the lesson, or fix the Teachers tab if the day-away is wrong. |
| Auto-fill left duties empty | Nobody was free: everyone eligible is away, capped, teaching a clashing period or already on duty. Raise a cap or add a teacher. |
| Two Year 12 classes are in the same group and a student has both | The plan puts them in one line, so they can never be separated. Move one class to another group in the Classes tab. |
| The workflow isn't in the Actions tab | GitHub Actions must be enabled for the repository (Settings → Actions). |

**Where is everything?**

| Thing | Place |
| --- | --- |
| The editor page | `timetable.html` from the cloud artifact, or made locally with `python -m tt report` |
| The plan and settings | `config/` in the repository |
| The current timetable | `timetable/TTable.txt` in the repository |
| Student enrolments | `SCourse.txt`, kept out of the repository |
| This guide | `docs/user-guide.md` in the repository |
