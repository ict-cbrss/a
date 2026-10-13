import filecmp
import tempfile
import unittest
from pathlib import Path

from tt import formats, report, validate

FIX = Path(__file__).with_name("fixtures")


def load():
    return (formats.read_timetable(FIX / "TTable.txt"),
            formats.read_enrolments(FIX / "SCourse.txt"))


class FormatTests(unittest.TestCase):
    def test_round_trip_is_byte_identical(self):
        lessons, enrolments = load()
        with tempfile.TemporaryDirectory() as d:
            formats.write_timetable(Path(d) / "T.txt", lessons)
            formats.write_enrolments(Path(d) / "S.txt", enrolments)
            self.assertTrue(filecmp.cmp(FIX / "TTable.txt", Path(d) / "T.txt", shallow=False))
            self.assertTrue(filecmp.cmp(FIX / "SCourse.txt", Path(d) / "S.txt", shallow=False))

    def test_parses_fields(self):
        lessons, enrolments = load()
        self.assertEqual(lessons[5], formats.Lesson(2, 2, "12", "C12D&T_1", "W", "PP", 1, 1, 3))
        self.assertEqual(enrolments[2].field6, "Athens")

    def test_wrong_width_names_line(self):
        with tempfile.TemporaryDirectory() as d:
            bad = Path(d) / "T.txt"
            bad.write_text("1,2,7,C07E_1,G7,AA,16,16,16\r\n1,2,7\r\n")
            with self.assertRaisesRegex(ValueError, r"T.txt:2: expected 9 fields"):
                formats.read_timetable(bad)


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.issues = validate.check(*load())

    def kinds(self, kind):
        return [i for i in self.issues if i.kind == kind]

    def test_teacher_clash(self):
        [i] = self.kinds("teacher-clash")
        self.assertEqual((i.day, i.period), (1, 2))
        self.assertIn("AA has C07E_1, C08E_1", i.message)

    def test_team_teaching_shared_room_is_not_a_clash(self):
        # C07MA_1 has two teachers in G7 at day 1 P3; only C07E_1/C08E_1 clash in G7.
        [i] = self.kinds("room-clash")
        self.assertEqual((i.day, i.period), (1, 2))

    def test_student_clash(self):
        [i] = self.kinds("student-clash")
        self.assertIn("900001", i.message)
        self.assertIn("C07MA_1, C07Sc_1", i.message)

    def test_unknown_and_empty_classes(self):
        self.assertIn("C08Old_1", self.kinds("unknown-class")[0].message)
        self.assertIn("C12D&T_1", self.kinds("empty-class")[0].message)


class ReportTests(unittest.TestCase):
    def test_embeds_data(self):
        lessons, enrolments = load()
        html = report.build(lessons, enrolments, validate.check(lessons, enrolments))
        self.assertNotIn("/*DATA*/null", html)
        self.assertIn("C12D&T_1", html)


if __name__ == "__main__":
    unittest.main()


class ConfigTests(unittest.TestCase):
    def test_missing_directory_gives_defaults(self):
        from tt import config
        cfg = config.load(None)
        self.assertEqual(cfg["blocks"], [])
        self.assertEqual(cfg["names"], [])

    def test_loads_school_and_names(self):
        from tt import config
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "school.json").write_text('{"term": "T1", "blocks": [{"name": "B1", "short": "B1", "days": [1]}]}')
            (Path(d) / "classnames.csv").write_text("code,name,block\nC07E_1,C7 English,\nC07ML_1,C7 Birthing,2\n")
            cfg = config.load(d)
        self.assertEqual(cfg["term"], "T1")
        self.assertEqual(cfg["blocks"][0]["name"], "B1")
        self.assertEqual(cfg["names"], [["C07E_1", "C7 English", None], ["C07ML_1", "C7 Birthing", 2]])

    def test_repo_config_is_valid_and_names_every_fixture_class(self):
        from tt import config
        cfg = config.load(Path(__file__).resolve().parents[1] / "config")
        self.assertEqual(len(cfg["blocks"]), 3)
        self.assertEqual(sum(len(p["ids"]) for p in cfg["periods"]), 8)   # TASS periods 2-9
        self.assertIn(["C07E_1", "C7 English", None], cfg["names"])
