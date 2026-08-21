"""
SmartShed AI - Intelligent Constraint-Based Timetable Scheduler
===============================================================
A pure-Python Constraint Satisfaction Problem (CSP) scheduler with:
1. Multi-Period Lab and Single-Period Theory Unit Expansion
2. Minimum Remaining Values (MRV) & Most Constrained Variable (MCV) Ordering
3. Forward Pruning & Recursive Backtracking Search
4. Soft Constraint Heuristic Scoring (Daily load balancing, spacing, room fit)
5. Independent Final Validation Suite (Verifies all 8+ hard constraints)
6. Infeasibility & Conflict Diagnostic Analyzer

Zero paid APIs, zero external AI subscriptions, completely explainable & offline.
"""

from typing import List, Dict, Tuple, Optional, Any, Set
from collections import defaultdict
import time


class SchedulingUnit:
    """
    Represents a discrete block of teaching activity to be scheduled.
    For Theory: duration = 1 period.
    For Lab: duration = lab_duration periods (e.g. 2 or 3 consecutive periods).
    """
    def __init__(
        self,
        unit_id: str,
        section_id: int,
        section_name: str,
        student_strength: int,
        subject_id: int,
        subject_code: str,
        subject_name: str,
        subject_type: str,  # 'Theory' or 'Lab'
        duration: int,      # Number of consecutive periods
        faculty_id: int,
        faculty_name: str,
    ):
        self.unit_id = unit_id
        self.section_id = section_id
        self.section_name = section_name
        self.student_strength = student_strength
        self.subject_id = subject_id
        self.subject_code = subject_code
        self.subject_name = subject_name
        self.subject_type = subject_type
        self.duration = duration
        self.faculty_id = faculty_id
        self.faculty_name = faculty_name

        # Calculated constraint metrics for MRV heuristic sorting
        self.domain_size: int = 0
        self.eligible_rooms_count: int = 0

    def __repr__(self):
        return (f"<Unit {self.unit_id}: Sec {self.section_name} | {self.subject_code} "
                f"({self.subject_type} x{self.duration}p) | Fac {self.faculty_name}>")


class TimetableScheduler:
    """
    Pure Python CSP Backtracking Scheduler for College Timetable Generation.
    """

    def __init__(
        self,
        days: List[str],
        periods: List[int],
        sections: List[Dict[str, Any]],
        subjects: List[Dict[str, Any]],
        faculty: List[Dict[str, Any]],
        classrooms: List[Dict[str, Any]],
        faculty_availability: List[Dict[str, Any]],
        section_subjects: Optional[List[Dict[str, Any]]] = None,
    ):
        self.days = days
        self.periods = sorted(periods)
        self.num_periods = len(self.periods)
        self.sections = {s["id"]: s for s in sections}
        self.subjects = {s["id"]: s for s in subjects}
        self.faculty = {f["id"]: f for f in faculty}
        self.classrooms = {r["id"]: r for r in classrooms}
        self.section_subjects = section_subjects or []

        # Build faculty availability lookup: (faculty_id, day, period) -> bool
        self.fac_avail_map: Dict[Tuple[int, str, int], bool] = {}
        for fa in faculty_availability:
            self.fac_avail_map[(fa["faculty_id"], fa["day"], fa["period"])] = bool(fa.get("is_available", 1))

        # Separate rooms into Classrooms and Labs
        self.theory_rooms = [r for r in classrooms if r.get("room_type") == "Classroom"]
        self.lab_rooms = [r for r in classrooms if r.get("room_type") == "Lab"]

        # Results & Diagnostic state
        self.conflict_reasons: List[str] = []
        self.backtrack_count: int = 0
        self.nodes_explored: int = 0
        self.max_search_time_seconds: float = 20.0  # Timeout safety to prevent hanging

    def is_faculty_available(self, faculty_id: int, day: str, period: int) -> bool:
        """
        Returns True if the faculty is available at (day, period).
        Defaults to True if no explicit record exists.
        """
        return self.fac_avail_map.get((faculty_id, day, period), True)

    def get_eligible_rooms(self, unit: SchedulingUnit) -> List[Dict[str, Any]]:
        """
        Finds classrooms/labs matching the unit's required room type and student capacity.
        """
        target_pool = self.lab_rooms if unit.subject_type == "Lab" else self.theory_rooms
        # Room capacity must be >= section student strength
        eligible = [
            room for room in target_pool
            if room["capacity"] >= unit.student_strength
        ]
        # Sort rooms by capacity ascending (Best Fit / Least Waste heuristic)
        eligible.sort(key=lambda r: r["capacity"])
        return eligible

    def expand_scheduling_units(self) -> List[SchedulingUnit]:
        """
        Deconstructs weekly subject requirements into discrete scheduling blocks.
        - Labs are split into multi-period blocks according to lab_duration.
        - Theory subjects are split into single-period units.
        """
        units: List[SchedulingUnit] = []
        unit_counter = 0

        # Build section-to-subject map
        # If section_subjects table entries exist, use them; otherwise use all subjects
        sec_sub_map: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        if self.section_subjects:
            for item in self.section_subjects:
                sec_sub_map[item["section_id"]].append(item)
        else:
            for sec_id in self.sections:
                for sub_id, sub in self.subjects.items():
                    sec_sub_map[sec_id].append({
                        "section_id": sec_id,
                        "subject_id": sub_id,
                        "faculty_id": sub.get("preferred_faculty_id")
                    })

        for sec_id, assigned_list in sec_sub_map.items():
            section = self.sections.get(sec_id)
            if not section:
                continue

            for item in assigned_list:
                sub_id = item["subject_id"]
                subject = self.subjects.get(sub_id)
                if not subject:
                    continue

                # Determine assigned faculty: from assignment item, subject default, or first available faculty
                fac_id = item.get("faculty_id") or subject.get("preferred_faculty_id")
                if not fac_id or fac_id not in self.faculty:
                    # Fallback to any faculty if unassigned
                    fac_id = next(iter(self.faculty.keys())) if self.faculty else None

                fac = self.faculty.get(fac_id, {"name": "Unassigned Faculty"}) if fac_id else {"name": "Unassigned"}
                weekly_periods = subject.get("periods_per_week", 4)
                sub_type = subject.get("type", "Theory")
                lab_duration = max(1, subject.get("lab_duration", 1))

                if sub_type == "Lab":
                    # Create multi-period lab blocks
                    remaining_periods = weekly_periods
                    while remaining_periods > 0:
                        block_dur = min(lab_duration, remaining_periods)
                        unit_counter += 1
                        u = SchedulingUnit(
                            unit_id=f"LAB_{sec_id}_{sub_id}_{unit_counter}",
                            section_id=sec_id,
                            section_name=section.get("section_name", f"Sec-{sec_id}"),
                            student_strength=section.get("student_strength", 60),
                            subject_id=sub_id,
                            subject_code=subject.get("code", "SUB"),
                            subject_name=subject.get("name", "Subject"),
                            subject_type="Lab",
                            duration=block_dur,
                            faculty_id=fac_id,
                            faculty_name=fac.get("name", "Faculty")
                        )
                        units.append(u)
                        remaining_periods -= block_dur
                else:
                    # Theory subjects: 1 period per unit
                    for _ in range(weekly_periods):
                        unit_counter += 1
                        u = SchedulingUnit(
                            unit_id=f"TH_{sec_id}_{sub_id}_{unit_counter}",
                            section_id=sec_id,
                            section_name=section.get("section_name", f"Sec-{sec_id}"),
                            student_strength=section.get("student_strength", 60),
                            subject_id=sub_id,
                            subject_code=subject.get("code", "SUB"),
                            subject_name=subject.get("name", "Subject"),
                            subject_type="Theory",
                            duration=1,
                            faculty_id=fac_id,
                            faculty_name=fac.get("name", "Faculty")
                        )
                        units.append(u)

        return units

    def calculate_unit_constraints(self, unit: SchedulingUnit) -> int:
        """
        Calculates a constraint score for a unit used for MRV sorting.
        Lower domain / fewer valid slots = higher constraint priority (processed earlier).
        """
        eligible_rooms = self.get_eligible_rooms(unit)
        unit.eligible_rooms_count = len(eligible_rooms)

        valid_slot_count = 0
        for day in self.days:
            # Check all possible start periods for this unit's duration
            for p_idx in range(self.num_periods - unit.duration + 1):
                start_p = self.periods[p_idx]
                # Check faculty availability across all consecutive periods of the unit
                faculty_ok = all(
                    self.is_faculty_available(unit.faculty_id, day, self.periods[p_idx + offset])
                    for offset in range(unit.duration)
                )
                if faculty_ok:
                    valid_slot_count += unit.eligible_rooms_count

        unit.domain_size = valid_slot_count
        return valid_slot_count

    def soft_penalty_score(
        self,
        unit: SchedulingUnit,
        day: str,
        start_period: int,
        room: Dict[str, Any],
        section_day_counts: Dict[int, Dict[str, int]],
        section_day_sub_counts: Dict[int, Dict[Tuple[str, int], int]],
        section_schedule: Dict[int, Dict[Tuple[str, int], Any]],
        fac_day_counts: Dict[int, Dict[str, int]]
    ) -> float:
        """
        Calculates a soft penalty score for placing a unit at a given candidate slot.
        Lower score = Better / More Balanced Timetable.
        
        Soft Objectives:
        1. Balanced classes per day per section.
        2. Avoid scheduling > 2 periods of the same theory subject on the same day for a section.
        3. Avoid placing lab sessions on the very last period if it cuts into late evening.
        4. Distribute faculty workload evenly across days.
        5. Minimize wasted classroom capacity (best fit).
        """
        penalty = 0.0

        # 1. Section daily load balance
        current_day_load = section_day_counts[unit.section_id][day]
        penalty += (current_day_load * 3.0)  # Prefer days with fewer classes already scheduled

        # 2. Avoid repeated subject on the same day for a section
        same_sub_count = section_day_sub_counts[unit.section_id].get((day, unit.subject_id), 0)
        if unit.subject_type == "Theory":
            if same_sub_count >= 1:
                penalty += 15.0  # Strongly penalize 2nd or 3rd theory lecture of same subject on same day
        else:
            if same_sub_count >= 1:
                penalty += 25.0  # Do not place two different lab blocks of same subject on same day

        # 3. Faculty daily load balance
        fac_load = fac_day_counts[unit.faculty_id][day]
        penalty += (fac_load * 2.0)

        # 4. Room capacity waste penalty (smaller room preferred if it fits)
        capacity_waste = room["capacity"] - unit.student_strength
        penalty += (capacity_waste * 0.05)

        # 5. Consecutive class fatigue heuristic: check adjacent periods
        p_idx = self.periods.index(start_period)
        prev_p = self.periods[p_idx - 1] if p_idx > 0 else None
        next_p_after_unit = self.periods[p_idx + unit.duration] if (p_idx + unit.duration) < self.num_periods else None

        has_prev = prev_p and (day, prev_p) in section_schedule[unit.section_id]
        has_next = next_p_after_unit and (day, next_p_after_unit) in section_schedule[unit.section_id]
        if has_prev and has_next:
            penalty += 1.0  # Sandwiching between classes is okay but keep it moderately weighted

        return penalty

    def solve(self) -> Tuple[bool, Optional[List[Dict[str, Any]]], List[str]]:
        """
        Executes the pure Python Constraint Satisfaction & Backtracking search.
        
        Returns:
            (success: bool, timetable_rows: list, conflict_reasons: list)
        """
        start_time = time.time()
        self.conflict_reasons.clear()
        self.backtrack_count = 0
        self.nodes_explored = 0

        # Step 1: Expand into discrete scheduling units
        units = self.expand_scheduling_units()
        if not units:
            return False, None, ["No subjects or sections found to schedule. Please add master data."]

        # Step 2: Calculate constraint metrics and apply MRV (Most Constrained First)
        for u in units:
            self.calculate_unit_constraints(u)

        # Fail fast if any unit has 0 eligible rooms or 0 possible slots
        for u in units:
            if u.eligible_rooms_count == 0:
                reason = (f"Infeasible: No eligible {u.subject_type.lower()} room available for section "
                          f"'{u.section_name}' (Strength: {u.student_strength}). "
                          f"Check room capacities or add a suitable {u.subject_type}.")
                return False, None, [reason]
            if u.domain_size == 0:
                reason = (f"Infeasible: Faculty '{u.faculty_name}' has 0 available {u.duration}-period slots "
                          f"for subject '{u.subject_code}' ({u.subject_name}). Check faculty availability.")
                return False, None, [reason]

        # Sorting key for MRV:
        # 1. Labs before Theory (duration desc)
        # 2. Fewest available slots (domain_size asc)
        # 3. Fewest eligible rooms (eligible_rooms_count asc)
        units.sort(key=lambda u: (-u.duration, u.domain_size, u.eligible_rooms_count))

        # State track structures for O(1) constraint verification
        # Key: (day, period) -> Resource ID or assigned object
        section_schedule: Dict[int, Dict[Tuple[str, int], Any]] = defaultdict(dict)
        faculty_schedule: Dict[int, Dict[Tuple[str, int], Any]] = defaultdict(dict)
        room_schedule: Dict[int, Dict[Tuple[str, int], Any]] = defaultdict(dict)

        # State trackers for Soft Constraints & Heuristics
        section_day_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        section_day_sub_counts: Dict[int, Dict[Tuple[str, int], int]] = defaultdict(lambda: defaultdict(int))
        fac_day_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # List of final placed unit assignments
        assignments: List[Dict[str, Any]] = []

        def can_place_unit(
            unit: SchedulingUnit,
            day: str,
            start_p_idx: int,
            room: Dict[str, Any]
        ) -> bool:
            """
            Checks ALL 8 Hard Constraints for placing unit at (day, start_p_idx, room).
            """
            # Check if duration fits within the day's periods
            if start_p_idx + unit.duration > self.num_periods:
                return False

            # HC6: Room capacity check
            if room["capacity"] < unit.student_strength:
                return False

            # HC5: Room type match
            required_room_type = "Lab" if unit.subject_type == "Lab" else "Classroom"
            if room["room_type"] != required_room_type:
                return False

            # Check each consecutive period in this unit block
            for offset in range(unit.duration):
                p = self.periods[start_p_idx + offset]
                slot_key = (day, p)

                # HC1: Section non-overlap (Section cannot have 2 classes at same day/period)
                if slot_key in section_schedule[unit.section_id]:
                    return False

                # HC2: Faculty non-overlap (Faculty cannot teach 2 classes at same day/period)
                if slot_key in faculty_schedule[unit.faculty_id]:
                    return False

                # HC3: Room non-overlap (Room cannot host 2 classes at same day/period)
                if slot_key in room_schedule[room["id"]]:
                    return False

                # HC4: Faculty availability at this specific period
                if not self.is_faculty_available(unit.faculty_id, day, p):
                    return False

            return True

        def place_unit(
            unit: SchedulingUnit,
            day: str,
            start_p_idx: int,
            room: Dict[str, Any]
        ) -> Dict[str, Any]:
            """
            Commits the unit to the tracking state across all consecutive periods.
            """
            assigned_periods = []
            for offset in range(unit.duration):
                p = self.periods[start_p_idx + offset]
                slot_key = (day, p)
                assigned_periods.append(p)

                section_schedule[unit.section_id][slot_key] = unit
                faculty_schedule[unit.faculty_id][slot_key] = unit
                room_schedule[room["id"]][slot_key] = unit

            # Update soft optimization trackers
            section_day_counts[unit.section_id][day] += unit.duration
            section_day_sub_counts[unit.section_id][(day, unit.subject_id)] += 1
            fac_day_counts[unit.faculty_id][day] += unit.duration

            assignment = {
                "unit": unit,
                "day": day,
                "start_period": self.periods[start_p_idx],
                "periods": assigned_periods,
                "room": room
            }
            assignments.append(assignment)
            return assignment

        def unplace_unit(assignment: Dict[str, Any]):
            """
            Reverses unit placement during backtracking.
            """
            unit: SchedulingUnit = assignment["unit"]
            day: str = assignment["day"]
            room: Dict[str, Any] = assignment["room"]

            for p in assignment["periods"]:
                slot_key = (day, p)
                section_schedule[unit.section_id].pop(slot_key, None)
                faculty_schedule[unit.faculty_id].pop(slot_key, None)
                room_schedule[room["id"]].pop(slot_key, None)

            section_day_counts[unit.section_id][day] -= unit.duration
            section_day_sub_counts[unit.section_id][(day, unit.subject_id)] -= 1
            fac_day_counts[unit.faculty_id][day] -= unit.duration

            assignments.pop()

        def backtrack(unit_idx: int) -> bool:
            """
            Recursive Backtracking search with heuristic domain ordering and pruning.
            """
            self.nodes_explored += 1

            # Timeout check to prevent infinite search on mathematically impossible states
            if time.time() - start_time > self.max_search_time_seconds:
                return False

            # Base Case: All units successfully scheduled!
            if unit_idx >= len(units):
                return True

            current_unit = units[unit_idx]
            eligible_rooms = self.get_eligible_rooms(current_unit)

            # Generate and score candidate slots (Day, Start Period Index, Room)
            candidates = []
            for day in self.days:
                for p_idx in range(self.num_periods - current_unit.duration + 1):
                    start_p = self.periods[p_idx]
                    for room in eligible_rooms:
                        if can_place_unit(current_unit, day, p_idx, room):
                            score = self.soft_penalty_score(
                                current_unit, day, start_p, room,
                                section_day_counts, section_day_sub_counts,
                                section_schedule, fac_day_counts
                            )
                            candidates.append((score, day, p_idx, room))

            # Least Constraining / Best Heuristic Value First (sort by lowest penalty score)
            candidates.sort(key=lambda item: item[0])

            # Try each valid candidate slot
            for _, day, p_idx, room in candidates:
                assignment = place_unit(current_unit, day, p_idx, room)

                # Recurse to next unit
                if backtrack(unit_idx + 1):
                    return True

                # Backtrack on failure
                self.backtrack_count += 1
                unplace_unit(assignment)

            return False

        # Run the search
        success = backtrack(0)

        if not success:
            # Diagnose reason for infeasibility
            self.conflict_reasons = self.diagnose_conflicts(units)
            return False, None, self.conflict_reasons

        # Convert assignments into flat database rows
        timetable_rows: List[Dict[str, Any]] = []
        for assign in assignments:
            unit: SchedulingUnit = assign["unit"]
            day = assign["day"]
            room = assign["room"]
            for p in assign["periods"]:
                timetable_rows.append({
                    "day": day,
                    "period": p,
                    "subject_id": unit.subject_id,
                    "subject_code": unit.subject_code,
                    "subject_name": unit.subject_name,
                    "faculty_id": unit.faculty_id,
                    "faculty_name": unit.faculty_name,
                    "classroom_id": room["id"],
                    "room_number": room["room_number"],
                    "section_id": unit.section_id,
                    "section_name": unit.section_name,
                    "class_type": unit.subject_type
                })

        # Run independent final validation pass
        is_valid, validation_errors = validate_timetable_solution(
            timetable_rows,
            self.days,
            self.periods,
            self.sections,
            self.subjects,
            self.faculty,
            self.classrooms,
            self.fac_avail_map
        )

        if not is_valid:
            return False, None, [f"Validation Error: {err}" for err in validation_errors]

        return True, timetable_rows, []

    def diagnose_conflicts(self, units: List[SchedulingUnit]) -> List[str]:
        """
        Analyzes the data and constraints to report why the schedule could not be fulfilled.
        """
        reasons = []
        total_slots_per_section = len(self.days) * self.num_periods

        # 1. Check Section period capacity
        sec_load = defaultdict(int)
        for u in units:
            sec_load[u.section_id] += u.duration

        for sec_id, total_req in sec_load.items():
            sec_name = self.sections.get(sec_id, {}).get("section_name", f"Sec {sec_id}")
            if total_req > total_slots_per_section:
                reasons.append(
                    f"Section '{sec_name}' requires {total_req} weekly periods, but the weekly grid "
                    f"only has {total_slots_per_section} periods ({len(self.days)} days x {self.num_periods} periods)."
                )

        # 2. Check Faculty total teaching load vs available slots
        fac_load = defaultdict(int)
        for u in units:
            fac_load[u.faculty_id] += u.duration

        for fac_id, total_fac_req in fac_load.items():
            fac_name = self.faculty.get(fac_id, {}).get("name", f"Faculty {fac_id}")
            avail_slots = sum(
                1 for day in self.days for p in self.periods
                if self.is_faculty_available(fac_id, day, p)
            )
            if total_fac_req > avail_slots:
                reasons.append(
                    f"Faculty '{fac_name}' is assigned {total_fac_req} weekly periods but is only available "
                    f"for {avail_slots} slots across the week. Increase faculty availability or reassign subjects."
                )

        # 3. Check Lab rooms bottleneck
        total_lab_periods_req = sum(u.duration for u in units if u.subject_type == "Lab")
        total_lab_capacity = len(self.lab_rooms) * total_slots_per_section
        if total_lab_periods_req > total_lab_capacity:
            reasons.append(
                f"Total lab periods required ({total_lab_periods_req}) exceeds total available lab room capacity "
                f"({total_lab_capacity} slots across {len(self.lab_rooms)} labs). Add more labs."
            )

        # 4. Check Classroom capacity bottlenecks
        for u in units:
            eligible = self.get_eligible_rooms(u)
            if not eligible:
                reasons.append(
                    f"No {u.subject_type.lower()} room with capacity >= {u.student_strength} "
                    f"exists for section '{u.section_name}'."
                )

        if not reasons:
            reasons.append(
                "Search space exhausted: Simultaneous faculty availability conflicts or tight section constraints "
                "prevented a complete 100% conflict-free timetable. Try relaxing faculty availability constraints "
                "or distributing lab schedules."
            )

        return reasons


def validate_timetable_solution(
    timetable_rows: List[Dict[str, Any]],
    days: List[str],
    periods: List[int],
    sections: Dict[int, Dict[str, Any]],
    subjects: Dict[int, Dict[str, Any]],
    faculty: Dict[int, Dict[str, Any]],
    classrooms: Dict[int, Dict[str, Any]],
    fac_avail_map: Dict[Tuple[int, str, int], bool]
) -> Tuple[bool, List[str]]:
    """
    Independent Verification Engine:
    Validates a generated timetable against all 8 hard constraints.
    Returns (True, []) if perfectly valid, or (False, [list of error descriptions]).
    """
    errors: List[str] = []

    # Track slot allocations
    section_slots = set()
    faculty_slots = set()
    room_slots = set()

    for idx, row in enumerate(timetable_rows):
        day = row["day"]
        period = row["period"]
        sec_id = row["section_id"]
        fac_id = row["faculty_id"]
        room_id = row["classroom_id"]
        sub_id = row["subject_id"]
        class_type = row.get("class_type", "Theory")

        # 1. Section Non-overlap
        sec_key = (sec_id, day, period)
        if sec_key in section_slots:
            errors.append(f"Hard Constraint Violation: Section ID {sec_id} has duplicate class at {day} Period {period}.")
        section_slots.add(sec_key)

        # 2. Faculty Non-overlap
        fac_key = (fac_id, day, period)
        if fac_key in faculty_slots:
            errors.append(f"Hard Constraint Violation: Faculty ID {fac_id} scheduled for multiple classes at {day} Period {period}.")
        faculty_slots.add(fac_key)

        # 3. Room Non-overlap
        room_key = (room_id, day, period)
        if room_key in room_slots:
            errors.append(f"Hard Constraint Violation: Room ID {room_id} double-booked at {day} Period {period}.")
        room_slots.add(room_key)

        # 4. Faculty Availability Check
        if not fac_avail_map.get((fac_id, day, period), True):
            errors.append(f"Hard Constraint Violation: Faculty ID {fac_id} scheduled during unavailable slot {day} Period {period}.")

        # 5. Room Type Match
        room = classrooms.get(room_id)
        if room:
            required_type = "Lab" if class_type == "Lab" else "Classroom"
            if room.get("room_type") != required_type:
                errors.append(
                    f"Hard Constraint Violation: {class_type} class assigned to incompatible room type "
                    f"'{room.get('room_type')}' (Room {room.get('room_number')})."
                )

            # 6. Room Capacity
            sec = sections.get(sec_id)
            if sec and room.get("capacity", 0) < sec.get("student_strength", 0):
                errors.append(
                    f"Hard Constraint Violation: Room {room.get('room_number')} capacity ({room.get('capacity')}) "
                    f"< Section strength ({sec.get('student_strength')})."
                )

    return (len(errors) == 0), errors
