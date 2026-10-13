"""Build a single self-contained HTML viewer for a timetable."""
import json
from collections import Counter
from dataclasses import asdict, astuple, fields
from pathlib import Path

from . import formats

TEMPLATE = Path(__file__).with_name("viewer.html")


def build(lessons, enrolments, issues):
    data = {
        "lessons": [asdict(l) for l in lessons],
        "students": sorted({(e.student_id, e.name, e.year) for e in enrolments},
                           key=lambda s: (s[2].zfill(3), s[1])),
        # Full rows in file order, so the page can re-export the import files.
        "lesson_fields": [f.name for f in fields(formats.Lesson)],
        "enrolment_fields": [f.name for f in fields(formats.Enrolment)],
        "enrolments": [astuple(e) for e in enrolments],
        "issues": [asdict(i) for i in issues],
        "load": Counter(l.teacher for l in lessons),
    }
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", payload)
