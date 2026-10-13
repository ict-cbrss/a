"""Year rollover and next-term planning.

Rollover moves students into their next year group. Class codes carry the
year (C07E_1 is Year 7 English), so a Year 7 student's enrolments become the
matching Year 8 classes where those exist in the timetable; cross-year
classes (E9/10Ar_1) are kept while the student's new year is still one the
class takes. Enrolments with no matching class are dropped and listed, so
the coordinator knows which students still need classes.

Two moments in the school year (NSW: Year 12 starts in Term 4):
  end-of-year   Term 4 -> Term 1: Years 7-11 move up one; Year 12 stays
                (their HSC year runs to Term 3); the new Year 7 arrives
                from TASS and is not in the files yet.
  into-term4    Term 3 -> Term 4: Year 12 leaves; Year 11 becomes Year 12.

A "next term" folder holds a copy of the current timetable and settings to
plan the coming term in, while the current ones stay live. start_term makes
it current and archives what it replaced.
"""
import csv
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from . import formats

PRESETS = {"end-of-year": ([7, 8, 9, 10, 11], []), "into-term4": ([11], [12]), "none": ([], [])}
_RANGE = re.compile(r"(\d{1,2})/(\d{1,2})")


def class_years(code, lessons, classes=()):
    """Years a class takes: from its timetable rows, the plan, and a 9/10 style range in the code."""
    years = {int(l.year) for l in lessons if l.class_code == code and l.year.isdigit()}
    years |= {int(c["year"]) for c in classes if c.get("class_code") == code and c["year"].isdigit()}
    for a, b in _RANGE.findall(code):
        years |= set(range(int(a), int(b) + 1))
    return years


def advance_code(code, old, new):
    """C07E_1 -> C08E_1 for 7 -> 8; the year token keeps its zero padding."""
    for pad in (f"{old:02d}", str(old)):
        token = re.compile(rf"(?<![\d/]){re.escape(pad)}(?![\d/])")
        if token.search(code):
            return token.sub(f"{new:02d}" if len(pad) == 2 else str(new), code, count=1)
    return code


def roll_enrolments(enrolments, lessons, classes=(), advance=(), leave=(), core=0.75):
    """Return (new enrolments, report).

    advance: years that move up one; leave: years whose students leave. A class
    taken by at least `core` of a year's students is a core class: students
    moving up swap their year's core classes for the next year's. Other
    (elective) classes are kept while the class takes the new year, else
    mapped by code (C07Sp_1 -> C08Sp_1) when that class exists, else dropped
    and reported.
    """
    advance, leave = {int(y) for y in advance}, {int(y) for y in leave}
    known = {l.class_code for l in lessons} | {c["class_code"] for c in classes if c.get("class_code")}
    years_of = {code: class_years(code, lessons, classes) for code in known}
    timetabled = {y for l in lessons for y in years_of[l.class_code]}   # years with classes in the timetable
    rows = {}
    for e in enrolments:
        rows.setdefault(e.student_id, []).append(e)
    cohort, in_class = {}, {}
    for sid, es in rows.items():
        y = _year(es[0])
        cohort.setdefault(y, set()).add(sid)
        for e in es:
            in_class.setdefault(e.class_code, set()).add(sid)

    def core_of(y):
        n = len(cohort.get(y, ()))
        return {c for c, ss in in_class.items() if n and len(years_of.get(c, ())) < 2 and len(ss & cohort[y]) >= core * n}

    out, unplaced = [], {}
    moved, left = Counter(), 0
    for sid, es in rows.items():
        y = _year(es[0])
        if y in leave:
            left += 1
            continue
        if y not in advance:
            out.extend(es)
            continue
        new = y + 1
        moved[(y, new)] += 1
        old_core, new_core = core_of(y), core_of(new)
        codes = []
        for e in es:
            if new in years_of.get(e.class_code, ()):   # cross-year class (E9/10Ar_1) still takes them
                codes.append(e.class_code)
                continue
            if e.class_code in old_core:
                continue
            code = advance_code(e.class_code, y, new)
            if code not in known:   # C07VAB_1 -> C08VAB_2: same class, different suffix
                stem = re.sub(r"_\d+$", "_", code)
                code = next((c for c in sorted(known) if c.startswith(stem) and new in years_of[c]), code)
            if code in known and new in years_of[code]:
                codes.append(code)
            else:
                unplaced.setdefault((y, new, e.class_code), []).append(f"{sid} {e.name}")
        codes += sorted(new_core - set(codes))
        first = es[0]
        form = str(new) if first.form == str(y) else advance_code(first.form, y, new)
        seen = set()
        for code in codes:
            if code not in seen:
                seen.add(code)
                out.append(formats.Enrolment(sid, first.name, str(new), code, first.field5, first.field6, first.field7, form))
    report = {
        "moved": {f"{a}->{b}": n for (a, b), n in sorted(moved.items())},
        "students_moved": sum(moved.values()),
        "left": left,
        "kept": len(out),
        "unplaced": [(y, new, code, names) for (y, new, code), names in sorted(unplaced.items())],
        "years_without_classes": sorted({b for (a, b) in moved} - timetabled),
        "planned_classes": {y: sum(1 for ys in years_of.values() if y in ys) for y in sorted({b for (a, b) in moved} - timetabled)},
    }
    return out, report


def _year(e):
    return int(e.year) if e.year.isdigit() else None


def report_text(report):
    lines = [f"Students moved up: {report['students_moved']} ({', '.join(f'{k}: {v}' for k, v in report['moved'].items()) or 'none'})",
             f"Students who left: {report['left']}", f"Enrolments written: {report['kept']}"]
    for y in report["years_without_classes"]:
        n = sum(len(names) for _, new, _, names in report["unplaced"] if new == y)
        students = len({s for _, new, _, names in report["unplaced"] if new == y for s in names})
        planned = report.get("planned_classes", {}).get(y, 0)
        lines.append(f"Year {y} is not in the timetable yet ({planned} classes in the plan, none timetabled): "
                     f"its {students} students ({n} enrolments) need classes once it is built.")
    missing = [u for u in report["unplaced"] if u[1] not in report["years_without_classes"]]
    if missing:
        lines.append(f"Classes with no Year-up equivalent ({len(missing)}); these students still need a class:")
        for y, new, code, names in missing:
            lines.append(f"  {code} (Year {y} -> {new}, {len(names)} students): {', '.join(names)}")
    return "\n".join(lines) + "\n"


def refresh_student_counts(curriculum, enrolments):
    """Rewrite curriculum.csv's students column from the enrolments."""
    counts = Counter(e.class_code for e in enrolments)
    with Path(curriculum).open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows, fields = list(reader), reader.fieldnames
    if "students" not in fields:
        return
    for r in rows:
        if r.get("class_code"):
            r["students"] = str(counts.get(r["class_code"], 0))
    with Path(curriculum).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fields)
        w.writeheader()
        w.writerows(rows)


def new_term(dest, term, ttable, config_dir, scourse=None, rollover="none"):
    """Create a planning folder: config/ copy with the new term name, TTable.txt, rolled SCourse.txt and a report."""
    dest = Path(dest)
    if dest.exists() and any(dest.iterdir()):
        raise FileExistsError(f"{dest} already exists; remove it or choose another folder")
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(config_dir, dest / "config", dirs_exist_ok=True)
    school = dest / "config" / "school.json"
    data = json.loads(school.read_text(encoding="utf-8")) if school.exists() else {}
    data["term"] = term
    school.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    lessons = formats.read_timetable(ttable)
    formats.write_timetable(dest / "TTable.txt", lessons)
    report = None
    if scourse:
        from . import config as cfgmod
        advance, leave = PRESETS[rollover]
        enrolments = formats.read_enrolments(scourse)
        rolled, report = roll_enrolments(enrolments, lessons, cfgmod.load(config_dir)["classes"], advance, leave)
        formats.write_enrolments(dest / "SCourse.txt", rolled)
        if rollover != "none":
            (dest / "rollover-report.txt").write_text(report_text(report), encoding="utf-8")
            if (dest / "config" / "curriculum.csv").exists():
                refresh_student_counts(dest / "config" / "curriculum.csv", rolled)
    return report


def start_term(src, root="."):
    """Make a planning folder the current term: archive timetable/TTable.txt and config/, then replace them."""
    src, root = Path(src), Path(root)
    if not (src / "TTable.txt").exists() or not (src / "config").is_dir():
        raise FileNotFoundError(f"{src} needs TTable.txt and config/ (made by: python -m tt next-term)")
    old_school = root / "config" / "school.json"
    old_term = json.loads(old_school.read_text(encoding="utf-8")).get("term", "") if old_school.exists() else ""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", old_term).strip("-").lower() or "previous"
    archive = root / "archive" / slug
    if (root / "timetable" / "TTable.txt").exists() or (root / "config").is_dir():
        archive.mkdir(parents=True, exist_ok=True)
        if (root / "timetable" / "TTable.txt").exists():
            shutil.copy2(root / "timetable" / "TTable.txt", archive / "TTable.txt")
        if (root / "config").is_dir():
            shutil.copytree(root / "config", archive / "config", dirs_exist_ok=True)
    (root / "timetable").mkdir(exist_ok=True)
    shutil.copy2(src / "TTable.txt", root / "timetable" / "TTable.txt")
    shutil.rmtree(root / "config", ignore_errors=True)
    shutil.copytree(src / "config", root / "config")
    return archive
