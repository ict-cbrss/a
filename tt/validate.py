"""Clash and consistency checks over a timetable and its enrolments."""
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Issue:
    severity: str   # "error" or "warning"
    kind: str
    day: int | None
    period: int | None
    message: str


def _slot_clashes(lessons, key, kind, label):
    """Two different classes sharing a teacher or room in the same slot."""
    by_slot = defaultdict(set)
    for l in lessons:
        by_slot[(l.day, l.period, getattr(l, key))].add(l.class_code)
    return [
        Issue("error", kind, d, p, f"{label} {who} has {', '.join(sorted(cs))}")
        for (d, p, who), cs in sorted(by_slot.items())
        if len(cs) > 1
    ]


def check(lessons, enrolments, planned=None):
    """planned: optional {class_code: periods per cycle} from the curriculum file."""
    issues = []
    issues += _slot_clashes(lessons, "teacher", "teacher-clash", "Teacher")
    issues += _slot_clashes(lessons, "room", "room-clash", "Room")

    seen = set()
    for l in lessons:
        if l in seen:
            issues.append(Issue("warning", "duplicate-row", l.day, l.period,
                                f"Duplicate row for {l.class_code} / {l.teacher}"))
        seen.add(l)

    slots = defaultdict(set)
    for l in lessons:
        slots[l.class_code].add((l.day, l.period))

    classes_by_student = defaultdict(set)
    names = {}
    for e in enrolments:
        classes_by_student[e.student_id].add(e.class_code)
        names[e.student_id] = e.name
        if e.class_code not in slots:
            issues.append(Issue("error", "unknown-class", None, None,
                                f"{e.name} ({e.student_id}) enrolled in {e.class_code}, "
                                "which is not in the timetable"))

    for sid, classes in sorted(classes_by_student.items()):
        by_slot = defaultdict(set)
        for c in classes:
            for s in slots.get(c, ()):
                by_slot[s].add(c)
        for (d, p), cs in sorted(by_slot.items()):
            if len(cs) > 1:
                issues.append(Issue("error", "student-clash", d, p,
                                    f"{names[sid]} ({sid}) has {', '.join(sorted(cs))}"))

    enrolled = {e.class_code for e in enrolments}
    for c in sorted(set(slots) - enrolled):
        issues.append(Issue("warning", "empty-class", None, None,
                            f"{c} is timetabled but has no students"))

    for c, want in sorted((planned or {}).items()):
        got = len(slots.get(c, ()))
        if got and got != want:
            issues.append(Issue("warning", "period-count", None, None,
                                f"{c} is timetabled for {got} periods, curriculum says {want}"))
    return issues
