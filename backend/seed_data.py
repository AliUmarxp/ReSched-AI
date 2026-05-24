from __future__ import annotations

from copy import deepcopy


DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]


def build_time_slots() -> list[dict]:
    periods = [
        ("09:00", "09:50"),
        ("10:00", "10:50"),
        ("11:00", "11:50"),
        ("12:00", "12:50"),
        ("13:20", "14:10"),
        ("14:20", "15:10"),
        ("15:40", "16:30"),
    ]
    slots: list[dict] = []
    for day_index, day in enumerate(DAYS):
        for period_index, (start, end) in enumerate(periods, start=1):
            slots.append(
                {
                    "id": f"{day[:3].lower()}-p{period_index}",
                    "day": day,
                    "start_time": start,
                    "end_time": end,
                    "period_index": period_index,
                    "sort_index": day_index * 10 + period_index,
                }
            )
    return slots


ALL_SLOT_IDS = [slot["id"] for slot in build_time_slots()]
NO_FRIDAY_LATE = [
    slot["id"]
    for slot in build_time_slots()
    if not (slot["day"] == "Friday" and slot["period_index"] >= 7)
]
MORNING_HEAVY = [
    slot["id"]
    for slot in build_time_slots()
    if slot["period_index"] <= 5
]


SOURCE_INSIGHTS = {
    "source": "SECTION-WISE.zip",
    "documents_count": 12,
    "programs_found": ["BSCS", "BSAI", "BSCYS", "BSSE"],
    "semesters_found": ["2nd", "3rd", "4th", "5th"],
    "observed_time_pattern": [
        "0900-0950",
        "1000-1050",
        "1100-1150",
        "1200-1250",
        "Break 1250-1320",
        "1320-1410",
        "1420-1510",
        "1540-1630",
    ],
    "observed_lab_rooms": ["117", "119", "120", "142", "143"],
    "documents": [
        "2nd Sem BSCS FALL 2025",
        "3rd Sem BSCS SPRING 2025",
        "4th Sem BSCS FALL 2024",
        "5th Sem BSCS SPRING 2024",
        "2nd Sem BSAI FALL 2025",
        "3rd Sem BSAI SPRING 2025",
        "4th Sem BSAI FALL 2024",
        "5th Sem BSAI SPRING 2024",
        "2nd Sem BSCYS FALL 2025",
        "4th Sem BSCYS FALL 2024",
        "2nd Sem BSSE FALL 2025",
        "4th Sem BSSE FALL 2024",
    ],
    "real_courses_used_in_seed": [
        "CS112 Object Oriented Programming",
        "CS216 Data Structures",
        "CS260 Computer Networks",
        "CS305 Software Engineering",
        "CS215 Information Security",
        "CS344 Artificial Intelligence",
        "AI321 Knowledge Representation and Reasoning",
        "AI324 Natural Language Programming",
        "AI335 Deep Learning",
        "CS332 Design and Analysis of Algorithms",
        "CS325 Operating Systems",
        "CY223 Network Security",
        "SE414 IoT for Software Engineering",
    ],
    "ai_ccp_mapping": [
        "Real section documents inform slot template, lab duration, room naming, and course catalog.",
        "CSP variables are section-course sessions; domains are teacher-room-time combinations.",
        "Backtracking rejects teacher, room, section, capacity, availability, expertise, lab, and repeat-student clashes.",
        "Heuristic scoring prefers compact days, early release, teacher balance, difficult courses early, and fair recovery after late days.",
    ],
}


SEED_DATA = {
    "institution": {
        "name": "NIIT Lahore",
        "portal_context": "AMS-ready demo dataset",
        "note": "Seed data is based on the provided SECTION-WISE documents and public NIIT program context. Private AMS data is not scraped.",
    },
    "sourceInsights": SOURCE_INSIGHTS,
    "programs": [
        {"id": "bs-ai", "name": "BS Artificial Intelligence"},
        {"id": "bs-cs", "name": "BS Computer Science"},
        {"id": "bs-se", "name": "BS Software Engineering"},
        {"id": "bs-cy", "name": "BS Cyber Security"},
    ],
    "timeSlots": build_time_slots(),
    "teachers": [
        {
            "id": "t-ali",
            "name": "Dr. Ali",
            "expertise_courses": ["cs344"],
            "availability_slots": NO_FRIDAY_LATE,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-iqra",
            "name": "LE Iqra",
            "expertise_courses": ["cs260-l", "cs325-l"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-unaiza",
            "name": "Lec Unaiza",
            "expertise_courses": ["cs112", "cs216"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-sajid",
            "name": "Dr. Sajid",
            "expertise_courses": ["cs305", "cs215"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-shahan",
            "name": "Dr. Shahan",
            "expertise_courses": ["ai233"],
            "availability_slots": MORNING_HEAVY,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-haseeb",
            "name": "Lec Haseeb",
            "expertise_courses": ["ai335", "ai335-l"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-hani",
            "name": "Dr. Hani",
            "expertise_courses": ["ai321", "ai324"],
            "availability_slots": NO_FRIDAY_LATE,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-saman",
            "name": "Dr. Saman",
            "expertise_courses": ["cs332"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-shagufta",
            "name": "Lec Shagufta",
            "expertise_courses": ["cs260", "cs325"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-nazim",
            "name": "Lec Nazim",
            "expertise_courses": ["cs305"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-daniyal",
            "name": "LE Daniyal",
            "expertise_courses": ["cs216-l", "cs325-l", "cs226"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-azeem",
            "name": "Lec Azeem",
            "expertise_courses": ["cy103", "cy223", "cy223-l"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-rubab",
            "name": "Dr. Rubab",
            "expertise_courses": ["se216", "se200"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-tabassum",
            "name": "Lec Tabassum",
            "expertise_courses": ["cs216", "se414", "se414-l"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-faryal",
            "name": "LE Faryal",
            "expertise_courses": ["cs344-l"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
        {
            "id": "t-usama",
            "name": "LE Usama",
            "expertise_courses": ["cs260-l"],
            "availability_slots": ALL_SLOT_IDS,
            "max_lectures_per_day": 4,
        },
    ],
    "courses": [
        {
            "id": "cs112",
            "name": "CS112 Object Oriented Programming",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 3,
            "allowed_teachers": ["t-unaiza"],
        },
        {
            "id": "cs216",
            "name": "CS216 Data Structures",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-unaiza", "t-tabassum"],
        },
        {
            "id": "cs216-l",
            "name": "CS216L Data Structures Lab",
            "type": "lab",
            "duration": 3,
            "difficulty_level": 4,
            "allowed_teachers": ["t-daniyal"],
        },
        {
            "id": "cs260",
            "name": "CS260 Computer Networks",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 4,
            "allowed_teachers": ["t-shagufta"],
        },
        {
            "id": "cs260-l",
            "name": "CS260L Computer Networks Lab",
            "type": "lab",
            "duration": 3,
            "difficulty_level": 4,
            "allowed_teachers": ["t-iqra", "t-usama"],
        },
        {
            "id": "cs305",
            "name": "CS305 Software Engineering",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 3,
            "allowed_teachers": ["t-sajid", "t-nazim"],
        },
        {
            "id": "cs215",
            "name": "CS215 Information Security",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 4,
            "allowed_teachers": ["t-sajid"],
        },
        {
            "id": "cs344",
            "name": "CS344 Artificial Intelligence",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-ali"],
        },
        {
            "id": "cs344-l",
            "name": "CS344L Artificial Intelligence Lab",
            "type": "lab",
            "duration": 3,
            "difficulty_level": 5,
            "allowed_teachers": ["t-faryal"],
        },
        {
            "id": "ai233",
            "name": "AI233 Machine Learning",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-shahan"],
        },
        {
            "id": "ai321",
            "name": "AI321 Knowledge Representation and Reasoning",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-hani"],
        },
        {
            "id": "ai324",
            "name": "AI324 Natural Language Programming",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-hani"],
        },
        {
            "id": "ai335",
            "name": "AI335 Deep Learning",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-haseeb"],
        },
        {
            "id": "ai335-l",
            "name": "AI335L Deep Learning Lab",
            "type": "lab",
            "duration": 3,
            "difficulty_level": 5,
            "allowed_teachers": ["t-haseeb"],
        },
        {
            "id": "cs332",
            "name": "CS332 Design and Analysis of Algorithms",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-saman"],
        },
        {
            "id": "cs325",
            "name": "CS325 Operating Systems",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 4,
            "allowed_teachers": ["t-shagufta"],
        },
        {
            "id": "cs325-l",
            "name": "CS325L Operating Systems Lab",
            "type": "lab",
            "duration": 3,
            "difficulty_level": 4,
            "allowed_teachers": ["t-daniyal", "t-iqra"],
        },
        {
            "id": "cy103",
            "name": "CY103 Information Assurance",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 4,
            "allowed_teachers": ["t-azeem"],
        },
        {
            "id": "cy223",
            "name": "CY223 Network Security",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 5,
            "allowed_teachers": ["t-azeem"],
        },
        {
            "id": "cy223-l",
            "name": "CY223L Network Security Lab",
            "type": "lab",
            "duration": 3,
            "difficulty_level": 5,
            "allowed_teachers": ["t-azeem"],
        },
        {
            "id": "se216",
            "name": "SE216 Software Design and Architecture",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 4,
            "allowed_teachers": ["t-rubab"],
        },
        {
            "id": "se200",
            "name": "SE200 Software Requirement Engineering",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 3,
            "allowed_teachers": ["t-rubab"],
        },
        {
            "id": "se414",
            "name": "SE414 IoT for Software Engineering",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 4,
            "allowed_teachers": ["t-tabassum"],
        },
        {
            "id": "se414-l",
            "name": "SE414L IoT for Software Engineering Lab",
            "type": "lab",
            "duration": 3,
            "difficulty_level": 4,
            "allowed_teachers": ["t-tabassum"],
        },
        {
            "id": "cs226",
            "name": "CS226 Computer Organization and Assembly Language",
            "type": "theory",
            "duration": 1,
            "difficulty_level": 4,
            "allowed_teachers": ["t-daniyal"],
        },
    ],
    "sections": [
        {
            "id": "ai-3a",
            "program": "BS Artificial Intelligence",
            "semester": 3,
            "name": "AI-3A",
            "strength": 42,
            "required_courses": ["cs260", "cs216", "cs215", "cs344", "cs260-l"],
        },
        {
            "id": "ai-5a",
            "program": "BS Artificial Intelligence",
            "semester": 5,
            "name": "AI-5A",
            "strength": 38,
            "required_courses": ["ai321", "ai324", "ai335", "cs332", "ai335-l"],
        },
        {
            "id": "cs-3a",
            "program": "BS Computer Science",
            "semester": 3,
            "name": "CS-3A",
            "strength": 48,
            "required_courses": ["cs260", "cs216", "cs305", "cs215", "cs216-l"],
        },
        {
            "id": "cs-5a",
            "program": "BS Computer Science",
            "semester": 5,
            "name": "CS-5A",
            "strength": 45,
            "required_courses": ["cs325", "cs332", "ai335", "cs260", "cs325-l"],
        },
        {
            "id": "cy-4a",
            "program": "BS Cyber Security",
            "semester": 4,
            "name": "CY-4A",
            "strength": 35,
            "required_courses": ["cy103", "cy223", "cs325", "cs226", "cy223-l"],
        },
        {
            "id": "se-4a",
            "program": "BS Software Engineering",
            "semester": 4,
            "name": "SE-4A",
            "strength": 40,
            "required_courses": ["se216", "se200", "se414", "cs226", "se414-l"],
        },
    ],
    "rooms": [
        {"id": "room-101", "name": "Room 101", "type": "classroom", "capacity": 45},
        {"id": "room-102", "name": "Room 102", "type": "classroom", "capacity": 50},
        {"id": "room-204", "name": "Room 204", "type": "classroom", "capacity": 60},
        {"id": "room-305", "name": "Room 305", "type": "classroom", "capacity": 42},
        {"id": "lab-117", "name": "Lab 117", "type": "lab", "capacity": 45},
        {"id": "lab-119", "name": "Lab 119", "type": "lab", "capacity": 45},
        {"id": "lab-120", "name": "Lab 120", "type": "lab", "capacity": 45},
        {"id": "lab-142", "name": "Lab 142", "type": "lab", "capacity": 50},
        {"id": "lab-143", "name": "Lab 143", "type": "lab", "capacity": 45},
    ],
    "repeatStudents": [
        {
            "id": "rs-ahmed",
            "name": "Ahmed Raza",
            "current_section": "ai-5a",
            "repeated_courses": [{"course_id": "cs216", "section_id": "ai-3a"}],
        },
        {
            "id": "rs-sara",
            "name": "Sara Khan",
            "current_section": "cs-5a",
            "repeated_courses": [{"course_id": "cs216", "section_id": "cs-3a"}],
        },
        {
            "id": "rs-bilal",
            "name": "Bilal Ahmed",
            "current_section": "cy-4a",
            "repeated_courses": [{"course_id": "cs260", "section_id": "ai-3a"}],
        },
        {
            "id": "rs-hina",
            "name": "Hina Tariq",
            "current_section": "se-4a",
            "repeated_courses": [{"course_id": "cs325", "section_id": "cs-5a"}],
        },
        {
            "id": "rs-umer",
            "name": "Umer Farooq",
            "current_section": "ai-5a",
            "repeated_courses": [
                {"course_id": "cs215", "section_id": "ai-3a"},
                {"course_id": "cs260", "section_id": "cs-3a"},
            ],
        },
    ],
}


def get_seed_data() -> dict:
    return deepcopy(SEED_DATA)
