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


def main(argv=None):
    p = argparse.ArgumentParser(prog="tt", description="TASS timetable file tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn, help_ in [("check", cmd_check, "list clashes and data problems"),
                            ("report", cmd_report, "write an HTML timetable viewer"),
                            ("export", cmd_export, "write TASS import files"),
                            ("pdf", cmd_pdf, "write the print sheets as PDFs (needs playwright)")]:
        s = sub.add_parser(name, help=help_)
        s.add_argument("ttable", help="TTable.txt")
        s.add_argument("scourse", help="SCourse.txt")
        if name in ("check", "report", "pdf"):
            s.add_argument("-c", "--config", default="config" if Path("config").is_dir() else None,
                           help="folder with school.json, classnames.csv, curriculum.csv (default: ./config if present)")
        if name == "report":
            s.add_argument("-o", "--out", default="timetable.html")
        if name == "export":
            s.add_argument("-o", "--out-dir", default="out")
        if name == "pdf":
            s.add_argument("-o", "--out-dir", default="pdf")
            s.add_argument("-w", "--what", nargs="+", default=["master", "years", "roster", "dutysheets"],
                           choices=["master", "years", "roster", "dutysheets"], help="which sheets to write (default: all)")
        s.set_defaults(fn=fn)
    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
