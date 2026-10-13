"""School configuration: the cycle layout, class names and planned periods.

A config directory holds:
  school.json     blocks (weeks of the cycle), weekday names, period names and
                  times (a period may span several TASS period numbers), and the
                  order years print in.
  classnames.csv  code,name,block - display name for a class code; block is
                  blank for all blocks or a block number (1-based) when the
                  name changes per block, as main lessons do.
  curriculum.csv  Timetabler's Class Details report: one row per class per
                  line group, with periods per cycle. Used to check that each
                  class is timetabled for its planned number of periods.
  duties.csv      day,block,weekday,slot,duty,teacher - yard duty roster from
                  Timetabler's Yard Duties report. Edited in the editor's
                  Duties tab, which downloads a replacement for this file.
  teachers.csv    code,name,email,max_duties,no_duties,away_days - duty
                  settings per teacher: a cap on duties per cycle, whether
                  they do duties at all, and the cycle days they are away
                  (semicolon-separated day numbers). Edited in the editor's
                  Teachers tab, which downloads a replacement for this file.
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
    cfg["duties"] = []
    cfg["teachers"] = []
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
                # A class in several groups gets their periods added; a group is counted once per class.
                key = (row["class_code"], row["group"])
                if key in seen or not row["class_code"]:
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
                    })
    return cfg
