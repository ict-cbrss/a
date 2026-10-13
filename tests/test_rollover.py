"""Year rollover and next-term folder tests."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tt import rollover
from tt.__main__ import main
from tt.formats import Enrolment, Lesson, read_enrolments, read_timetable

FIX = Path(__file__).with_name("fixtures")


def lesson(year, code):
    return Lesson(1, 2, year, code, "R1", "AA", 1, 1, 1)


def enrol(sid, name, year, code):
    return Enrolment(sid, name, year, code, "NS", "", "", year)


class RolloverTests(unittest.TestCase):
    def test_codes_advance_with_padding_and_ranges_are_left_alone(self):
        self.assertEqual(rollover.advance_code("C07E_1", 7, 8), "C08E_1")
        self.assertEqual(rollover.advance_code("C09Eng_1", 9, 10), "C10Eng_1")
        self.assertEqual(rollover.advance_code("MCHS_10", 10, 11), "MCHS_11")
        self.assertEqual(rollover.advance_code("E9/10Ar_1", 9, 10), "E9/10Ar_1")
        self.assertEqual(rollover.class_years("E9/10Ar_1", [lesson("9", "E9/10Ar_1")]), {9, 10})

    def test_cohort_moves_into_next_years_core_classes(self):
        lessons = [lesson("7", "C07E_1"), lesson("7", "C07Tex_1"), lesson("7", "C07VAB_1"),
                   lesson("8", "C08E_1"), lesson("8", "C08His_1"), lesson("8", "C08VAB_2"),
                   lesson("9", "E9/10Ar_1"), lesson("12", "C12EA_1")]
        year7 = [enrol("1", "A", "7", "C07E_1"), enrol("1", "A", "7", "C07Tex_1"), enrol("1", "A", "7", "C07VAB_1"),
                 enrol("2", "B", "7", "C07E_1"), enrol("2", "B", "7", "C07Tex_1")]
        year8 = [enrol("3", "C", "8", "C08E_1"), enrol("3", "C", "8", "C08His_1"), enrol("3", "C", "8", "C08VAB_2"),
                 enrol("6", "F", "8", "C08E_1"), enrol("6", "F", "8", "C08His_1")]
        year9 = [enrol("4", "D", "9", "E9/10Ar_1")]
        year12 = [enrol("5", "E", "12", "C12EA_1")]
        out, rep = rollover.roll_enrolments(year7 + year8 + year9 + year12, lessons, advance=[7, 8, 9, 10, 11])
        codes = lambda sid: [e.class_code for e in out if e.student_id == sid]
        # Year 7 core classes (English, Textiles) are swapped for Year 8's (English, History); the half-year
        # art class maps by stem to C08VAB_2; Textiles has no Year 8 class and is reported.
        self.assertEqual(codes("1"), ["C08VAB_2", "C08E_1", "C08His_1"])
        self.assertEqual(codes("2"), ["C08E_1", "C08His_1"])
        self.assertEqual({e.year for e in out if e.student_id == "1"}, {"8"})
        self.assertEqual([e.form for e in out if e.student_id == "1"], ["8", "8", "8"])
        self.assertEqual(codes("4"), ["E9/10Ar_1"])                   # cross-year elective kept for 9 -> 10
        self.assertEqual(codes("5"), ["C12EA_1"])                     # Year 12 stays
        self.assertEqual(rep["moved"], {"7->8": 2, "8->9": 2, "9->10": 1})
        self.assertEqual(rep["years_without_classes"], [])
        # Year 8's core classes are swapped away; Year 9 has no core classes (its elective is cross-year), so
        # only the half-year art class, which has no Year 9 match, is reported.
        self.assertEqual(codes("3"), [])
        self.assertEqual([(u[2], len(u[3])) for u in rep["unplaced"]], [("C08VAB_2", 1)])
        self.assertIn("C08VAB_2 (Year 8 -> 9, 1 students): 3 C", rollover.report_text(rep))

    def test_into_term4_leaves_year_12_and_reports_a_year_with_no_timetable(self):
        lessons = [lesson("11", "C11EA_1"), lesson("12", "C12EA_1")]
        enrolments = [enrol("1", "A", "11", "C11EA_1"), enrol("2", "B", "12", "C12EA_1")]
        out, rep = rollover.roll_enrolments(enrolments, lessons, advance=[11], leave=[12])
        self.assertEqual([(e.student_id, e.year, e.class_code) for e in out], [("1", "12", "C12EA_1")])
        self.assertEqual(rep["left"], 1)
        # Year 10 -> 11 with no Year 11 timetable yet: said once, not per class.
        out, rep = rollover.roll_enrolments([enrol("3", "C", "10", "C10Eng_1")], [lesson("10", "C10Eng_1")],
                                            classes=[{"year": "11", "class_code": "C11EA_1"}], advance=[10])
        self.assertEqual(out, [])
        self.assertEqual(rep["years_without_classes"], [11])
        text = rollover.report_text(rep)
        self.assertIn("Year 11 is not in the timetable yet (1 classes in the plan", text)
        self.assertNotIn("no Year-up equivalent", text)

    def test_next_term_and_start_term(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            shutil.copytree(Path("config"), root / "config")
            (root / "timetable").mkdir()
            shutil.copy(FIX / "TTable.txt", root / "timetable" / "TTable.txt")
            rc = main(["next-term", str(root / "timetable" / "TTable.txt"), "Term 1 2027", "-c", str(root / "config"),
                       "-s", str(FIX / "SCourse.txt"), "-r", "end-of-year", "-o", str(root / "next")])
            self.assertEqual(rc, 0)
            nxt = root / "next"
            self.assertEqual(json.loads((nxt / "config" / "school.json").read_text())["term"], "Term 1 2027")
            self.assertEqual(read_timetable(nxt / "TTable.txt"), read_timetable(FIX / "TTable.txt"))
            rolled = read_enrolments(nxt / "SCourse.txt")
            self.assertEqual({e.year for e in rolled if e.student_id == "900001"}, {"8"})
            self.assertTrue((nxt / "rollover-report.txt").exists())
            self.assertIn("students", (nxt / "config" / "curriculum.csv").read_text().splitlines()[0])
            with self.assertRaises(FileExistsError):
                rollover.new_term(nxt, "Term 1 2027", FIX / "TTable.txt", root / "config")
            # Make it the current term: old files archived under the old term's name.
            (nxt / "TTable.txt").write_bytes(b"1,2,8,C08E_1,R1,AA,1,1,1\r\n")
            self.assertEqual(main(["start-term", str(nxt), "--root", str(root)]), 0)
            self.assertEqual((root / "timetable" / "TTable.txt").read_bytes(), b"1,2,8,C08E_1,R1,AA,1,1,1\r\n")
            self.assertEqual(json.loads((root / "config" / "school.json").read_text())["term"], "Term 1 2027")
            self.assertEqual(read_timetable(root / "archive" / "term-4-2026" / "TTable.txt"), read_timetable(FIX / "TTable.txt"))
            self.assertEqual(json.loads((root / "archive" / "term-4-2026" / "config" / "school.json").read_text())["term"], "Term 4 2026")

    def test_rollover_command_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            rc = main(["rollover", str(FIX / "TTable.txt"), str(FIX / "SCourse.txt"), "-c", "config", "-o", d, "--advance", "7"])
            self.assertEqual(rc, 0)
            self.assertTrue((Path(d) / "SCourse.txt").exists() and (Path(d) / "rollover-report.txt").exists())


if __name__ == "__main__":
    unittest.main()
