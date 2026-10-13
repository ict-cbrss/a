# Timetabler V10 Timetable Development: what we use, and what we don't

Digest of the vendor help for the Timetable Development module (134
articles, read October 2026), kept to the features that matter for a
one-campus school of ~160 high-school students with fixed rooms. Each task
is marked: **have**, **build**, or **skip**.

## How Timetabler models a timetable

- **Roll class** = a year level (7, 8, 9, 10, 12 here).
- **Group** = a *line* within a roll class: one or more classes that run at
  the same time. Lettered A, B, C... Each group has periods per cycle,
  doubles/triples, and a load. Our `curriculum.csv` is this table.
- **MRCG** (multi roll class group) = a group that spans year levels, e.g.
  the 9/10 electives. In `TTable.txt`, column 7 is the group's column and
  columns 8-9 are the span of the MRCG it sits in.
- **Allocation** = placing a group into periods of the cycle ([13A]). The
  master timetable is just all groups of all roll classes allocated.
- **Blocking** ([12A]) = allocating the cross-year and hard groups first so
  lines at different year levels line up; then the rest ([13A]).
- **Edits** ([14]) sit *on top of* allocations: a different teacher or room
  for one lesson. Timetabler warns edits are not reflected back into [7A],
  so they are for rooming and cover, not for moving classes. (Our editor
  edits the exported rows directly, so this split doesn't exist for us.)

## Information stage

| Task | Purpose | Us |
|---|---|---|
| [1A] General | FTE loads, spare fields, sites, class suffix length | **skip** (one site; loads in periods) |
| [1B] Days and Periods per Day, [1C] Period Details | Period names, codes, times, **which pairs count as doubles** (not across a break), period loads | **have** names/times in `school.json`; **build** the doubles list |
| [1D] Allocation Spread Constraints | Spread a group's periods across the cycle: halves of the cycle, not all on one day, 2- and 3-period groups not on consecutive days | **build** as solver rules |
| [1E] Allocation Period Constraints | Per teacher: minimum periods off per day, max consecutive lessons | **build** (teacher settings) |
| [2A/B] Year Levels, Roll Classes | Year groups | **have** |
| [3] Faculties, [8] faculty loads | Departments, auto-staffing by faculty | **skip** |
| [4A] Teachers | Codes, proposed load, availability, yard duty load | **have** code, duty cap, days away; **build** max periods, unavailable periods |
| [4B] Unscheduled Duties, [4C] Meetings | Non-class loads, timetabled meetings | **skip** for now |
| [5] Rooms | Room list with seats and availability | **build** `rooms.csv` (seats already known from Class Details) |
| [6] Student files, [9] Students to classes | Enrolments | **have** (SCourse) |
| [7A] Class Information | The group/class table: periods, doubles, teacher, room per class; add/delete/copy groups | **build** an editor over `curriculum.csv` |
| [7B] Class Staffing, [7C] Class Details, [7D] Class Names | Reports/edits of the same data | covered by 7A editor; names **have** |
| [7E] MRCGs | Cross-year groups | **build** inside the 7A editor (a group spanning years) |
| [7F] Bands, [7G/H] RURs, [7I] Adjacent allocations, [7J/K] colours | Rotations, room pools, forced adjacency, display colours | **skip** (RURs only if rooms become scarce) |
| [10A-C] Yard duty areas, sessions, loads, names | Duty definitions and load per session | **have** areas/sessions; **build** per-session load if needed |
| [11A-C] Tightenings, clash matrix, matching matrix | Diagnostics before construction | **skip**; the solver reports infeasibility instead |

## Process stage

| Task | Purpose | Us |
|---|---|---|
| [12A-I] Blocking | Allocate MRCGs/hard groups first, view teacher/room clashes of the block, check | **build** as part of construction: pin groups to periods, solve the rest |
| [13A] Roll Class Allocations + Lookahead + Auto Allocate | Place each group in periods; lookahead says which cells stay feasible; auto allocate fills the rest; lock existing allocations | **build**: the solver, with "lock these" and a per-cell feasibility view |
| [13B] Groups Unavailable | Periods a group may not use (e.g. Year 12 only after school) | **build** (group settings) |
| [13C/D] Teacher Allocations, On/Off, Teachers Unavailable | Teacher availability per period; view clashes | **build** availability; views **have** |
| [13E/F] Room Allocations, On/Off | Room availability; view clashes | **build** availability; views **have** |
| [13G] Meetings, [13H/I] RURs | Meetings; room pools | **skip** |
| [13J] Check Allocations | Clashes, spread problems, teachers not getting days off | **have** clashes; **build** spread/days-off checks |
| [14] Edit Timetable + teacher/room lists | Change teacher/room/class per lesson, with clash counts per candidate | **have** (our edit dialog); candidate lists with clash counts would be a nice add |
| [15A-D] Yard duties, areas unavailable, staffing (auto), check | Duty builder | **have**; areas-unavailable per teacher **build** if wanted |
| [16A/B] Check Timetable, Check Edits | Problem report | **have** |

## Reports stage

| Task | Us |
|---|---|
| [17A] Master timetables (option: append free teachers / free rooms per period) | **have**; free teachers/rooms **build** (useful for daily cover) |
| [18] Roll class (year) timetables | **have** |
| [19A/B] Individual and daily teacher timetables (with yard duties) | **build** print; view **have** |
| [19E-H] Teacher on/off list, periods, loads, summary | **build** one teacher loads page |
| [20] Room timetables | **build** print; view **have** |
| [21] Class timetables, class frequency | **have** view |
| [22A] Individual student timetables (email to students) | **build** print |
| [23] Class lists (teacher, room, year, all) | **build** |
| [24] Yard duty timetables | **have** |
| [25] Load and file statistics | **build** one statistics page |
| Publish Timetable (Web Daily Organiser) | **skip**; later via the staff portal |
| Quick Export to TASS | **have** |

## Order of work

1. Class Information editor [7A/7E] over `curriculum.csv`, with MRCGs.
2. Rooms [5], teacher periods/limits [4A/1E], group unavailability [13B],
   doubles [1C]. All small config screens.
3. Construction [12/13]: solver with pins/locks and a lookahead view;
   spread rules [1D]; check [13J].
4. Prints: teacher, room, student timetables; class lists; loads and
   statistics; free teachers/rooms on the master.
