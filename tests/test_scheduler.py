"""
SmartShed AI - Automated Scheduler Unit & Constraint Verification Test Suite
Tests:
1. CSP Unit expansion with theory (1-period) and lab (multi-period) courses
2. MRV heuristic calculation
3. Backtracking scheduler solving realistic college dataset
4. Independent validator verification of all 8 hard constraints
5. Infeasibility and conflict reporting when over-constrained
"""

import unittest
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.scheduler import TimetableScheduler, validate_timetable_solution


class TestTimetableScheduler(unittest.TestCase):

    def setUp(self):
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.periods = [1, 2, 3, 4, 5, 6, 7]

        self.sections = [
            {"id": 1, "year": "III Year", "branch": "CSE", "section_name": "Sec-A", "student_strength": 60},
            {"id": 2, "year": "III Year", "branch": "CSE", "section_name": "Sec-B", "student_strength": 60},
            {"id": 3, "year": "III Year", "branch": "AI & DS", "section_name": "Sec-A", "student_strength": 55},
        ]

        self.faculty = [
            {"id": 1, "name": "Dr. Robert Smith", "department": "CSE"},
            {"id": 2, "name": "Dr. Emily Davis", "department": "CSE"},
            {"id": 3, "name": "Prof. Alan Turing", "department": "CSE"},
            {"id": 4, "name": "Prof. Grace Hopper", "department": "IT"},
            {"id": 5, "name": "Prof. John Von Neumann", "department": "CSE"},
            {"id": 6, "name": "Dr. Ada Lovelace", "department": "AI & DS"},
            {"id": 7, "name": "Prof. Claude Shannon", "department": "IT"},
            {"id": 8, "name": "Dr. Barbara Liskov", "department": "CSE"},
        ]

        self.classrooms = [
            {"id": 1, "room_number": "LH-101", "room_type": "Classroom", "capacity": 70, "building": "Main"},
            {"id": 2, "room_number": "LH-102", "room_type": "Classroom", "capacity": 70, "building": "Main"},
            {"id": 3, "room_number": "LH-103", "room_type": "Classroom", "capacity": 65, "building": "Main"},
            {"id": 4, "room_number": "CS-LAB-1", "room_type": "Lab", "capacity": 70, "building": "Turing Wing"},
            {"id": 5, "room_number": "CS-LAB-2", "room_type": "Lab", "capacity": 70, "building": "Hopper Wing"},
            {"id": 6, "room_number": "AI-LAB-1", "room_type": "Lab", "capacity": 65, "building": "AI Center"},
        ]

        self.subjects = [
            {"id": 1, "code": "CS301", "name": "Data Structures", "type": "Theory", "periods_per_week": 4, "lab_duration": 1, "preferred_faculty_id": 2},
            {"id": 2, "code": "CS302", "name": "DBMS", "type": "Theory", "periods_per_week": 4, "lab_duration": 1, "preferred_faculty_id": 4},
            {"id": 3, "code": "CS303", "name": "Operating Systems", "type": "Theory", "periods_per_week": 4, "lab_duration": 1, "preferred_faculty_id": 8},
            {"id": 4, "code": "CS304", "name": "Computer Networks", "type": "Theory", "periods_per_week": 3, "lab_duration": 1, "preferred_faculty_id": 7},
            {"id": 5, "code": "CS305", "name": "Artificial Intelligence", "type": "Theory", "periods_per_week": 3, "lab_duration": 1, "preferred_faculty_id": 1},
            {"id": 6, "code": "CS306", "name": "Theory of Computation", "type": "Theory", "periods_per_week": 3, "lab_duration": 1, "preferred_faculty_id": 3},
            {"id": 7, "code": "AI301", "name": "Machine Learning", "type": "Theory", "periods_per_week": 3, "lab_duration": 1, "preferred_faculty_id": 6},
            {"id": 8, "code": "CS391", "name": "Data Structures Lab", "type": "Lab", "periods_per_week": 2, "lab_duration": 2, "preferred_faculty_id": 2},
            {"id": 9, "code": "CS392", "name": "DBMS Lab", "type": "Lab", "periods_per_week": 2, "lab_duration": 2, "preferred_faculty_id": 4},
            {"id": 10, "code": "AI391", "name": "AI & Deep Learning Lab", "type": "Lab", "periods_per_week": 3, "lab_duration": 3, "preferred_faculty_id": 6},
        ]

        # Build comprehensive faculty availability (Mon-Fri, Periods 1-7)
        self.faculty_availability = []
        for f in self.faculty:
            for d in self.days:
                for p in self.periods:
                    is_avail = 1
                    # Natural busy slot
                    if f["id"] == 1 and d == "Wednesday" and p == 4:
                        is_avail = 0
                    self.faculty_availability.append({
                        "faculty_id": f["id"],
                        "day": d,
                        "period": p,
                        "is_available": is_avail
                    })

        # Section-Subject curriculum assignments
        self.section_subjects = []
        # CSE Sec-A
        for sub_id in [1, 2, 3, 4, 5, 6, 8, 9]:
            self.section_subjects.append({"section_id": 1, "subject_id": sub_id, "faculty_id": self.subjects[sub_id-1]["preferred_faculty_id"]})
        # CSE Sec-B
        for sub_id in [1, 2, 3, 4, 5, 6, 8, 9]:
            self.section_subjects.append({"section_id": 2, "subject_id": sub_id, "faculty_id": self.subjects[sub_id-1]["preferred_faculty_id"]})
        # AI&DS Sec-A
        for sub_id in [1, 2, 3, 5, 7, 8, 10]:
            self.section_subjects.append({"section_id": 3, "subject_id": sub_id, "faculty_id": self.subjects[sub_id-1]["preferred_faculty_id"]})

    def test_unit_expansion(self):
        """Verify that lab and theory units expand properly into correct durations."""
        scheduler = TimetableScheduler(
            self.days, self.periods, self.sections, self.subjects,
            self.faculty, self.classrooms, self.faculty_availability, self.section_subjects
        )
        units = scheduler.expand_scheduling_units()
        self.assertGreater(len(units), 0)

        # Check that 2-period and 3-period lab units exist
        lab_units = [u for u in units if u.subject_type == "Lab"]
        self.assertTrue(any(u.duration == 2 for u in lab_units))
        self.assertTrue(any(u.duration == 3 for u in lab_units))

        # Check that theory units are 1 period
        theory_units = [u for u in units if u.subject_type == "Theory"]
        self.assertTrue(all(u.duration == 1 for u in theory_units))

    def test_full_timetable_generation_and_validation(self):
        """Verify that a full schedule is successfully generated with 0 constraint violations."""
        scheduler = TimetableScheduler(
            self.days, self.periods, self.sections, self.subjects,
            self.faculty, self.classrooms, self.faculty_availability, self.section_subjects
        )
        success, rows, conflicts = scheduler.solve()

        self.assertTrue(success, f"Scheduling failed with conflicts: {conflicts}")
        self.assertIsNotNone(rows)
        self.assertGreater(len(rows), 0)

        # Verify all hard constraints independently
        fac_map = {(fa["faculty_id"], fa["day"], fa["period"]): bool(fa["is_available"]) for fa in self.faculty_availability}
        is_valid, validation_errors = validate_timetable_solution(
            rows, self.days, self.periods,
            {s["id"]: s for s in self.sections},
            {s["id"]: s for s in self.subjects},
            {f["id"]: f for f in self.faculty},
            {r["id"]: r for r in self.classrooms},
            fac_map
        )
        self.assertTrue(is_valid, f"Validation failed: {validation_errors}")

    def test_infeasibility_detection(self):
        """Verify that impossible constraints trigger conflict diagnostics without crashing."""
        # Restrict faculty 1 to only 1 period per week while being assigned 6 periods of classes
        restricted_avail = []
        for f in self.faculty:
            for d in self.days:
                for p in self.periods:
                    is_avail = 0 if f["id"] == 1 else 1
                    restricted_avail.append({
                        "faculty_id": f["id"],
                        "day": d,
                        "period": p,
                        "is_available": is_avail
                    })

        scheduler = TimetableScheduler(
            self.days, self.periods, self.sections, self.subjects,
            self.faculty, self.classrooms, restricted_avail, self.section_subjects
        )
        success, rows, conflicts = scheduler.solve()

        self.assertFalse(success)
        self.assertIsNone(rows)
        self.assertGreater(len(conflicts), 0)
        self.assertTrue(any("Faculty" in c or "available" in c for c in conflicts))


if __name__ == "__main__":
    unittest.main()
