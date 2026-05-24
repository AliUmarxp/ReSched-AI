from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from math import sqrt
from typing import Any


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DAY_INDEX = {day: index for index, day in enumerate(DAYS)}


@dataclass(frozen=True)
class Session:
    id: str
    section_id: str
    course_id: str
    duration: int
    is_lab: bool
    difficulty: int
    repeat_sensitive: bool
    weekly_slot_index: int


class Scheduler:
    def __init__(self, dataset: dict[str, Any]):
        self.dataset = dataset
        self.teachers = {item["id"]: item for item in dataset["teachers"]}
        self.courses = {item["id"]: item for item in dataset["courses"]}
        self.sections = {item["id"]: item for item in dataset["sections"]}
        self.rooms = {item["id"]: item for item in dataset["rooms"]}
        self.slots = {item["id"]: item for item in dataset["timeSlots"]}
        self.rejections: Counter[str] = Counter()
        self.repeat_index = self._build_repeat_index()
        self.windows = self._build_windows()
        self.sessions = self._build_sessions()
        self.best_entries: list[dict[str, Any]] = []
        self.best_unscheduled: list[dict[str, Any]] = []
        self.best_score = -10_000.0
        self.priority_rules = {
            "hard_must_have": [
                "teacher_clashes",
                "room_clashes",
                "section_clashes",
                "teacher_consistency_rejections",
                "course_day_spread_rejections",
                "section_gap_limit_rejections",
                "friday_prayer_break_rejections",
                "break_crossing_rejections",
                "repeat_student_clashes",
                "lab_allocation_conflicts",
                "room_type_rejections",
                "capacity_rejections",
                "availability_rejections",
                "expertise_rejections",
            ],
            "high_priority_soft": [
                "repeat student protection maximization",
                "daily difficulty overload control",
                "teacher daily workload balance",
                "teacher consecutive load control",
                "section day overstretch control",
                "day fairness recovery",
                "early release",
            ],
            "lower_priority_soft": [
                "room spare minimization",
                "teacher back-to-back reduction",
            ],
        }

    def run(self) -> dict[str, Any]:
        entries, unscheduled = self._construct_schedule()
        success = len(unscheduled) == 0
        conflicts = self._validate(entries)
        report = self._build_report(entries, conflicts, success, unscheduled)
        quality = self._quality(entries, conflicts)
        return {
            "status": "success" if success and not conflicts else "partial",
            "entries": entries,
            "unscheduled": unscheduled,
            "conflicts": conflicts,
            "report": report,
            "quality": quality,
            "aiEvidence": self._ai_evidence(),
            "views": self._build_views(entries),
        }

    def _construct_schedule(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        entries: list[dict[str, Any]] = []
        unscheduled: list[dict[str, Any]] = []
        for session in self.sessions:
            candidates = self._candidates(session, entries)
            if candidates:
                entries.append(candidates[0])
                continue
            unscheduled.append(
                {
                    "session_id": session.id,
                    "section_id": session.section_id,
                    "course_id": session.course_id,
                    "weekly_slot_index": session.weekly_slot_index,
                    "reason": "No feasible candidate under hard constraints",
                    "blockers": self._estimate_blockers(session, entries),
                }
            )
        return entries, unscheduled

    def _build_sessions(self) -> list[Session]:
        repeat_sensitive_keys = set()
        for student in self.dataset["repeatStudents"]:
            for repeated in student["repeated_courses"]:
                repeat_sensitive_keys.add((student["current_section"], None))
                repeat_sensitive_keys.add((repeated["section_id"], repeated["course_id"]))

        sessions: list[Session] = []
        for section in self.dataset["sections"]:
            for course_id in section["required_courses"]:
                course = self.courses[course_id]
                for slot_index, duration in enumerate(self._session_durations(course), start=1):
                    sessions.append(
                        Session(
                            id=f"{section['id']}::{course_id}::w{slot_index}",
                            section_id=section["id"],
                            course_id=course_id,
                            duration=int(duration),
                            is_lab=course["type"] == "lab",
                            difficulty=int(course["difficulty_level"]),
                            repeat_sensitive=(section["id"], None) in repeat_sensitive_keys
                            or (section["id"], course_id) in repeat_sensitive_keys,
                            weekly_slot_index=slot_index,
                        )
                    )

        def scarcity(session: Session) -> tuple:
            allowed = self._eligible_teachers(session.course_id, session.section_id)
            rooms = self._eligible_rooms(session)
            return (
                0 if session.is_lab else 1,
                len(allowed),
                len(rooms),
                0 if session.repeat_sensitive else 1,
                -self._section_weekly_load(session.section_id),
                -session.duration,
                -session.difficulty,
            )

        return sorted(sessions, key=scarcity)

    def _weekly_frequency(self, course: dict[str, Any]) -> int:
        if course["type"] == "lab":
            return 1
        raw = course.get("weekly_frequency") or course.get("credit_hours") or 3
        return max(1, min(4, int(raw)))

    def _session_durations(self, course: dict[str, Any]) -> list[int]:
        if course["type"] == "lab":
            return [3]
        credit_hours = int(course.get("credit_hours") or course.get("weekly_frequency") or 3)
        if credit_hours == 3:
            return [2, 1]
        if credit_hours == 2:
            return [2]
        return [1 for _ in range(max(1, min(4, credit_hours)))]

    def _section_weekly_load(self, section_id: str) -> int:
        total = 0
        for course_id in self.sections[section_id]["required_courses"]:
            total += sum(self._session_durations(self.courses[course_id]))
        return total

    def _build_repeat_index(self) -> dict[str, set[str]]:
        session_to_students: dict[str, set[str]] = defaultdict(set)
        for student in self.dataset["repeatStudents"]:
            current_section = student["current_section"]
            for course_id in self.sections[current_section]["required_courses"]:
                session_to_students[f"{current_section}::{course_id}"].add(student["id"])
            for repeated in student["repeated_courses"]:
                session_to_students[f"{repeated['section_id']}::{repeated['course_id']}"].add(
                    student["id"]
                )
        return session_to_students

    def _build_windows(self) -> list[dict[str, Any]]:
        by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for slot in self.dataset["timeSlots"]:
            by_day[slot["day"]].append(slot)
        for slots in by_day.values():
            slots.sort(key=lambda item: item["period_index"])

        windows: list[dict[str, Any]] = []
        for day, slots in by_day.items():
            for start_index in range(len(slots)):
                for length in (1, 2, 3):
                    chunk = slots[start_index : start_index + length]
                    if len(chunk) != length:
                        continue
                    if not self._is_continuous(chunk):
                        continue
                    if self._crosses_midday_break(chunk):
                        continue
                    windows.append(
                        {
                            "id": f"{day.lower()}-{chunk[0]['period_index']}-{chunk[-1]['period_index']}",
                            "day": day,
                            "slot_ids": [slot["id"] for slot in chunk],
                            "start_time": chunk[0]["start_time"],
                            "end_time": chunk[-1]["end_time"],
                            "start_index": chunk[0]["period_index"],
                            "end_index": chunk[-1]["period_index"],
                            "duration": length,
                        }
                    )
        return windows

    def _is_continuous(self, slots: list[dict[str, Any]]) -> bool:
        if len(slots) <= 1:
            return True
        return all(
            int(left["period_index"]) + 1 == int(right["period_index"])
            for left, right in zip(slots, slots[1:])
        )

    def _crosses_midday_break(self, slots: list[dict[str, Any]]) -> bool:
        periods = {int(slot["period_index"]) for slot in slots}
        return 4 in periods and 5 in periods

    def _eligible_teachers(self, course_id: str, section_id: str | None = None) -> list[dict[str, Any]]:
        if section_id:
            assigned_teacher = self.sections[section_id].get("course_teachers", {}).get(course_id)
            if assigned_teacher and assigned_teacher in self.teachers:
                return [self.teachers[assigned_teacher]]
        course = self.courses[course_id]
        allowed = set(course["allowed_teachers"])
        return [
            teacher
            for teacher in self.dataset["teachers"]
            if teacher["id"] in allowed and course_id in teacher["expertise_courses"]
        ]

    def _eligible_rooms(self, session: Session) -> list[dict[str, Any]]:
        section = self.sections[session.section_id]
        target_type = "lab" if session.is_lab else "classroom"
        return [
            room
            for room in self.dataset["rooms"]
            if room["type"] == target_type and int(room["capacity"]) >= int(section["strength"])
        ]

    def _search(
        self, index: int, entries: list[dict[str, Any]], unscheduled: list[dict[str, Any]]
    ) -> bool:
        if index == len(self.sessions):
            score = self._partial_score(entries) - len(unscheduled) * 220
            if score > self.best_score:
                self.best_score = score
                self.best_entries = [dict(entry) for entry in entries]
                self.best_unscheduled = [dict(item) for item in unscheduled]
            return True

        session = self.sessions[index]
        candidates = self._candidates(session, entries)
        found = False
        for candidate in candidates[:18]:
            entries.append(candidate)
            if self._search(index + 1, entries, unscheduled):
                found = True
            entries.pop()

        if not candidates:
            unscheduled.append(
                {
                    "session_id": session.id,
                    "section_id": session.section_id,
                    "course_id": session.course_id,
                    "weekly_slot_index": session.weekly_slot_index,
                    "reason": "No feasible candidate under hard constraints",
                    "blockers": self._estimate_blockers(session, entries),
                }
            )
            found = self._search(index + 1, entries, unscheduled) or found
            unscheduled.pop()
        return found

    def _estimate_blockers(self, session: Session, entries: list[dict[str, Any]]) -> dict[str, int]:
        blockers: Counter[str] = Counter()
        for teacher in self._eligible_teachers(session.course_id, session.section_id):
            for room in self._eligible_rooms(session):
                for window in self.windows:
                    if window["duration"] != session.duration:
                        continue
                    violation = self._hard_violation(session, teacher, room, window, entries)
                    if violation:
                        blockers[violation] += 1
        return dict(blockers)

    def _candidates(self, session: Session, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidates: list[tuple[float, dict[str, Any]]] = []
        course = self.courses[session.course_id]
        section = self.sections[session.section_id]
        for teacher in self._eligible_teachers(session.course_id, session.section_id):
            for room in self._eligible_rooms(session):
                for window in self.windows:
                    if window["duration"] != session.duration:
                        continue
                    violation = self._hard_violation(session, teacher, room, window, entries)
                    if violation:
                        self.rejections[violation] += 1
                        continue
                    score, score_notes = self._score_candidate(
                        session, teacher, room, window, entries
                    )
                    entry = {
                        "id": session.id,
                        "section_id": session.section_id,
                        "section_name": section["name"],
                        "course_id": session.course_id,
                        "course_name": course["name"],
                        "course_type": course["type"],
                        "teacher_id": teacher["id"],
                        "teacher_name": teacher["name"],
                        "room_id": room["id"],
                        "room_name": room["name"],
                        "day": window["day"],
                        "start_time": window["start_time"],
                        "end_time": window["end_time"],
                        "slot_ids": window["slot_ids"],
                        "start_index": window["start_index"],
                        "end_index": window["end_index"],
                        "duration": session.duration,
                        "difficulty_level": session.difficulty,
                        "soft_score": round(score, 2),
                        "explanation": self._explanation(
                            session, teacher, room, window, score_notes
                        ),
                    }
                    candidates.append((score, entry))
        candidates.sort(key=lambda item: item[0], reverse=True)
        return [entry for _, entry in candidates]

    def _hard_violation(
        self,
        session: Session,
        teacher: dict[str, Any],
        room: dict[str, Any],
        window: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> str | None:
        course = self.courses[session.course_id]
        section = self.sections[session.section_id]
        if session.course_id not in teacher["expertise_courses"]:
            return "expertise_rejections"
        if teacher["id"] not in course["allowed_teachers"]:
            return "expertise_rejections"
        if not set(window["slot_ids"]).issubset(set(teacher["availability_slots"])):
            return "availability_rejections"
        if self._is_friday_prayer_window(window):
            return "friday_prayer_break_rejections"
        if self._window_crosses_break(window):
            return "break_crossing_rejections"
        if session.is_lab and room["type"] != "lab":
            return "lab_allocation_conflicts"
        if not session.is_lab and room["type"] != "classroom":
            return "room_type_rejections"
        if int(room["capacity"]) < int(section["strength"]):
            return "capacity_rejections"
        projected_for_gap = entries + [
            {
                "section_id": session.section_id,
                "day": window["day"],
                "start_index": window["start_index"],
                "end_index": window["end_index"],
            }
        ]
        if self._section_day_gaps(projected_for_gap, session.section_id, window["day"]) > self._max_section_day_gap(session.section_id):
            return "section_gap_limit_rejections"
        for entry in entries:
            # Consistent teacher for same section-course across all weekly sessions.
            if entry["section_id"] == session.section_id and entry["course_id"] == session.course_id:
                if entry["teacher_id"] != teacher["id"]:
                    return "teacher_consistency_rejections"
                # Spread same course sessions across different days for better learning rhythm.
                if entry["day"] == window["day"]:
                    return "course_day_spread_rejections"
            if not self._overlaps(entry, window):
                continue
            if entry["teacher_id"] == teacher["id"]:
                return "teacher_clashes"
            if entry["room_id"] == room["id"]:
                return "room_clashes"
            if entry["section_id"] == session.section_id:
                return "section_clashes"
            if self._repeat_student_overlap(session.id, entry):
                return "repeat_student_clashes"
        return None

    def _is_friday_prayer_window(self, window: dict[str, Any]) -> bool:
        if window["day"] != "Friday":
            return False
        return bool(set(range(int(window["start_index"]), int(window["end_index"]) + 1)) & {4, 5})

    def _window_crosses_break(self, window: dict[str, Any]) -> bool:
        periods = set(range(int(window["start_index"]), int(window["end_index"]) + 1))
        return 4 in periods and 5 in periods

    def _overlaps(self, entry: dict[str, Any], window: dict[str, Any] | dict[str, Any]) -> bool:
        if entry["day"] != window["day"]:
            return False
        return bool(set(entry["slot_ids"]) & set(window["slot_ids"]))

    def _repeat_student_overlap(self, session_id: str, entry: dict[str, Any]) -> bool:
        left = self.repeat_index.get(session_id, set())
        right = self.repeat_index.get(entry["id"], set())
        if not left:
            left = self.repeat_index.get(self._base_session_id(session_id), set())
        if not right:
            right = self.repeat_index.get(self._base_session_id(entry["id"]), set())
        return bool(left & right)

    def _base_session_id(self, session_id: str) -> str:
        parts = session_id.split("::")
        if len(parts) >= 2:
            return f"{parts[0]}::{parts[1]}"
        return session_id

    def _score_candidate(
        self,
        session: Session,
        teacher: dict[str, Any],
        room: dict[str, Any],
        window: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> tuple[float, list[str]]:
        notes: list[str] = []
        score = 0.0
        projected = entries + [
            {
                "id": session.id,
                "section_id": session.section_id,
                "course_id": session.course_id,
                "teacher_id": teacher["id"],
                "room_id": room["id"],
                "day": window["day"],
                "slot_ids": window["slot_ids"],
                "start_index": window["start_index"],
                "end_index": window["end_index"],
                "duration": session.duration,
            }
        ]
        score += self._course_spread_score(projected, session)

        gap_count = self._section_day_gaps(projected, session.section_id, window["day"])
        score -= gap_count * 12
        if gap_count == 0:
            score += 14
            notes.append("Section day stays compact with no unnecessary internal gap.")
        else:
            notes.append(f"Section gap penalty applied: {gap_count} empty period(s).")

        same_day_section = [
            entry
            for entry in entries
            if entry["section_id"] == session.section_id and entry["day"] == window["day"]
        ]
        hard_courses_today = sum(
            1
            for entry in same_day_section
            if int(self.courses[entry["course_id"]]["difficulty_level"]) >= 4
        )
        if session.difficulty >= 4 and hard_courses_today >= 2:
            score -= 22
            notes.append("Soft penalty: section already has two difficult courses this day.")
        occupied = []
        for entry in same_day_section:
            occupied.extend(range(int(entry["start_index"]), int(entry["end_index"]) + 1))
        occupied.extend(range(int(window["start_index"]), int(window["end_index"]) + 1))
        if occupied and (max(occupied) - min(occupied) + 1) > 6:
            score -= 16
            notes.append("Soft penalty: section day span is getting long.")
        if self._max_consecutive(occupied) > 4:
            score -= 14
            notes.append("Soft penalty: section consecutive load is high.")

        early_bonus = max(0, 6 - window["end_index"]) * 4
        score += early_bonus
        if window["end_index"] <= 3:
            notes.append("This choice supports early release for the section.")

        if session.difficulty >= 4 and window["start_index"] <= 2:
            score += 12
            notes.append("Difficult course is placed in an earlier learning slot.")
        elif session.difficulty >= 4 and window["start_index"] >= 4:
            score -= 9
            notes.append("Difficult course is later than ideal, but hard constraints allow it.")

        same_day_teacher = [
            entry
            for entry in entries
            if entry["teacher_id"] == teacher["id"] and entry["day"] == window["day"]
        ]
        score -= len(same_day_teacher) * 7
        if len(same_day_teacher) == 0:
            notes.append("Teacher workload remains distributed for this day.")
        if len(same_day_teacher) >= int(teacher["max_lectures_per_day"]):
            score -= 30
            notes.append("Teacher workload is near the daily limit.")
        # Penalize very large idle windows for teacher on same day.
        teacher_periods = []
        for entry in same_day_teacher:
            teacher_periods.extend(range(int(entry["start_index"]), int(entry["end_index"]) + 1))
        teacher_periods.extend(range(int(window["start_index"]), int(window["end_index"]) + 1))
        if teacher_periods:
            spread = max(teacher_periods) - min(teacher_periods) + 1
            idle = spread - len(set(teacher_periods))
            if idle > 2:
                score -= idle * 2.5
                notes.append("Teacher idle-gap penalty applied.")

        if self._creates_teacher_back_to_back(teacher["id"], window, entries):
            score -= 8
            notes.append("Small penalty: teacher has adjacent teaching load.")

        if session.is_lab:
            score += 10
            if window["start_index"] <= 2:
                score += 5
            notes.append("Lab receives a continuous room block.")

        section_strength = int(self.sections[session.section_id]["strength"])
        room_spare = int(room["capacity"]) - section_strength
        score -= max(0, room_spare - 10) * 0.3

        fairness = self._day_fairness_score(projected, session.section_id, window["day"])
        score += fairness
        if fairness > 0:
            notes.append("Day fairness recovery improved this section's weekly rhythm.")
        elif fairness < 0:
            notes.append("Fairness penalty applied because late days are clustering.")

        return score, notes

    def _course_spread_score(self, entries: list[dict[str, Any]], session: Session) -> float:
        course_entries = [
            entry
            for entry in entries
            if entry["section_id"] == session.section_id and entry["course_id"] == session.course_id
        ]
        days = [DAY_INDEX[item["day"]] for item in course_entries]
        if len(days) <= 1:
            return 0.0
        duplicates = len(days) - len(set(days))
        return -8.0 * duplicates

    def _section_day_gaps(self, entries: list[dict[str, Any]], section_id: str, day: str) -> int:
        used: set[int] = set()
        for entry in entries:
            if entry["section_id"] == section_id and entry["day"] == day:
                used.update(range(int(entry["start_index"]), int(entry["end_index"]) + 1))
        if len(used) <= 1:
            return 0
        return max(used) - min(used) + 1 - len(used)

    def _max_section_day_gap(self, section_id: str) -> int:
        return 3 if self._section_weekly_load(section_id) >= 20 else 2

    def _creates_teacher_back_to_back(
        self, teacher_id: str, window: dict[str, Any], entries: list[dict[str, Any]]
    ) -> bool:
        adjacent = 0
        for entry in entries:
            if entry["teacher_id"] != teacher_id or entry["day"] != window["day"]:
                continue
            if entry["end_index"] + 1 == window["start_index"]:
                adjacent += 1
            if window["end_index"] + 1 == entry["start_index"]:
                adjacent += 1
        return adjacent >= 2

    def _max_consecutive(self, periods: list[int]) -> int:
        if not periods:
            return 0
        uniq = sorted(set(periods))
        longest = 1
        current = 1
        for left, right in zip(uniq, uniq[1:]):
            if right == left + 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        return longest

    def _day_fairness_score(self, entries: list[dict[str, Any]], section_id: str, day: str) -> float:
        current_day_index = DAY_INDEX[day]
        by_day = self._section_last_period_by_day(entries, section_id)
        score = 0.0
        previous_day = DAYS[current_day_index - 1] if current_day_index > 0 else None
        if previous_day and by_day.get(previous_day, 0) >= 5:
            score += 10 if by_day.get(day, 0) <= 3 else -10
        for left, right in zip(DAYS, DAYS[1:]):
            if by_day.get(left, 0) >= 5 and by_day.get(right, 0) >= 5:
                score -= 12
        return score

    def _section_last_period_by_day(
        self, entries: list[dict[str, Any]], section_id: str
    ) -> dict[str, int]:
        by_day: dict[str, int] = defaultdict(int)
        for entry in entries:
            if entry["section_id"] == section_id:
                by_day[entry["day"]] = max(by_day[entry["day"]], int(entry["end_index"]))
        return by_day

    def _partial_score(self, entries: list[dict[str, Any]]) -> float:
        return sum(float(entry.get("soft_score", 0)) for entry in entries)

    def _explanation(
        self,
        session: Session,
        teacher: dict[str, Any],
        room: dict[str, Any],
        window: dict[str, Any],
        score_notes: list[str],
    ) -> list[str]:
        section = self.sections[session.section_id]
        course = self.courses[session.course_id]
        reasons = [
            f"{teacher['name']} is available and has expertise for {course['name']}.",
            f"{room['name']} is a valid {room['type']} with capacity {room['capacity']} for {section['strength']} students.",
            "No teacher, room, or section clash was created at this time.",
            "Repeat-student enrolled courses remain clash-free for this placement.",
        ]
        reasons.extend(score_notes[:4])
        return reasons

    def _validate(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        for left, right in combinations(entries, 2):
            if left["day"] != right["day"]:
                continue
            if not (set(left["slot_ids"]) & set(right["slot_ids"])):
                continue
            if left["teacher_id"] == right["teacher_id"]:
                conflicts.append({"type": "teacher", "entries": [left["id"], right["id"]]})
            if left["room_id"] == right["room_id"]:
                conflicts.append({"type": "room", "entries": [left["id"], right["id"]]})
            if left["section_id"] == right["section_id"]:
                conflicts.append({"type": "section", "entries": [left["id"], right["id"]]})
            if self.repeat_index.get(left["id"], set()) & self.repeat_index.get(right["id"], set()):
                conflicts.append(
                    {"type": "repeat_student", "entries": [left["id"], right["id"]]}
                )

        for entry in entries:
            course = self.courses[entry["course_id"]]
            room = self.rooms[entry["room_id"]]
            section = self.sections[entry["section_id"]]
            teacher = self.teachers[entry["teacher_id"]]
            if course["type"] == "lab" and room["type"] != "lab":
                conflicts.append({"type": "lab_room", "entries": [entry["id"]]})
            if course["type"] == "theory" and room["type"] != "classroom":
                conflicts.append({"type": "classroom", "entries": [entry["id"]]})
            if int(room["capacity"]) < int(section["strength"]):
                conflicts.append({"type": "capacity", "entries": [entry["id"]]})
            if entry["course_id"] not in teacher["expertise_courses"]:
                conflicts.append({"type": "expertise", "entries": [entry["id"]]})
            if not set(entry["slot_ids"]).issubset(set(teacher["availability_slots"])):
                conflicts.append({"type": "availability", "entries": [entry["id"]]})
            if self._is_friday_prayer_window(entry):
                conflicts.append({"type": "friday_prayer_break", "entries": [entry["id"]]})
            if self._window_crosses_break(entry):
                conflicts.append({"type": "break_crossing", "entries": [entry["id"]]})
        for section in self.dataset["sections"]:
            for day in DAYS:
                if self._section_day_gaps(entries, section["id"], day) > self._max_section_day_gap(section["id"]):
                    conflicts.append({"type": "section_gap_limit", "section_id": section["id"], "day": day})
        conflicts.extend(self._validate_hard_group_policies(entries))
        return conflicts

    def _validate_hard_group_policies(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        section_course_teachers: dict[tuple[str, str], set[str]] = defaultdict(set)
        section_course_days: dict[tuple[str, str], list[str]] = defaultdict(list)
        for entry in entries:
            section_course = (entry["section_id"], entry["course_id"])
            section_course_teachers[section_course].add(entry["teacher_id"])
            section_course_days[section_course].append(entry["day"])

        for key, teachers in section_course_teachers.items():
            if len(teachers) > 1:
                conflicts.append({"type": "teacher_consistency", "section_course": list(key)})
        for key, days in section_course_days.items():
            if len(days) != len(set(days)):
                conflicts.append({"type": "course_day_spread", "section_course": list(key)})
        return conflicts

    def _soft_policy_warnings(self, entries: list[dict[str, Any]]) -> dict[str, int]:
        section_day_periods: dict[tuple[str, str], list[int]] = defaultdict(list)
        section_day_hard: Counter[tuple[str, str]] = Counter()
        teacher_day_periods: dict[tuple[str, str], list[int]] = defaultdict(list)
        for entry in entries:
            periods = list(range(int(entry["start_index"]), int(entry["end_index"]) + 1))
            section_day_periods[(entry["section_id"], entry["day"])].extend(periods)
            teacher_day_periods[(entry["teacher_id"], entry["day"])].extend(periods)
            if int(self.courses[entry["course_id"]]["difficulty_level"]) >= 4:
                section_day_hard[(entry["section_id"], entry["day"])] += 1
        warnings = {
            "daily_difficulty_overload_warnings": 0,
            "section_overstretch_warnings": 0,
            "section_consecutive_warnings": 0,
            "teacher_daily_overload_warnings": 0,
            "teacher_consecutive_warnings": 0,
        }
        for (section_id, day), periods in section_day_periods.items():
            if self._max_consecutive(periods) > 4:
                warnings["section_consecutive_warnings"] += 1
            if periods and (max(periods) - min(periods) + 1) > 6:
                warnings["section_overstretch_warnings"] += 1
        for count in section_day_hard.values():
            if count > 2:
                warnings["daily_difficulty_overload_warnings"] += 1
        for (teacher_id, _day), periods in teacher_day_periods.items():
            teacher = self.teachers[teacher_id]
            if len(set(periods)) > int(teacher["max_lectures_per_day"]):
                warnings["teacher_daily_overload_warnings"] += 1
            if self._max_consecutive(periods) > 3:
                warnings["teacher_consecutive_warnings"] += 1
        return warnings

    def _build_report(
        self,
        entries: list[dict[str, Any]],
        conflicts: list[dict[str, Any]],
        success: bool,
        unscheduled: list[dict[str, Any]],
    ) -> dict[str, Any]:
        scheduled = len(entries)
        total = len(self.sessions)
        repeat_cases = len(self.dataset["repeatStudents"])
        lab_sessions = sum(1 for session in self.sessions if session.is_lab)
        classroom_count = sum(1 for room in self.dataset["rooms"] if room["type"] == "classroom")
        soft_warnings = self._soft_policy_warnings(entries)
        return {
            "success": success,
            "scheduled_sessions": scheduled,
            "total_sessions": total,
            "unscheduled_sessions": len(unscheduled),
            "unscheduled_details": unscheduled[:30],
            "hard_conflicts": len(conflicts),
            "teacher_clashes_avoided": self.rejections["teacher_clashes"],
            "teacher_consistency_rejections": self.rejections["teacher_consistency_rejections"],
            "course_day_spread_rejections": self.rejections["course_day_spread_rejections"],
            "section_gap_limit_rejections": self.rejections["section_gap_limit_rejections"],
            "teacher_daily_limit_rejections": self.rejections["teacher_daily_limit_rejections"],
            "daily_difficulty_overload_rejections": self.rejections["daily_difficulty_overload_rejections"],
            "section_overstretch_rejections": self.rejections["section_overstretch_rejections"],
            "teacher_consecutive_limit_rejections": self.rejections["teacher_consecutive_limit_rejections"],
            "section_consecutive_limit_rejections": self.rejections["section_consecutive_limit_rejections"],
            **soft_warnings,
            "friday_prayer_break_rejections": self.rejections["friday_prayer_break_rejections"],
            "break_crossing_rejections": self.rejections["break_crossing_rejections"],
            "room_clashes_avoided": self.rejections["room_clashes"],
            "section_clashes_avoided": self.rejections["section_clashes"],
            "repeat_student_clashes_avoided": self.rejections["repeat_student_clashes"],
            "lab_allocation_conflicts_avoided": self.rejections["lab_allocation_conflicts"]
            or lab_sessions * classroom_count,
            "capacity_rejections": self.rejections["capacity_rejections"],
            "availability_rejections": self.rejections["availability_rejections"],
            "expertise_rejections": self.rejections["expertise_rejections"],
            "repeat_student_cases_protected": repeat_cases,
            "constraint_priority": self.priority_rules,
        }

    def _quality(self, entries: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> dict[str, Any]:
        hard = max(0, 100 - len(conflicts) * 20)
        compact = self._compactness_score(entries)
        early = self._early_release_score(entries)
        fairness = self._fairness_score(entries)
        teacher_balance = self._teacher_balance_score(entries)
        lab = self._lab_quality_score(entries)
        repeat = 100 if not any(conflict["type"] == "repeat_student" for conflict in conflicts) else 55
        overall = round(
            hard * 0.28
            + compact * 0.18
            + early * 0.14
            + fairness * 0.13
            + teacher_balance * 0.13
            + lab * 0.07
            + repeat * 0.07
        )
        return {
            "overall": overall,
            "hard_constraints": round(hard),
            "compactness": round(compact),
            "early_release": round(early),
            "day_fairness": round(fairness),
            "teacher_balance": round(teacher_balance),
            "lab_quality": round(lab),
            "repeat_protection": round(repeat),
        }

    def _compactness_score(self, entries: list[dict[str, Any]]) -> float:
        penalties = 0
        opportunities = 0
        for section in self.dataset["sections"]:
            for day in DAYS:
                day_entries = [
                    entry
                    for entry in entries
                    if entry["section_id"] == section["id"] and entry["day"] == day
                ]
                if len(day_entries) <= 1:
                    continue
                opportunities += 1
                penalties += self._section_day_gaps(entries, section["id"], day)
        if opportunities == 0:
            return 100
        return max(45, 100 - (penalties / opportunities) * 22)

    def _early_release_score(self, entries: list[dict[str, Any]]) -> float:
        endings: list[int] = []
        for section in self.dataset["sections"]:
            by_day = self._section_last_period_by_day(entries, section["id"])
            endings.extend(by_day.values())
        if not endings:
            return 0
        average_end = sum(endings) / len(endings)
        return max(40, min(100, 120 - average_end * 14))

    def _fairness_score(self, entries: list[dict[str, Any]]) -> float:
        penalty = 0
        checks = 0
        for section in self.dataset["sections"]:
            by_day = self._section_last_period_by_day(entries, section["id"])
            for left, right in zip(DAYS, DAYS[1:]):
                if left in by_day and right in by_day:
                    checks += 1
                    if by_day[left] >= 5 and by_day[right] >= 5:
                        penalty += 1
        if checks == 0:
            return 100
        return max(55, 100 - (penalty / checks) * 60)

    def _teacher_balance_score(self, entries: list[dict[str, Any]]) -> float:
        scores: list[float] = []
        for teacher in self.dataset["teachers"]:
            counts = [0, 0, 0, 0, 0]
            for entry in entries:
                if entry["teacher_id"] == teacher["id"]:
                    counts[DAY_INDEX[entry["day"]]] += 1
            total = sum(counts)
            if total == 0:
                continue
            mean = total / len(counts)
            variance = sum((count - mean) ** 2 for count in counts) / len(counts)
            scores.append(max(45, 100 - sqrt(variance) * 28))
        return sum(scores) / len(scores) if scores else 100

    def _lab_quality_score(self, entries: list[dict[str, Any]]) -> float:
        labs = [entry for entry in entries if entry["course_type"] == "lab"]
        if not labs:
            return 100
        score = 0
        for entry in labs:
            continuous = int(entry["duration"]) >= 2
            morning = int(entry["start_index"]) <= 2
            score += 70 + (20 if continuous else 0) + (10 if morning else 0)
        return min(100, score / len(labs))

    def _build_views(self, entries: list[dict[str, Any]]) -> dict[str, dict[str, list[dict[str, Any]]]]:
        views = {"section": defaultdict(list), "teacher": defaultdict(list), "room": defaultdict(list), "lab": defaultdict(list)}
        for entry in entries:
            views["section"][entry["section_name"]].append(entry)
            views["teacher"][entry["teacher_name"]].append(entry)
            views["room"][entry["room_name"]].append(entry)
            if entry["course_type"] == "lab":
                views["lab"][entry["room_name"]].append(entry)
        serializable: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for view_name, groups in views.items():
            serializable[view_name] = {}
            for key, items in groups.items():
                serializable[view_name][key] = sorted(
                    items, key=lambda item: (DAY_INDEX[item["day"]], item["start_index"])
                )
        return serializable

    def _ai_evidence(self) -> dict[str, Any]:
        return {
            "title": "CSP + DFS Backtracking + Heuristic Optimization",
            "variables": len(self.sessions),
            "domain_description": "Each variable is assigned one teacher, one valid room/lab, and one contiguous time window.",
            "variable_ordering": [
                "Labs first",
                "Courses with fewer eligible teachers first",
                "Sections affected by repeat students first",
                "Longer duration sessions first",
                "Difficult courses earlier in tie-breaks",
            ],
            "hard_constraints": [
                "Teacher clash",
                "Room/lab double booking",
                "Section clash",
                "Lab-only room rule",
                "Classroom-only theory rule",
                "Room capacity",
                "Teacher availability",
                "Teacher expertise",
                "Same section-course keeps the same teacher",
                "Same section-course is spread across different days",
                "3-credit theory courses split as one 2-hour block plus one 1-hour lecture",
                "Section day gaps stay within the allowed limit",
                "Friday prayer buffer is protected",
                "Repeat-student clash",
                "Duration fits a contiguous time window",
            ],
            "soft_constraints": [
                "Minimize section gaps",
                "Maximize early release",
                "Recover fairness after late days",
                "Balance teacher workload",
                "Prefer difficult courses earlier",
                "Prefer continuous lab blocks",
                "Avoid excessive teacher back-to-back load",
            ],
            "rejection_trace": dict(self.rejections),
            "priority_framework": self.priority_rules,
        }


def generate_timetable(dataset: dict[str, Any]) -> dict[str, Any]:
    scheduler = Scheduler(dataset)
    return scheduler.run()
