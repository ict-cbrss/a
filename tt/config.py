"""School configuration: the cycle layout, class names and planned periods.

A config directory holds:
  school.json     blocks (weeks of the cycle), weekday names, period names and
                  times (a period may span several TASS period numbers), and the
                  order years print in.
  classnames.csv  code,name,block - display name for a class code; block is
                  blank for all blocks or a block number (1-based) when the
                  name changes per block, as main lessons do.
  curriculum.csv  Timetabler's Class Information: one row per class per
                  group (line), with the group's periods per cycle, doubles
                  and cross-year group number (mrcg), and the class's
                  teacher, room, seats and student count. Edited in the
                  editor's Classes tab; also used to check that each class
                  is timetabled for its planned number of periods.
  duties.csv      day,block,weekday,slot,duty,teacher - yard duty roster from
                  Timetabler's Yard Duties report. Edited in the editor's
                  Duties tab, which downloads a replacement for this file.
  teachers.csv    per-teacher settings: duty cap (max_duties), no_duties,
                  away_days (semicolon-separated day numbers), max_periods
                  per cycle, min_off_per_day, max_consecutive lessons, and
                  unavailable periods ("day:period;day:period"). Edited in
                  the editor's Teachers tab, which downloads a replacement.
  rooms.csv       code,name,seats,unavailable - rooms with capacity and
                  unavailable periods. Edited in the Rooms tab.
A "slots" value anywhere is "day:period" tokens separated by semicolons.
All are optional; without them the editor shows Day N / PN and class codes.
"""
import csv
import json
from pathlib import Path

DEFAULT = {"school": "", "term": "", "weekdays": [], "blocks": [], "periods": [], "year_order": []}


def load(directory):
    cfg = dict(DEFAULT)
    cfg["names"] = []
    cfg["planned"] = {}
    cfg["classes"] = []
    cfg["duties"] = []
    cfg["teachers"] = []
    cfg["rooms"] = []
    if not directory:
        return cfg
    directory = Path(directory)
    school = directory / "school.json"
    if school.exists():
        cfg.update(json.loads(school.read_text(encoding="utf-8")))
    names = directory / "classnames.csv"
    if names.exists():
        with names.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row["code"]:
                    cfg["names"].append([row["code"], row["name"], int(row["block"]) if row.get("block") else None])
    curriculum = directory / "curriculum.csv"
    if curriculum.exists():
        seen = set()
        with curriculum.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if not row["class_code"]:
                    continue
                cfg["classes"].append({k: (row.get(k) or "") for k in
                                       ("year", "group", "periods", "doubles", "mrcg", "unavailable", "class_code",
                                        "class_name", "students", "teacher", "room", "seats", "class_type")})
                # A class in several groups gets their periods added; a group is counted once per class.
                key = (row["class_code"], row["group"])
                if key in seen:
                    continue
                seen.add(key)
                cfg["planned"][row["class_code"]] = cfg["planned"].get(row["class_code"], 0) + int(row["periods"])
    duties = directory / "duties.csv"
    if duties.exists():
        with duties.open(encoding="utf-8", newline="") as f:
            cfg["duties"] = [[int(r["day"]), r["slot"], r["duty"], r["teacher"]] for r in csv.DictReader(f)]
    teachers = directory / "teachers.csv"
    if teachers.exists():
        with teachers.open(encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                if r["code"]:
                    cfg["teachers"].append({
                        "code": r["code"], "name": r.get("name", ""), "email": r.get("email", ""),
                        "max_duties": int(r["max_duties"]) if r.get("max_duties") else None,
                        "no_duties": (r.get("no_duties") or "").strip().lower() in ("y", "yes", "true", "1"),
                        "away_days": [int(x) for x in (r.get("away_days") or "").split(";") if x.strip()],
                        "max_periods": int(r["max_periods"]) if r.get("max_periods") else None,
                        "min_off_per_day": int(r["min_off_per_day"]) if r.get("min_off_per_day") else None,
                        "max_consecutive": int(r["max_consecutive"]) if r.get("max_consecutive") else None,
                        "unavailable": _slots(r.get("unavailable")),
                    })
    rooms = directory / "rooms.csv"
    if rooms.exists():
        with rooms.open(encoding="utf-8", newline="") as f:
            cfg["rooms"] = [{"code": r["code"], "name": r.get("name", ""), "seats": int(r["seats"]) if r.get("seats") else None,
                             "unavailable": _slots(r.get("unavailable"))}
                            for r in csv.DictReader(f) if r["code"]]
    return cfg


def _slots(text):
    """'1:5;3:2' -> [[1, 5], [3, 2]] (day, period pairs)."""
    return [[int(a), int(b)] for a, b in (x.split(":") for x in (text or "").split(";") if x.strip())]
