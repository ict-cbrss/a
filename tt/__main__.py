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


def cmd_pdf(args):
    """Write the print sheets as PDFs using a headless browser (needs playwright + Chromium)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("pip install playwright   (and set PLAYWRIGHT_CHROMIUM or run: playwright install chromium)", file=sys.stderr)
        return 2
    import os
    import tempfile
    lessons, enrolments = _load(args)
    cfg = config.load(args.config)
    html = report.build(lessons, enrolments, validate.check(lessons, enrolments, cfg["planned"]), cfg)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    with tempfile.TemporaryDirectory() as tmp:
        page_file = Path(tmp) / "timetable.html"
        page_file.write_text(html, encoding="utf-8")
        with sync_playwright() as p:
            exe = os.environ.get("PLAYWRIGHT_CHROMIUM")
            browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
            page = browser.new_page()
            page.goto(page_file.as_uri())
            page.click("#views button[data-v=Print]")

            def save(name, year, block="", teacher=None):
                # The print stylesheet hides the controls, so pick the sheet in screen media first.
                page.emulate_media(media="screen")
                page.select_option("#print-year", year)
                page.select_option("#print-block", block)
                if teacher is not None:
                    page.select_option("#print-teacher", teacher)
                page.emulate_media(media="print")
                path = out / name
                page.pdf(path=str(path), prefer_css_page_size=True)
                written.append(path)

            what = set(args.what)
            if "master" in what:
                save("master-timetable.pdf", "")
            if "years" in what:
                for y in page.eval_on_selector_all("#print-year option", "os => os.map(o => o.value).filter(v => /^\\d+$/.test(v))"):
                    save(f"class-{y}-timetable.pdf", y)
            if "roster" in what and page.locator("#print-year option[value=duties]").count():
                save("yard-duty-roster.pdf", "duties")
            if "dutysheets" in what and page.locator("#print-year option[value=dutysheets]").count():
                page.emulate_media(media="screen")
                page.select_option("#print-year", "dutysheets")
                for t in page.eval_on_selector_all("#print-teacher option", "os => os.map(o => o.value).filter(Boolean)"):
                    save(f"duties-{t.replace('/', '_')}.pdf", "dutysheets", teacher=t)
            browser.close()
    for path in written:
        print(f"Wrote {path}")
    return 0


def cmd_solve(args):
    """Place every unlocked group into the cycle (needs ortools)."""
    try:
        import ortools  # noqa: F401
    except ImportError:
        print("pip install ortools", file=sys.stderr)
        return 2
    from . import solve as solver
    lessons, enrolments = _load(args)
    cfg = config.load(args.config)
    days = sorted({d for b in cfg["blocks"] for d in b["days"]} | {l.day for l in lessons})
    periods = sorted(cfg.get("teaching_periods") or {l.period for l in lessons} or {i for p in cfg["periods"] for i in p["ids"]})
    years = set(args.years.split(",")) if args.years else ({l.year for l in lessons} or None)
    print(f"{len(days)} days x {len(periods)} periods, years {','.join(sorted(years, key=lambda y: -int(y))) if years else 'all'}, "
          f"time limit {args.time}s")
    status, new, report = solver.solve_with_diagnosis(cfg, lessons, days, periods, years, args.time)
    for p in report.get("problems", []):
        print(f"[plan] {p}")
    locked = [l.key for l in report["lines"] if l.locked]
    print(f"{len(report['lines'])} lines ({len(locked)} locked), status {status}" + (f", relaxed: {', '.join(report['relaxed'])}" if report.get("relaxed") else ""))
    if status == "INFEASIBLE":
        print("No timetable satisfies the plan. Fix the problems above or loosen the constraints.")
        return 1
    total = sum(l.periods for l in report["lines"])
    print(f"{report['kept']} of {total} placements are where the current timetable has them; {len(report['moved'])} lines got new slots:")
    for key, kept, new_slots in report["moved"]:
        print(f"  {key}: kept {kept}, new {', '.join(f'{d}:{p}' for d, p in new_slots)}")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    formats.write_timetable(out / "TTable.txt", new)
    formats.write_enrolments(out / "SCourse.txt", enrolments)
    issues = validate.check(new, enrolments, cfg["planned"])
    errs = [i for i in issues if i.severity == "error"]
    print(f"Wrote {out / 'TTable.txt'} ({len(new)} rows) and SCourse.txt; check: {len(errs)} errors, {len(issues) - len(errs)} warnings")
    for i in errs[:20]:
        print(f"  [error] {i.message}")
    return 0


def cmd_rollover(args):
    """Move students into their next year group; write SCourse.txt and a report."""
    lessons, enrolments = _load(args)
    from . import rollover
    advance = [int(y) for y in args.advance.split(",")] if args.advance else sorted({int(l.year) for l in lessons if l.year.isdigit()})[:-1]
    leave = [int(y) for y in args.leave.split(",")] if args.leave else []
    rolled, rep = rollover.roll_enrolments(enrolments, lessons, config.load(args.config)["classes"], advance, leave)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    formats.write_enrolments(out / "SCourse.txt", rolled)
    (out / "rollover-report.txt").write_text(rollover.report_text(rep), encoding="utf-8")
    print(rollover.report_text(rep), end="")
    print(f"Wrote {out / 'SCourse.txt'} and rollover-report.txt")
    return 0


def cmd_next_term(args):
    """Start a planning folder for the coming term next to the live one."""
    from . import rollover
    if not args.config:
        print("No config folder: pass -c config", file=sys.stderr)
        return 2
    rep = rollover.new_term(args.out_dir, args.term, args.ttable, args.config, args.students, args.rollover)
    print(f"Created {args.out_dir}/ for {args.term}: config/, TTable.txt" + (", SCourse.txt" if args.students else ""))
    if rep and args.rollover != "none":
        print(rollover.report_text(rep), end="")
    print(f"Plan there: python -m tt report {args.out_dir}/TTable.txt {args.out_dir}/SCourse.txt -c {args.out_dir}/config -o {args.out_dir}/timetable.html")
    print(f"When the term starts: python -m tt start-term {args.out_dir}")
    return 0


def cmd_start_term(args):
    from . import rollover
    archive = rollover.start_term(args.folder, args.root)
    print(f"{args.folder}/ is now the current term: timetable/TTable.txt and config/ replaced; the old ones are in {archive}/")
    print(f"Import {args.folder}/TTable.txt and {args.folder}/SCourse.txt into TASS; SCourse.txt stays out of the repo.")
    return 0


def cmd_backup(args):
    from . import backup
    path = backup.backup(args.out_dir, args.ttable, args.scourse, args.config)
    print(f"Wrote {path}")
    return 0


def cmd_restore(args):
    from . import backup
    files = backup.restore(args.zip, args.out_dir)
    print(f"Restored {len(files)} files into {args.out_dir}/: " + ", ".join(sorted({str(f.relative_to(args.out_dir)).split('/')[0] for f in files})))
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="tt", description="TASS timetable file tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in [("check", cmd_check, "list clashes and data problems"),
                            ("report", cmd_report, "write an HTML timetable viewer"),
                            ("export", cmd_export, "write TASS import files"),
                            ("pdf", cmd_pdf, "write the print sheets as PDFs (needs playwright)"),
                            ("solve", cmd_solve, "construct a timetable from the plan (needs ortools)"),
                            ("rollover", cmd_rollover, "move students up a year group (end of year, or Year 11 -> 12 for Term 4)"),
                            ("next-term", cmd_next_term, "start a planning folder for next term from the current timetable"),
                            ("start-term", cmd_start_term, "make a planning folder the current term (archives the old one)"),
                            ("backup", cmd_backup, "zip the timetable, student file and config into one backup"),
                            ("restore", cmd_restore, "unpack a backup zip into a folder")]:
        s = sub.add_parser(name, help=help_)
        if name == "restore":
            s.add_argument("zip", help="a backup zip")
            s.add_argument("-o", "--out-dir", default="restored")
            s.set_defaults(fn=fn)
            continue
        if name == "start-term":
            s.add_argument("folder", nargs="?", default="next", help="planning folder (default: next)")
            s.add_argument("--root", default=".", help="repository folder holding timetable/ and config/")
            s.set_defaults(fn=fn)
            continue
        s.add_argument("ttable", help="TTable.txt" + (" (the current timetable)" if name == "next-term" else ""))
        if name == "next-term":
            s.add_argument("term", help='name of the term, e.g. "Term 1 2027"')
            s.add_argument("-s", "--students", help="current SCourse.txt (optional; rolled over into the folder, never committed)")
            s.add_argument("-r", "--rollover", default="none", choices=["none", "end-of-year", "into-term4"],
                           help="end-of-year: Years 7-11 move up, 12 stays; into-term4: Year 12 leaves, 11 becomes 12")
            s.add_argument("-o", "--out-dir", default="next")
        else:
            s.add_argument("scourse", help="SCourse.txt")
        if name == "backup":
            s.add_argument("-o", "--out-dir", default="backups")
        if name == "rollover":
            s.add_argument("-o", "--out-dir", default="rolled")
            s.add_argument("--advance", help="years that move up one (default: every year but the highest)")
            s.add_argument("--leave", help="years whose students leave, e.g. 12")
        if name in ("check", "report", "pdf", "solve", "rollover", "next-term", "backup"):
            s.add_argument("-c", "--config", default="config" if Path("config").is_dir() else None,
                           help="folder with school.json, classnames.csv, curriculum.csv (default: ./config if present)")
        if name == "report":
            s.add_argument("-o", "--out", default="timetable.html")
        if name == "export":
            s.add_argument("-o", "--out-dir", default="out")
        if name == "solve":
            s.add_argument("-o", "--out-dir", default="solved")
            s.add_argument("-t", "--time", type=int, default=60, help="seconds to search (default 60)")
            s.add_argument("-y", "--years", help="comma-separated years to build (default: years in TTable.txt)")
        if name == "pdf":
            s.add_argument("-o", "--out-dir", default="pdf")
            s.add_argument("-w", "--what", nargs="+", default=["master", "years", "roster", "dutysheets"],
                           choices=["master", "years", "roster", "dutysheets"], help="which sheets to write (default: all)")
        s.set_defaults(fn=fn)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
