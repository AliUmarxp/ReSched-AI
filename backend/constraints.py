from __future__ import annotations


CONSTRAINT_CATALOG = [
    {"key": "teacher_clashes", "name": "Teacher collision", "category": "Collision", "description": "A teacher cannot teach two sessions at the same time.", "locked": True, "default_mode": "hard", "default_weight": 1.0},
    {"key": "room_clashes", "name": "Room collision", "category": "Collision", "description": "A room cannot host two sessions at the same time.", "locked": True, "default_mode": "hard", "default_weight": 1.0},
    {"key": "section_clashes", "name": "Section collision", "category": "Collision", "description": "A section cannot attend two sessions at the same time.", "locked": True, "default_mode": "hard", "default_weight": 1.0},
    {"key": "repeat_student_clashes", "name": "Repeat-student protection", "category": "Student", "description": "Current and repeated courses for the same student cannot overlap.", "locked": False, "default_mode": "hard", "default_weight": 2.0},
    {"key": "expertise_rejections", "name": "Teacher expertise", "category": "Teacher", "description": "Only qualified and course-approved teachers may be assigned.", "locked": False, "default_mode": "hard", "default_weight": 1.5},
    {"key": "availability_rejections", "name": "Teacher availability", "category": "Teacher", "description": "Assignments must fit teacher availability.", "locked": False, "default_mode": "hard", "default_weight": 1.5},
    {"key": "teacher_consistency_rejections", "name": "Teacher consistency", "category": "Teacher", "description": "Keep one teacher for all meetings of a section-course.", "locked": False, "default_mode": "hard", "default_weight": 1.2},
    {"key": "room_type_rejections", "name": "Room type", "category": "Room", "description": "Theory uses classrooms and labs use laboratory rooms.", "locked": False, "default_mode": "hard", "default_weight": 1.5},
    {"key": "capacity_rejections", "name": "Room capacity", "category": "Room", "description": "Room capacity must meet section strength.", "locked": False, "default_mode": "hard", "default_weight": 1.5},
    {"key": "course_day_spread_rejections", "name": "Course day spread", "category": "Academic", "description": "Separate meetings of the same course across different days.", "locked": False, "default_mode": "hard", "default_weight": 1.0},
    {"key": "section_gap_limit_rejections", "name": "Section gap limit", "category": "Student", "description": "Avoid long idle gaps within a section's day.", "locked": False, "default_mode": "hard", "default_weight": 1.0},
    {"key": "friday_prayer_break_rejections", "name": "Friday prayer window", "category": "Calendar", "description": "Protect the configured Friday prayer period.", "locked": False, "default_mode": "hard", "default_weight": 1.0},
    {"key": "break_crossing_rejections", "name": "Midday break", "category": "Calendar", "description": "Prevent a session from crossing the midday break.", "locked": False, "default_mode": "hard", "default_weight": 1.0},
    {"key": "compactness", "name": "Compact section days", "category": "Quality", "description": "Prefer fewer gaps in student timetables.", "locked": False, "default_mode": "soft", "default_weight": 1.0},
    {"key": "early_release", "name": "Early release", "category": "Quality", "description": "Prefer schedules that finish earlier.", "locked": False, "default_mode": "soft", "default_weight": 1.0},
    {"key": "day_fairness", "name": "Day fairness", "category": "Quality", "description": "Distribute section load across the week.", "locked": False, "default_mode": "soft", "default_weight": 1.0},
    {"key": "teacher_balance", "name": "Teacher workload balance", "category": "Quality", "description": "Avoid uneven teacher daily workloads.", "locked": False, "default_mode": "soft", "default_weight": 1.0},
]

CATALOG_BY_KEY = {item["key"]: item for item in CONSTRAINT_CATALOG}


def default_constraint_rows() -> list[dict]:
    return [
        {
            "constraint_key": item["key"],
            "enabled": True,
            "mode": item["default_mode"],
            "weight": item["default_weight"],
            "parameters": {},
        }
        for item in CONSTRAINT_CATALOG
    ]
