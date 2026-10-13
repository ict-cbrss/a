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
        cls.html.write_text(report.build(cls.lessons, cls.enrolments,
                                         validate.check(cls.lessons, cls.enrolments)), encoding="utf-8")
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
        self.page.on("dialog", lambda d: d.accept())
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
        self.assertIn("Moved C08E_1 from Day 1 P2 to Day 2 P2", self.page.inner_text("#changes"))

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
