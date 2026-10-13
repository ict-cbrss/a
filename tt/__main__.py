"""Command line entry point: python -m tt <command> ..."""
import argparse
import sys
from collections import Counter
from pathlib import Path

from . import config, formats, report, validate


def _load(args):
    return formats.read_timetable(args.ttable), formats.read_enrolments(args.scourse)


def cmd_check(args):
    lessons, enrolments = _load(args)
    issues = validate.check(lessons, enrolments, config.load(args.config)["planned"])
    print(f"{len(lessons)} timetable rows, {len({l.class_code for l in lessons})} classes, "
          f"{len({e.student_id for e in enrolments})} students")
    for kind, n in sorted(Counter(i.kind for i in issues).items()):
        print(f"  {kind}: {n}")
    for i in issues:
        where = f"Day {i.day} P{i.period}: " if i.day else ""
        print(f"[{i.severity}] {where}{i.message}")
    return 1 if any(i.severity == "error" for i in issues) else 0


def cmd_report(args):
    lessons, enrolments = _load(args)
    cfg = config.load(args.config)
    issues = validate.check(lessons, enrolments, cfg["planned"])
    Path(args.out).write_text(report.build(lessons, enrolments, issues, cfg), encoding="utf-8")
    print(f"Wrote {args.out}")
    return 0


def cmd_export(args):
    lessons, enrolments = _load(args)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    formats.write_timetable(out / "TTable.txt", lessons)
    formats.write_enrolments(out / "SCourse.txt", enrolments)
    print(f"Wrote {out / 'TTable.txt'} and {out / 'SCourse.txt'}")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="tt", description="TASS timetable file tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in [("check", cmd_check, "list clashes and data problems"),
                            ("report", cmd_report, "write an HTML timetable viewer"),
                            ("export", cmd_export, "write TASS import files")]:
        s = sub.add_parser(name, help=help_)
        s.add_argument("ttable", help="TTable.txt")
        s.add_argument("scourse", help="SCourse.txt")
        if name in ("check", "report"):
            s.add_argument("-c", "--config", default="config" if Path("config").is_dir() else None,
                           help="folder with school.json, classnames.csv, curriculum.csv (default: ./config if present)")
        if name == "report":
            s.add_argument("-o", "--out", default="timetable.html")
        if name == "export":
            s.add_argument("-o", "--out-dir", default="out")
        s.set_defaults(fn=fn)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
