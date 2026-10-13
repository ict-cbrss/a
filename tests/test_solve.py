"""Solver tests on a tiny synthetic school. Skipped unless ortools is installed."""
import unittest

try:
    import ortools  # noqa: F401
except ImportError:  # pragma: no cover
    ortools = None

from tt import solve
from tt.formats import Lesson

DAYS = [1, 2]
PERIODS = [2, 3, 4, 5]


def row(year, group, periods, code, teacher, room, doubles="0", mrcg="", unavailable="", locked=""):
    return {"year": year, "group": group, "periods": str(periods), "doubles": doubles, "mrcg": mrcg,
            "unavailable": unavailable, "locked": locked, "class_code": code, "class_name": code,
            "students": "10", "teacher": teacher, "room": room, "seats": "30", "class_type": ""}


def cfg(classes, teachers=(), rooms=(), doubles=((3, 4),)):
    return {"classes": classes, "teachers": list(teachers), "rooms": list(rooms), "doubles": [list(d) for d in doubles]}


def slots_of(lessons, code):
    return {(l.day, l.period) for l in lessons if l.class_code == code}


@unittest.skipUnless(ortools, "ortools not installed")
class SolveTests(unittest.TestCase):
    def test_places_groups_without_clashes(self):
        c = cfg([row("7", "7A", 3, "C07E_1", "AA", "G7"), row("7", "7B", 2, "C07MA_1", "BB", "G7"),
                 row("8", "8A", 3, "C08E_1", "AA", "C8")])
        status, lessons, report = solve.solve(c, [], DAYS, PERIODS)
        self.assertIn(status, ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(len(slots_of(lessons, "C07E_1")), 3)
        self.assertEqual(len(slots_of(lessons, "C07MA_1")), 2)
        # Year 7 never in two lines at once; AA never teaches two classes at once; G7 never double-booked.
        self.assertFalse(slots_of(lessons, "C07E_1") & slots_of(lessons, "C07MA_1"))
        self.assertFalse(slots_of(lessons, "C07E_1") & slots_of(lessons, "C08E_1"))
        self.assertEqual(report["moved"][0][1], 0)   # nothing to keep: no current timetable

    def test_locked_group_keeps_its_slots_and_others_avoid_them(self):
        current = [Lesson(1, 2, "7", "C07E_1", "G7", "AA", 1, 1, 1), Lesson(2, 5, "7", "C07E_1", "G7", "AA", 1, 1, 1)]
        c = cfg([row("7", "7A", 2, "C07E_1", "AA", "G7", locked="yes"), row("7", "7B", 6, "C07MA_1", "BB", "G7")])
        status, lessons, report = solve.solve(c, current, DAYS, PERIODS)
        self.assertEqual(slots_of(lessons, "C07E_1"), {(1, 2), (2, 5)})
        self.assertEqual(len(slots_of(lessons, "C07MA_1")), 6)
        self.assertFalse(slots_of(lessons, "C07MA_1") & {(1, 2), (2, 5)})
        self.assertEqual(report["kept"], 2)

    def test_prefers_current_timetable(self):
        current = [Lesson(1, 3, "7", "C07E_1", "G7", "AA", 1, 1, 1), Lesson(2, 4, "7", "C07E_1", "G7", "AA", 1, 1, 1)]
        c = cfg([row("7", "7A", 2, "C07E_1", "AA", "G7")])
        status, lessons, report = solve.solve(c, current, DAYS, PERIODS)
        self.assertEqual(slots_of(lessons, "C07E_1"), {(1, 3), (2, 4)})
        self.assertEqual(report["moved"], [])

    def test_doubles_unavailability_and_cross_year_groups(self):
        teachers = [{"code": "AA", "away_days": [2], "unavailable": [[1, 2]], "min_off_per_day": None, "max_consecutive": None}]
        c = cfg([row("7", "7A", 2, "C07E_1", "AA", "G7", doubles="1"),
                 row("9", "9E", 2, "E9/10Mu_1", "NW", "MU", mrcg="1"), row("10", "10E", 2, "E9/10Sp_1", "LG", "CO", mrcg="1"),
                 row("10", "10A", 1, "C10Eng_1", "TWH", "G10", unavailable="1:2;1:3;1:4;1:5;2:2;2:3;2:4")],
                teachers=teachers)
        status, lessons, report = solve.solve(c, [], DAYS, PERIODS)
        self.assertIn(status, ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(slots_of(lessons, "C07E_1"), {(1, 3), (1, 4)})          # AA away day 2, off P2: only double left
        self.assertEqual(slots_of(lessons, "E9/10Mu_1"), slots_of(lessons, "E9/10Sp_1"))   # cross-year group runs together
        self.assertEqual(slots_of(lessons, "C10Eng_1"), {(2, 5)})                # only slot the group may use
        self.assertFalse(slots_of(lessons, "E9/10Sp_1") & {(2, 5)})              # Year 10 not in two lines at once
        self.assertEqual([l.room for l in lessons if l.class_code == "E9/10Mu_1"], ["MU", "MU"])

    def test_teacher_limits(self):
        teachers = [{"code": "AA", "away_days": [], "unavailable": [], "min_off_per_day": 2, "max_consecutive": 1}]
        c = cfg([row("7", "7A", 4, "C07E_1", "AA", "G7")], teachers=teachers)
        status, lessons, report = solve.solve(c, [], DAYS, PERIODS)
        self.assertIn(status, ("OPTIMAL", "FEASIBLE"))
        for d in DAYS:
            ps = sorted(p for dd, p in slots_of(lessons, "C07E_1") if dd == d)
            self.assertEqual(len(ps), 2)                               # 4 periods, 2 off per day
            self.assertNotEqual(ps[1], ps[0] + 1)                      # never consecutive

    def test_plan_problems_and_infeasibility_diagnosis(self):
        c = cfg([row("7", "7A", 2, "C07E_1", "AA", "G7"), row("7", "7A", 2, "C07MA_1", "AA", "G7")])
        status, lessons, report = solve.solve(c, [], DAYS, PERIODS)
        self.assertEqual(status, "INFEASIBLE")
        self.assertEqual(sorted(report["problems"]), ["7A: AA teaches C07E_1, C07MA_1, which run at the same time",
                                                      "7A: classes C07E_1, C07MA_1 all want room G7 at the same time"])
        # Too many doubles for the cycle: diagnosis relaxes doubles and succeeds.
        c = cfg([row("7", "7A", 6, "C07E_1", "AA", "G7", doubles="4")])
        status, lessons, report = solve.solve_with_diagnosis(c, [], DAYS, PERIODS, log=lambda *a: None)
        self.assertIn(status, ("OPTIMAL", "FEASIBLE"))
        self.assertEqual(report["relaxed"], ["doubles"])

    def test_rooms_fall_back_to_the_usual_room(self):
        current = [Lesson(1, 2, "12", "C12MS_1", "Bang", "ARO", 1, 1, 2), Lesson(1, 2, "12", "C12MA_1", "SLab", "SC", 2, 1, 2),
                   Lesson(1, 3, "12", "C12MA_1", "Bang", "SC", 2, 1, 2)]
        c = cfg([row("12", "12B", 2, "C12MS_1", "ARO", ""), row("12", "12B", 2, "C12MA_1", "SC", "")])
        status, lessons, report = solve.solve(c, current, DAYS, PERIODS)
        rooms = {l.class_code: {l.room for l in lessons if l.class_code == l.class_code} for l in lessons}
        self.assertEqual({l.room for l in lessons if l.class_code == "C12MS_1"}, {"Bang"})
        self.assertEqual({l.room for l in lessons if l.class_code == "C12MA_1"}, {"SLab"})   # Bang taken in this line
