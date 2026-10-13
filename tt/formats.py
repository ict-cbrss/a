"""Read and write the TASS timetable import files (TTable.txt and SCourse.txt).

Both are headerless, unquoted CSV with CRLF line endings, as exported by
Timetabler V10. Writers reproduce the input byte-for-byte so a file can be
loaded, edited and re-imported into TASS unchanged.
"""
from dataclasses import dataclass, astuple, fields
from pathlib import Path

NEWLINE = "\r\n"


@dataclass(frozen=True)
class Lesson:
    """One row of TTable.txt: a class (and one of its teachers) in a slot."""
    day: int            # day of the cycle (1-15 = three-week cycle)
    period: int
    year: str
    class_code: str
    room: str
    teacher: str
    column: int         # grid column (sub-line) the class sits in
    block_start: int    # first grid column of the line/block
    block_end: int      # last grid column of the line/block


@dataclass(frozen=True)
class Enrolment:
    """One row of SCourse.txt: a student in a class."""
    student_id: str
    name: str
    year: str
    class_code: str
    field5: str         # F / M / NS - meaning to confirm
    field6: str         # e.g. Athens / Crete (house?) - meaning to confirm
    field7: str         # always blank in the sample
    form: str           # roll/form group (matches year in the sample)


def _read_rows(path, width):
    rows = []
    text = Path(path).read_text(encoding="utf-8-sig")
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        parts = line.split(",")
        if len(parts) != width:
            raise ValueError(f"{path}:{n}: expected {width} fields, got {len(parts)}")
        rows.append((n, parts))
    return rows


def _types(cls):
    return [f.type for f in fields(cls)]


def _read(path, cls):
    types = _types(cls)
    out = []
    for n, parts in _read_rows(path, len(types)):
        try:
            out.append(cls(*(t(p) if t is int else p for t, p in zip(types, parts))))
        except ValueError as e:
            raise ValueError(f"{path}:{n}: {e}") from None
    return out


def _write(path, records):
    lines = (",".join(str(v) for v in astuple(r)) for r in records)
    Path(path).write_bytes((NEWLINE.join(lines) + NEWLINE).encode("utf-8"))


def read_timetable(path):
    return _read(path, Lesson)


def read_enrolments(path):
    return _read(path, Enrolment)


def write_timetable(path, lessons):
    _write(path, lessons)


def write_enrolments(path, enrolments):
    _write(path, enrolments)
