"""Construct a timetable: place each group (line) of classes into periods of the cycle.

This is Timetabler's [12]/[13] step done with OR-Tools CP-SAT. The plan comes
from curriculum.csv (groups, periods, doubles, cross-year group numbers,
teachers, rooms); availability and limits from teachers.csv, rooms.csv and
school.json. Locked groups keep the slots they have in the current
TTable.txt; every other group is placed so that nothing clashes, and the
solver prefers the current timetable where it still fits, so a re-solve
moves as little as possible.

Hard rules: a year is in at most one line per slot; a teacher or room is in at
most one line per slot; teacher/room/group unavailable periods and teacher days
away are respected; each group gets its periods and at least its doubles (on
the configured double pairs); no group has more lessons on a day than its
spread allows; teachers get their minimum periods off per day and are not
over their maximum consecutive lessons.
"""
import math
from collections import defaultdict
from dataclasses import dataclass, field

from .formats import Lesson

RULES = ["doubles", "spread", "teacher_limits", "availability"]   # relaxed in this order to diagnose infeasibility


@dataclass
class Line:
    key: str                     # e.g. "12A" or "9E+10E" for a cross-year group
    groups: list                 # [(year, group)]
    periods: int
    doubles: int
    classes: list = field(default_factory=list)   # curriculum rows (one per class per teacher)
    years: set = field(default_factory=set)
    teachers: set = field(default_factory=set)
    rooms: set = field(default_factory=set)
    unavailable: set = field(default_factory=set)  # {(day, period)}
    locked: bool = False
    current: set = field(default_factory=set)      # slots the class codes occupy in the current timetable


def build_lines(cfg, lessons, years=None):
    """Group curriculum rows into lines, joining cross-year groups by their mrcg number."""
    rows = [c for c in cfg["classes"] if (years is None or c["year"] in years)]
    by_group = defaultdict(list)
    for c in rows:
        by_group[(c["year"], c["group"])].append(c)
    # Union groups that share an mrcg number.
    parent = {g: g for g in by_group}

    def find(g):
        while parent[g] != g:
            parent[g] = parent[parent[g]]
            g = parent[g]
        return g
    by_mrcg = defaultdict(list)
    for g, cs in by_group.items():
        if cs[0]["mrcg"]:
            by_mrcg[cs[0]["mrcg"]].append(g)
    for gs in by_mrcg.values():
        for g in gs[1:]:
            parent[find(g)] = find(gs[0])
    members = defaultdict(list)
    for g in by_group:
        members[find(g)].append(g)
    current_slots = defaultdict(set)
    for l in lessons:
        current_slots[l.class_code].add((l.day, l.period))
    usual = usual_rooms(lessons)
    lines = []
    for root, gs in members.items():
        gs.sort()
        first = by_group[gs[0]][0]
        line = Line(key="+".join(y + g[len(y):] for y, g in gs), groups=gs,
                    periods=int(first["periods"] or 0), doubles=int(first["doubles"] or 0))
        for g in gs:
            for c in by_group[g]:
                line.classes.append(c)
                line.years.add(c["year"])
                if c["teacher"]:
                    line.teachers.add(c["teacher"])
                for d, p in _slots(c.get("unavailable")):
                    line.unavailable.add((d, p))
                line.current |= current_slots.get(c["class_code"], set())
                if (c.get("locked") or "").strip().lower() in ("y", "yes", "true", "1"):
                    line.locked = True
        assign_rooms(line, usual)
        line.rooms = {c["_room"] for c in line.classes if c["_room"]}
        lines.append(line)
    lines.sort(key=lambda x: x.key)
    return lines


def _slots(text):
    return [tuple(int(v) for v in x.split(":")) for x in (text or "").split(";") if x.strip()]


def check_plan(lines):
    """Problems that make a plan impossible before solving."""
    problems = []
    for line in lines:
        seen_rooms = defaultdict(set)
        for c in line.classes:
            if c.get("_room"):
                seen_rooms[c["_room"]].add(c["class_code"])
            else:
                problems.append(f"{line.key}: {c['class_code']} has no room in the plan and none in the timetable")
        for room, codes in seen_rooms.items():
            if len(codes) > 1:
                problems.append(f"{line.key}: classes {', '.join(sorted(codes))} all want room {room} at the same time")
        seen_t = defaultdict(set)
        for c in line.classes:
            if c["teacher"]:
                seen_t[c["teacher"]].add(c["class_code"])
        for t, codes in seen_t.items():
            if len(codes) > 1:
                problems.append(f"{line.key}: {t} teaches {', '.join(sorted(codes))}, which run at the same time")
        if line.locked and len(line.current) != line.periods:
            problems.append(f"{line.key} is locked but has {len(line.current)} periods in the timetable, plan says {line.periods}")
    return problems


def solve(cfg, lessons, days, periods, years=None, time_limit=60, relax=(), log=print):
    """Return (status, new_lessons, report). status is 'OPTIMAL', 'FEASIBLE' or 'INFEASIBLE'."""
    from ortools.sat.python import cp_model

    lines = build_lines(cfg, lessons, years)
    problems = check_plan(lines)
    if problems:
        return "INFEASIBLE", [], {"problems": problems, "lines": lines}
    slots = [(d, p) for d in days for p in periods]
    double_pairs = [tuple(x) for x in cfg.get("doubles", []) if tuple(x)[0] in periods and tuple(x)[1] in periods]
    teachers = {t["code"]: t for t in cfg.get("teachers", [])}
    rooms = {r["code"]: r for r in cfg.get("rooms", [])}
    relax = set(relax)

    m = cp_model.CpModel()
    x = {}   # (line index, slot) -> bool
    for i, line in enumerate(lines):
        for s in slots:
            x[i, s] = m.NewBoolVar(f"x{i}_{s[0]}_{s[1]}")
        m.Add(sum(x[i, s] for s in slots) == line.periods)
        if line.locked:
            for s in slots:
                m.Add(x[i, s] == (1 if s in line.current else 0))
        if "availability" not in relax:
            restricted = {int(k): set(v) for k, v in cfg.get("restricted_periods", {}).items()}
            for s in slots:
                blocked = s in line.unavailable
                # A period reserved for certain years (e.g. after school for Year 12 only).
                if s[1] in restricted and not line.years <= restricted[s[1]]:
                    blocked = True
                for t in line.teachers:
                    ts = teachers.get(t, {})
                    if s[0] in ts.get("away_days", []) or list(s) in ts.get("unavailable", []):
                        blocked = True
                for r in line.rooms:
                    if list(s) in rooms.get(r, {}).get("unavailable", []):
                        blocked = True
                if blocked and not line.locked:
                    m.Add(x[i, s] == 0)
        if line.doubles and "doubles" not in relax:
            ys = []
            for d in days:
                for a, b in double_pairs:
                    y = m.NewBoolVar(f"y{i}_{d}_{a}")
                    m.AddImplication(y, x[i, (d, a)])
                    m.AddImplication(y, x[i, (d, b)])
                    ys.append(y)
            m.Add(sum(ys) >= line.doubles)
        if "spread" not in relax and not line.locked:
            per_day = max(math.ceil(line.periods / len(days)), 2)
            for d in days:
                m.Add(sum(x[i, (d, p)] for p in periods) <= per_day)

    # One line per year per slot; one line per teacher per slot; one line per room per slot.
    for s in slots:
        for year in {y for line in lines for y in line.years}:
            m.Add(sum(x[i, s] for i, line in enumerate(lines) if year in line.years) <= 1)
        for t in {t for line in lines for t in line.teachers}:
            m.Add(sum(x[i, s] for i, line in enumerate(lines) if t in line.teachers) <= 1)
        for r in {r for line in lines for r in line.rooms}:
            m.Add(sum(x[i, s] for i, line in enumerate(lines) if r in line.rooms) <= 1)

    if "teacher_limits" not in relax:
        for t, ts in teachers.items():
            mine = [i for i, line in enumerate(lines) if t in line.teachers]
            if not mine:
                continue
            for d in days:
                if ts.get("min_off_per_day") is not None:
                    m.Add(sum(x[i, (d, p)] for i in mine for p in periods) <= len(periods) - ts["min_off_per_day"])
                if ts.get("max_consecutive") is not None:
                    k = ts["max_consecutive"]
                    for j in range(len(periods) - k):
                        m.Add(sum(x[i, (d, p)] for i in mine for p in periods[j:j + k + 1]) <= k)

    # Prefer the current timetable: reward keeping a line where it already is.
    m.Maximize(sum(x[i, s] for i, line in enumerate(lines) for s in line.current if (i, s) in x))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_workers = 8
    status = solver.Solve(m)
    name = solver.StatusName(status)
    if name not in ("OPTIMAL", "FEASIBLE"):
        return "INFEASIBLE", [], {"problems": [], "lines": lines, "status": name}

    placed = {i: {s for s in slots if solver.Value(x[i, s])} for i in range(len(lines))}
    new_lessons = _to_lessons(lines, placed, lessons)
    moved = []
    for i, line in enumerate(lines):
        new_slots = sorted(placed[i] - line.current)
        if new_slots:
            moved.append((line.key, len(placed[i] & line.current), new_slots))
    return name, new_lessons, {"problems": [], "lines": lines, "moved": moved, "status": name,
                               "placed": {line.key: sorted(placed[i]) for i, line in enumerate(lines)},
                               "kept": sum(len(placed[i] & l.current) for i, l in enumerate(lines))}


def usual_rooms(old_lessons):
    """Rooms each class uses in the current timetable, most used first, for plan rows with no room."""
    count = defaultdict(lambda: defaultdict(int))
    for l in old_lessons:
        if l.room:
            count[l.class_code][l.room] += 1
    return {code: sorted(rooms, key=lambda r: -rooms[r]) for code, rooms in count.items()}


def assign_rooms(line, usual):
    """Give every class in a line a room: the plan's, else its usual room not already taken in this line."""
    taken = {c["room"] for c in line.classes if c["room"]}
    for c in line.classes:
        c["_room"] = c["room"]
        if c["_room"]:
            continue
        for r in usual.get(c["class_code"], []):
            if r not in taken:
                c["_room"] = r
                taken.add(r)
                break
        # The same class listed twice (two teachers) shares the room.
        if not c["_room"]:
            same = next((o for o in line.classes if o is not c and o["class_code"] == c["class_code"] and o.get("_room")), None)
            if same:
                c["_room"] = same["_room"]


def _to_lessons(lines, placed, old_lessons):
    """Expand line placements into TTable rows, keeping TTable's grid columns from the old rows where known."""
    cols = {}
    for l in old_lessons:
        cols.setdefault((l.class_code, l.teacher), (l.column, l.block_start, l.block_end))
        cols.setdefault(l.class_code, (l.column, l.block_start, l.block_end))
    out = []
    for i, line in enumerate(lines):
        for d, p in sorted(placed[i]):
            for n, c in enumerate(line.classes, 1):
                col = cols.get((c["class_code"], c["teacher"])) or cols.get(c["class_code"]) or (n, 1, len(line.classes))
                out.append(Lesson(d, p, c["year"], c["class_code"], c.get("_room") or c["room"], c["teacher"], *col))
    out.sort(key=lambda l: (l.day, l.period, -int(l.year) if l.year.isdigit() else 0, l.column))
    return out


def solve_with_diagnosis(cfg, lessons, days, periods, years=None, time_limit=60, log=print):
    """Solve; if infeasible, relax rules one family at a time to say which one is the problem."""
    status, new, report = solve(cfg, lessons, days, periods, years, time_limit)
    if status != "INFEASIBLE" or report["problems"]:
        return status, new, report
    relaxed = []
    for rule in RULES:
        relaxed.append(rule)
        log(f"infeasible; retrying without {', '.join(relaxed)} ...")
        status, new, report2 = solve(cfg, lessons, days, periods, years, time_limit, relax=relaxed)
        if status != "INFEASIBLE":
            report2["relaxed"] = list(relaxed)
            return status, new, report2
    report["relaxed"] = list(relaxed)
    return "INFEASIBLE", [], report
