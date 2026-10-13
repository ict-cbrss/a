"""Browser tests for the editor. Skipped unless Playwright and Chromium are available.

Run with:  pip install playwright && python -m unittest tests.test_viewer
Chromium is found via PLAYWRIGHT_CHROMIUM (a path) or Playwright's own install.
"""
import os
import tempfile
import unittest
from pathlib import Path

from tt import formats, report, validate

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

FIX = Path(__file__).with_name("fixtures")


@unittest.skipUnless(sync_playwright, "playwright not installed")
class ViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lessons = formats.read_timetable(FIX / "TTable.txt")
        cls.enrolments = formats.read_enrolments(FIX / "SCourse.txt")
        cls.tmp = tempfile.TemporaryDirectory()
        cls.html = Path(cls.tmp.name) / "t.html"
        cfg = {"term": "Term 4 2026", "weekdays": ["Mon", "Tue"],
               "blocks": [{"name": "Main Lesson 1", "short": "ML1", "weeks": "Weeks 1-3", "days": [1]},
                          {"name": "Main Lesson 2", "short": "ML2", "weeks": "Weeks 4-6", "days": [2]}],
               "periods": [{"ids": [2], "name": "MC", "time": "9:00"}, {"ids": [3], "name": "Main Lesson", "time": "9:10 - 10:40"}],
               "year_order": ["12", "8", "7"],
               "names": [["C07E_1", "C7 English", None], ["C07MA_1", "C7 Maths ML1", 1], ["C07MA_1", "C7 Maths ML2", 2]],
               "duty_slots": [{"name": "Before School", "conflicts": [2]}, {"name": "Recess", "conflicts": []}, {"name": "Lunch 1", "conflicts": []}],
               "classes": [
                   {"year": "7", "group": "7A", "periods": "1", "doubles": "0", "mrcg": "", "class_code": "C07E_1", "class_name": "C7 English", "students": "1", "teacher": "AA", "room": "G7", "seats": "30", "class_type": ""},
                   {"year": "7", "group": "7B", "periods": "1", "doubles": "0", "mrcg": "1", "class_code": "C07MA_1", "class_name": "C7 Maths", "students": "1", "teacher": "BB", "room": "G7", "seats": "30", "class_type": ""},
                   {"year": "7", "group": "7B", "periods": "1", "doubles": "0", "mrcg": "1", "class_code": "C07Sc_1", "class_name": "C7 Science", "students": "1", "teacher": "DD", "room": "SLab", "seats": "36", "class_type": ""},
                   {"year": "8", "group": "8A", "periods": "2", "doubles": "0", "mrcg": "", "class_code": "C08E_1", "class_name": "C8 English", "students": "1", "teacher": "AA", "room": "G7", "seats": "30", "class_type": ""}],
               "teachers": [{"code": "DD", "name": "Dee D", "email": "dd@school", "max_duties": None, "no_duties": False, "away_days": [2], "max_periods": None, "min_off_per_day": None, "max_consecutive": None, "unavailable": []},
                            {"code": "CC", "name": "", "email": "", "max_duties": 1, "no_duties": False, "away_days": [], "max_periods": None, "min_off_per_day": None, "max_consecutive": None, "unavailable": []}],
               "rooms": [{"code": "G7", "name": "", "seats": 30, "unavailable": []}, {"code": "SLab", "name": "Science lab", "seats": 36, "unavailable": []}],
               "doubles": [[2, 3]],
               "duties": [[1, "Recess", "Recess top", "AA"], [1, "Lunch 1", "Lunch 1 Walk", "BB"], [2, "Recess", "Recess top", "AA"]]}
        cls.html.write_text(report.build(cls.lessons, cls.enrolments,
                                         validate.check(cls.lessons, cls.enrolments), cfg), encoding="utf-8")
        cls.pw = sync_playwright().start()
        exe = os.environ.get("PLAYWRIGHT_CHROMIUM")
        cls.browser = cls.pw.chromium.launch(executable_path=exe) if exe else cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.tmp.cleanup()

    def setUp(self):
        # A fresh context each test, so localStorage edits never leak between tests.
        self.ctx = self.browser.new_context(accept_downloads=True)
        self.page = self.ctx.new_page()
        self.errors = []
        self.page.on("pageerror", lambda e: self.errors.append(str(e)))
        self._dialog = lambda d: d.accept()   # confirm() dialogs are accepted; tests needing a prompt swap this
        self.page.on("dialog", self._dialog)
        self.page.goto(self.html.as_uri())

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.ctx.close()

    def download(self, button):
        with self.page.expect_download() as d:
            self.page.click(button)
        path = Path(self.tmp.name) / d.value.suggested_filename
        d.value.save_as(path)
        return path

    def issues_button(self):
        return self.page.inner_text("#views button[data-v=Issues]")

    def test_unedited_downloads_are_byte_identical(self):
        for button, name in [("#dl-ttable", "TTable.txt"), ("#dl-scourse", "SCourse.txt")]:
            self.assertEqual(self.download(button).read_bytes(), (FIX / name).read_bytes())

    def test_drag_moves_every_teacher_row_and_clears_clash(self):
        self.assertIn("4 errors", self.issues_button())
        self.page.click("#views button[data-v=Class]")
        self.page.select_option("#pick", "C08E_1")
        # C08E_1 shares teacher AA and room G7 with C07E_1 on Day 1 P2; moving it clears both clashes.
        self.page.drag_and_drop(".l[data-c=C08E_1]", "td[data-d='2'][data-p='2']")
        self.assertIn("2 errors", self.issues_button())
        lessons = formats.read_timetable(self.download("#dl-ttable"))
        moved = [l for l in lessons if l.class_code == "C08E_1"]
        self.assertEqual([(l.day, l.period, l.teacher) for l in moved], [(2, 2, "AA")])
        self.page.click("#views button[data-v=Changes]")
        self.assertIn("Moved C08E_1 from ML1 Mon MC to ML2 Mon MC", self.page.inner_text("#changes"))

    def test_dialog_edits_room_and_teachers(self):
        self.page.click("#views button[data-v=Class]")
        self.page.select_option("#pick", "C07MA_1")
        self.page.click(".l[data-c=C07MA_1]")
        self.page.fill("#dlg-room", "Art1")
        self.page.fill("#dlg-teachers", "BB, EE, FF")
        self.page.click("#dlg-save")
        rows = [l for l in formats.read_timetable(self.download("#dl-ttable")) if l.class_code == "C07MA_1"]
        self.assertEqual(sorted(l.teacher for l in rows), ["BB", "EE", "FF"])
        self.assertEqual({(l.room, l.column, l.block_start, l.block_end) for l in rows}, {("Art1", 16, 16, 17)})

    def test_add_and_delete_lesson(self):
        self.page.click("#views button[data-v=Class]")
        self.page.select_option("#pick", "C12D&T_1")
        self.page.click("td[data-d='1'][data-p='3']")
        self.assertEqual(self.page.input_value("#dlg-room"), "W")       # prefilled from the class
        self.assertEqual(self.page.input_value("#dlg-teachers"), "PP")
        self.page.click("#dlg-save")
        self.assertEqual(self.page.locator(".l[data-c='C12D&T_1']").count(), 2)
        self.page.click(".l[data-c='C12D&T_1'][data-d='2']")
        self.page.click("#dlg-delete")  # confirm() auto-accepted
        rows = [l for l in formats.read_timetable(self.download("#dl-ttable")) if l.class_code == "C12D&T_1"]
        self.assertEqual([(l.day, l.period, l.year, l.column) for l in rows], [(1, 3, "12", 1)])

    def test_student_moves_and_undo(self):
        self.page.click("#views button[data-v=Student]")
        self.page.select_option("#pick", "900001")
        self.page.select_option("select[data-from=C07Sc_1]", "C12D&T_1")  # Day 2 P2: drops the student clash
        self.assertIn("3 errors", self.issues_button())
        enr = formats.read_enrolments(self.download("#dl-scourse"))
        self.assertEqual([e.class_code for e in enr if e.student_id == "900001"], ["C07E_1", "C07MA_1", "C12D&T_1"])
        self.assertEqual(enr[2].field6, "Athens")  # other columns of the row are kept
        self.page.click("#undo")
        self.assertIn("4 errors", self.issues_button())
        self.assertEqual(self.download("#dl-scourse").read_bytes(), (FIX / "SCourse.txt").read_bytes())

    def test_edits_survive_reload_and_reset_clears_them(self):
        self.page.click("#views button[data-v=Student]")
        self.page.select_option("#pick", "900002")
        self.page.click("button[data-remove=C08Old_1]")
        self.page.reload()
        self.assertIn("Restored 1 edits", self.page.inner_text("#note"))
        self.page.click("#reset")
        self.page.reload()
        self.assertNotIn("Restored", self.page.inner_text("#note"))

    def test_config_labels_and_block_names(self):
        self.page.click("#views button[data-v=Class]")
        self.page.select_option("#pick", "C07MA_1")
        self.assertEqual(self.page.inner_text("#grid thead tr:first-child").split(), ["Main", "Lesson", "1", "Weeks", "1-3", "Main", "Lesson", "2", "Weeks", "4-6"])
        self.assertIn("C7 Maths ML1", self.page.inner_text(".l[data-c=C07MA_1][data-d='1']"))
        self.page.click("#views button[data-v=Issues]")
        self.assertIn("ML1 Mon MC: Teacher AA has", self.page.inner_text("#issues"))

    def test_print_view_master_and_single_year(self):
        self.page.click("#views button[data-v=Print]")
        sheets = self.page.locator(".sheet")
        self.assertEqual(sheets.count(), 2)   # one per block
        first = sheets.nth(0)
        self.assertEqual(first.locator("h2").inner_text(), "TERM 4 2026 MASTER TIMETABLE — MAIN LESSON 1 (WEEKS 1-3)")
        self.assertEqual([c.inner_text() for c in first.locator("td.yr").all()], ["12", "8", "7"])   # year_order
        row7 = first.locator("tbody tr").nth(2)   # third year row = year 7; first row carries the day cell too
        mc, ml = row7.locator("td").nth(1), row7.locator("td").nth(2)
        self.assertIn("C7 English", mc.inner_text()); self.assertIn("G7 AA", mc.inner_text())
        self.assertIn("C7 Maths ML1", ml.inner_text()); self.assertIn("G7 BB", ml.inner_text()); self.assertIn("G7 CC", ml.inner_text())
        self.page.select_option("#print-year", "7")
        self.page.select_option("#print-block", "2")
        self.assertEqual(self.page.locator(".sheet").count(), 1)
        self.assertEqual(self.page.locator(".sheet h2").inner_text(), "CLASS 7 TERM 4 2026 TIMETABLE — MAIN LESSON 2 WEEKS 4-6")
        self.assertIn("C12D&T_1", self.page.content())   # unnamed codes fall back to the code

    def test_yard_duties_in_teacher_view_and_roster_print(self):
        self.page.select_option("#pick", "AA")
        self.assertIn("2 yard duties", self.page.inner_text("#info"))
        self.assertEqual(self.page.locator("#grid .l.duty").all_inner_texts(), ["Recess top", "Recess top"])
        self.page.click("#views button[data-v=Print]")
        self.page.select_option("#print-year", "duties")
        self.page.select_option("#print-block", "1")
        sheet = self.page.locator(".sheet")
        self.assertEqual(sheet.locator("h2").inner_text(), "TERM 4 2026 YARD DUTY ROSTER — MAIN LESSON 1 (WEEKS 1-3)")
        self.assertIn("Recess top\tAA", sheet.inner_text())
        self.assertIn("Lunch 1 Walk\tBB", sheet.inner_text())

    def test_duty_builder_assign_clash_autofill_remove_download(self):
        self.page.click("#views button[data-v=Duties]")
        self.assertEqual(self.page.inner_text("#info"), "2 duties · 3 assigned · 1 empty · 0 problems")
        sel = "select[data-d='2'][data-duty='Lunch 1 Walk']"
        self.page.select_option(sel, "AA")   # AA already has Recess top on day 2 - different slot, so fine
        self.assertEqual(self.page.inner_text("#info"), "2 duties · 4 assigned · 0 empty · 0 problems")
        self.page.select_option("select[data-d='2'][data-duty='Recess top']", "DD")   # DD is away on day 2
        self.assertEqual(self.page.inner_text("#info"), "2 duties · 4 assigned · 0 empty · 1 problems")
        self.assertIn("DD is away", self.page.locator("#duty-grid td.clash").first.get_attribute("title"))
        self.page.click("#undo"); self.page.click("#undo")
        # New duty before school: AA teaches at P2 (MC) on day 1 so cannot take it; auto-fill must pick someone else.
        self.page.select_option("#duty-slot", "Before School"); self.page.fill("#duty-name", "Gate"); self.page.click("#duty-add")
        self.assertEqual(self.page.inner_text("#info"), "3 duties · 3 assigned · 3 empty · 0 problems")
        self.page.click("#duty-auto")
        self.assertEqual(self.page.inner_text("#info"), "3 duties · 6 assigned · 0 empty · 0 problems")
        self.assertNotEqual(self.page.input_value("select[data-d='1'][data-duty='Gate']"), "AA")
        self.assertNotEqual(self.page.input_value("select[data-d='2'][data-duty='Gate']"), "DD")
        csv_text = self.download("#dl-duties").read_text()
        self.assertTrue(csv_text.startswith("day,block,weekday,slot,duty,teacher\n1,1,Mon,Before School,Gate,"))
        self.assertEqual(csv_text.count("\n"), 7)
        self.page.click("button[data-rm-duty='Gate']")   # confirm() auto-accepted
        self.assertEqual(self.page.inner_text("#info"), "2 duties · 4 assigned · 0 empty · 0 problems")   # auto-fill also filled Lunch 1 Walk
        self.page.click("#views button[data-v=Changes]")
        self.assertIn("Removed duty Gate at Before School", self.page.inner_text("#changes"))

    def test_teacher_settings_cap_no_duties_and_duty_sheets(self):
        self.page.click("#views button[data-v=Teachers]")
        self.assertEqual(self.page.inner_text("#info"), "5 teachers")
        self.page.check("tr[data-t=AA] input[data-f=no_duties]")
        self.page.fill("tr[data-t=BB] input[data-f=name]", "Bea B"); self.page.press("tr[data-t=BB] input[data-f=name]", "Tab")
        self.page.click("#views button[data-v=Duties]")
        # AA now does no duties: both existing AA duties are problems; CC is capped at 1.
        self.assertEqual(self.page.inner_text("#info"), "2 duties · 3 assigned · 1 empty · 2 problems")
        self.page.select_option("select[data-d='2'][data-duty='Lunch 1 Walk']", "CC")
        self.page.select_option("select[data-d='1'][data-duty='Recess top']", "CC")
        self.assertIn("would have 2 duties, max 1", self.page.locator("select[data-d='1'][data-duty='Recess top']").locator("..").get_attribute("title"))
        self.page.click("#views button[data-v=Issues]")
        self.assertIn("CC has 2 duties, max 1", self.page.inner_text("#issues"))
        self.page.click("#views button[data-v=Print]")
        self.page.select_option("#print-year", "dutysheets")
        self.assertEqual(self.page.locator(".sheet.a4").count(), 3)   # AA (still rostered day 2), BB, CC
        self.page.select_option("#print-teacher", "BB")
        sheet = self.page.locator(".sheet.a4")
        self.assertEqual(sheet.count(), 1)
        self.assertEqual(sheet.locator("h2").inner_text(), "Yard Duties — Bea B")
        self.assertIn("Lunch 1 Walk", sheet.inner_text())
        self.page.click("#views button[data-v=Teachers]")
        csv_text = self.download("#dl-teachers").read_text()
        self.assertIn("AA,,,,yes,,,,,\n", csv_text)
        self.assertIn("BB,Bea B,,,,,,,,\n", csv_text)
        self.assertIn("DD,Dee D,dd@school,,,2,,,,\n", csv_text)

    def test_class_information_editor(self):
        self.page.click("#views button[data-v=Classes]")
        self.page.select_option("#pick", "7")
        self.assertEqual(self.page.inner_text("#class-total"), "2 groups · 2 periods of 4 in the cycle")
        self.assertEqual([th.inner_text().split("\n")[0] for th in self.page.locator("#class-grid thead th.g").all()], ["A", "B"])
        # C8 English is planned for 2 periods but timetabled for 1: an issue, and shown in the loads table.
        self.page.click("#views button[data-v=Issues]")
        self.assertIn("C08E_1 is timetabled for 1 periods, plan says 2", self.page.inner_text("#issues"))
        self.page.click("#views button[data-v=Classes]")
        self.assertIn("AA\t3\t1", self.page.inner_text("#class-loads"))   # both AA classes sit in the one slot
        # Change a group's periods, a class's teacher, move a group, add and remove a class, add a group.
        self.page.fill("input[data-g='7A'][data-f=periods]", "3"); self.page.press("input[data-g='7A'][data-f=periods]", "Tab")
        self.assertEqual(self.page.inner_text("#class-total"), "2 groups · 4 periods of 4 in the cycle")
        self.page.select_option("select[data-g='7B'][data-c='C07Sc_1'][data-f=teacher]", "CC")
        self.page.click("button[data-mv='7A'][data-dir='1']")
        self.assertEqual([th.inner_text().split("\n")[0] for th in self.page.locator("#class-grid thead th.g").all()], ["A", "B"])
        self.assertEqual(self.page.locator("#class-grid .cls[data-g='7A']").first.get_attribute("data-c"), "C07MA_1")   # old B is now A
        self.page.select_option("select[data-add-g='7B']", "C12D&T_1")
        self.assertEqual(self.page.locator("#class-grid .cls[data-g='7B']").count(), 2)
        self.page.click("button[data-rm-g='7B'][data-rm-c='C12D&T_1']")
        self.assertEqual(self.page.locator("#class-grid .cls[data-g='7B']").count(), 1)
        self.page.remove_listener("dialog", self._dialog)
        self.page.on("dialog", lambda d: d.accept("C07Geo_1") if d.type == "prompt" else d.accept())
        self.page.click("#group-add")
        self.assertEqual([th.inner_text().split("\n")[0] for th in self.page.locator("#class-grid thead th.g").all()], ["A", "B", "C"])
        csv_text = self.download("#dl-curriculum").read_text()
        rows = [l.split(",") for l in csv_text.strip().split("\n")]
        self.assertEqual(rows[0][:7], ["year", "group", "periods", "doubles", "mrcg", "unavailable", "class_code"])
        by = {(r[1], r[6]): r for r in rows[1:]}
        self.assertEqual(by[("7A", "C07Sc_1")][9], "CC")          # moved to A, teacher changed
        self.assertEqual(by[("7B", "C07E_1")][2], "3")            # periods changed
        self.assertEqual(by[("7C", "C07Geo_1")][6], "C07Geo_1")   # new group
        self.page.click("#views button[data-v=Changes]")
        self.assertIn("Moved group A (Year 7) right", self.page.inner_text("#changes"))

    def test_rooms_teacher_limits_group_unavailable_and_doubles(self):
        # Rooms: mark SLab unavailable where C07Sc_1 is timetabled (day 1 P3) -> error; seats warning for a big class.
        self.page.click("#views button[data-v=Rooms]")
        self.assertEqual(self.page.inner_text("#info"), "3 rooms")   # G7, SLab from config + W from the file
        self.page.click("button[data-avail='SLab']")
        self.assertEqual(self.page.locator("#room-avail td[data-d='1'][data-p='3']").get_attribute("title"), "C7 Science with DD")
        self.page.click("#room-avail td[data-d='1'][data-p='3']")
        self.page.fill("tr[data-r=G7] input[data-f=seats]", "0"); self.page.press("tr[data-r=G7] input[data-f=seats]", "Tab")
        self.page.click("#views button[data-v=Issues]")
        issues = self.page.inner_text("#issues")
        self.assertIn("SLab has C7 Science but is marked unavailable", issues)
        self.assertIn("C07E_1 has 1 students but G7 seats 0", issues)
        # Teacher limits: AA teaches 1 period; cap at 0 and mark a period unavailable.
        self.page.click("#views button[data-v=Teachers]")
        self.page.fill("tr[data-t=AA] input[data-f=max_periods]", "0"); self.page.press("tr[data-t=AA] input[data-f=max_periods]", "Tab")
        self.page.click("button[data-avail='AA']"); self.page.click("#teacher-avail td[data-d='1'][data-p='2']")
        self.assertEqual(self.page.inner_text("button[data-avail='AA']"), "Periods (1)")
        self.page.click("#views button[data-v=Issues]")
        issues = self.page.inner_text("#issues")
        self.assertIn("AA teaches 1 periods, max 0", issues)
        self.assertIn("AA teaches C7 English but is marked unavailable", issues)
        # Group unavailable: Year 7 group A (C07E_1) at day 1 P2.
        self.page.click("#views button[data-v=Classes]"); self.page.select_option("#pick", "7")
        self.page.click("button[data-avail-g='7A']"); self.page.click("#group-avail td[data-d='1'][data-p='2']")
        self.assertEqual(self.page.inner_text("button[data-avail-g='7A']"), "Unavail (1)")
        self.page.click("#views button[data-v=Issues]")
        self.assertIn("C7 English is timetabled but group A (Year 7) is marked unavailable", self.page.inner_text("#issues"))
        # Doubles: one pair ticked from config; untick it, download school.json.
        self.page.click("#views button[data-v=Settings]")
        self.assertEqual(self.page.inner_text("#info"), "1 double period pairs")
        self.page.uncheck("#doubles input[data-a='2'][data-b='3']")
        self.assertEqual(self.page.inner_text("#info"), "0 double period pairs")
        self.assertIn('"doubles": []', self.download("#dl-school").read_text())
        self.page.click("#views button[data-v=Rooms]")
        rooms_csv = self.download("#dl-rooms").read_text()
        self.assertIn("G7,,0,\n", rooms_csv); self.assertIn("SLab,Science lab,36,1:3\n", rooms_csv)
        self.page.click("#views button[data-v=Teachers]")
        self.assertIn("AA,,,,,,0,,,1:2\n", self.download("#dl-teachers").read_text())


@unittest.skipUnless(sync_playwright, "playwright not installed")
class PdfCommandTests(unittest.TestCase):
    def test_pdf_command_writes_sheets(self):
        from tt.__main__ import main
        with tempfile.TemporaryDirectory() as d:
            cfg = Path(d) / "config"; cfg.mkdir()
            (cfg / "school.json").write_text('{"term": "T1", "weekdays": ["Mon", "Tue"], "blocks": [{"name": "B1", "short": "B1", "weeks": "", "days": [1, 2]}], "periods": [{"ids": [2], "name": "MC", "time": ""}, {"ids": [3], "name": "ML", "time": ""}], "duty_slots": [{"name": "Recess", "conflicts": []}]}')
            (cfg / "duties.csv").write_text("day,block,weekday,slot,duty,teacher\n1,1,Mon,Recess,Recess top,AA\n2,1,Tue,Recess,Recess top,BB\n")
            rc = main(["pdf", str(FIX / "TTable.txt"), str(FIX / "SCourse.txt"), "-c", str(cfg), "-o", str(Path(d) / "pdf")])
            self.assertEqual(rc, 0)
            names = sorted(p.name for p in (Path(d) / "pdf").iterdir())
        self.assertEqual(names, ["class-12-timetable.pdf", "class-7-timetable.pdf", "class-8-timetable.pdf",
                                 "duties-AA.pdf", "duties-BB.pdf", "master-timetable.pdf", "yard-duty-roster.pdf"])

