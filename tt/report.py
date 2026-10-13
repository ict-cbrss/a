"""Build a single self-contained HTML viewer for a timetable."""
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

TEMPLATE = Path(__file__).with_name("viewer.html")


def build(lessons, enrolments, issues):
    data = {
        "lessons": [asdict(l) for l in lessons],
        "students": sorted({(e.student_id, e.name, e.year) for e in enrolments},
                           key=lambda s: (s[2].zfill(3), s[1])),
        "enrolments": [[e.student_id, e.class_code] for e in enrolments],
        "issues": [asdict(i) for i in issues],
        "load": Counter(l.teacher for l in lessons),
    }
    payload = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", payload)
