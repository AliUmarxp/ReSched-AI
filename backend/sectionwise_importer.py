from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from .seed_data import build_time_slots


NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def _cell_text(cell: ET.Element) -> str:
    texts: list[str] = []
    for node in cell.findall(".//w:t", NS):
        if node.text:
            texts.append(node.text.strip())
    return " ".join(part for part in texts if part).strip()


def _parse_docx_tables(docx_path: Path) -> list[list[list[str]]]:
    with ZipFile(docx_path) as archive:
        xml = archive.read("word/document.xml")
    root = ET.fromstring(xml)
    tables: list[list[list[str]]] = []
    for table in root.findall(".//w:tbl", NS):
        rows: list[list[str]] = []
        for row in table.findall("./w:tr", NS):
            cells = [_cell_text(cell) for cell in row.findall("./w:tc", NS)]
            if any(cells):
                rows.append(cells)
        if rows:
            tables.append(rows)
    return tables


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _program_from_path(path: Path) -> tuple[str, str]:
    folder = path.parent.name.lower()
    if "ai" in folder:
        return "BS Artificial Intelligence", "ai"
    if "cs" in folder:
        return "BS Computer Science", "cs"
    if "cys" in folder:
        return "BS Cyber Security", "cy"
    if "se" in folder:
        return "BS Software Engineering", "se"
    return "BS Computer Science", "cs"


def _extract_semester(filename: str) -> int:
    match = re.search(r"(\d+)\s*(st|nd|rd|th)\s*sem", filename.lower())
    if not match:
        return 1
    return int(match.group(1))


def _normalize_course_code(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value or "").upper()
    return cleaned


def _parse_credit_hours(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+)(?:\.0)?\s*", value or "")
    if not match:
        return 1
    return max(1, min(4, int(match.group(1))))


def _looks_like_summary_row(code: str, title: str, faculty: str) -> bool:
    haystack = f"{code} {title} {faculty}".lower()
    return any(
        token in haystack
        for token in [
            "total credit",
            "semester credit",
            "sem credit",
            "credit hrs",
        ]
    )


def _clean_teacher_name(raw: str) -> str:
    value = re.sub(r"\s+", " ", (raw or "").strip())
    value = value.replace("LESibgha", "LE Sibgha")
    value = value.replace("Le Faryal", "LE Faryal")
    value = value.replace("LE Frayal", "LE Faryal")
    value = value.replace("Lec Tabasum", "Lec Tabassum")
    value = value.replace("Lec Daniyal Baig", "Lec Daniyal")
    value = value.replace("Lec Shagufta Riaz", "Lec Shagufta")
    value = value.replace("Dr Saman Riaz", "Dr Saman")
    value = value.replace("Dr Fiza Batool", "Dr Fiza")
    return value


def _teacher_id(raw: str) -> tuple[str, str]:
    raw = _clean_teacher_name(raw)
    chunks = [part for part in re.split(r"\s+", raw.strip()) if part]
    if not chunks:
        return "t-tbd", "TBD"
    last = chunks[-1]
    return f"t-{_slug(last)}", raw.strip()


def _build_default_rooms() -> list[dict]:
    return [
        {"id": "room-101", "name": "Room 101", "type": "classroom", "capacity": 50},
        {"id": "room-102", "name": "Room 102", "type": "classroom", "capacity": 50},
        {"id": "room-103", "name": "Room 103", "type": "classroom", "capacity": 50},
        {"id": "room-104", "name": "Room 104", "type": "classroom", "capacity": 50},
        {"id": "room-121", "name": "Room 121", "type": "classroom", "capacity": 55},
        {"id": "room-122", "name": "Room 122", "type": "classroom", "capacity": 55},
        {"id": "room-123", "name": "Room 123", "type": "classroom", "capacity": 55},
        {"id": "room-124", "name": "Room 124", "type": "classroom", "capacity": 55},
        {"id": "room-204", "name": "Room 204", "type": "classroom", "capacity": 60},
        {"id": "room-305", "name": "Room 305", "type": "classroom", "capacity": 45},
        {"id": "lab-117", "name": "Lab 117", "type": "lab", "capacity": 45},
        {"id": "lab-119", "name": "Lab 119", "type": "lab", "capacity": 45},
        {"id": "lab-120", "name": "Lab 120", "type": "lab", "capacity": 45},
        {"id": "lab-142", "name": "Lab 142", "type": "lab", "capacity": 50},
        {"id": "lab-143", "name": "Lab 143", "type": "lab", "capacity": 45},
    ]


def import_sectionwise_dataset(base_dir: Path) -> dict:
    documents = sorted(base_dir.rglob("*.docx"))
    teachers: dict[str, dict] = {}
    courses: dict[str, dict] = {}
    sections: list[dict] = []
    programs = {
        "bs-ai": {"id": "bs-ai", "name": "BS Artificial Intelligence"},
        "bs-cs": {"id": "bs-cs", "name": "BS Computer Science"},
        "bs-se": {"id": "bs-se", "name": "BS Software Engineering"},
        "bs-cy": {"id": "bs-cy", "name": "BS Cyber Security"},
    }

    for doc in documents:
        tables = _parse_docx_tables(doc)
        if len(tables) < 2:
            continue
        course_table = tables[1]
        course_rows = course_table[1:]
        program_name, section_prefix = _program_from_path(doc)
        semester = _extract_semester(doc.name)
        degree = {"ai": "BSAI", "cs": "BSCS", "cy": "BSCYS", "se": "BSSE"}[section_prefix]
        cohort_match = re.search(r"\b(FALL|SPRING)\s+\d{4}(?:-\d+)?\b", doc.stem, re.I)
        cohort = cohort_match.group(0).upper() if cohort_match else ""
        section_id = f"{section_prefix}-{semester}-{_slug(doc.stem)[:6]}"
        section_name = f"{degree}-{semester}"
        required_courses: list[str] = []
        course_teachers: dict[str, str] = {}

        for row in course_rows:
            if len(row) < 6:
                continue
            code_raw = row[1]
            credit_raw = row[2]
            title = row[4]
            faculty = row[5]
            if not code_raw or not title:
                continue
            if _looks_like_summary_row(code_raw, title, faculty):
                continue
            code = _normalize_course_code(code_raw)
            if not code:
                continue
            is_lab = "lab" in title.lower() or code.endswith("L")
            if is_lab and not code.endswith("L"):
                code = f"{code}L"
            course_id = _slug(code.lower())
            duration = 3 if is_lab else 1
            credit_hours = _parse_credit_hours(credit_raw)
            weekly_frequency = 1 if is_lab else credit_hours
            difficulty = 5 if any(token in title.lower() for token in ["ai", "deep", "security", "network"]) else 3
            teacher_key, teacher_name = _teacher_id(faculty or "TBD")
            teachers.setdefault(
                teacher_key,
                {
                    "id": teacher_key,
                    "name": teacher_name,
                    "expertise_courses": [],
                    "availability_slots": [slot["id"] for slot in build_time_slots()],
                    "max_lectures_per_day": 4,
                },
            )
            if course_id not in teachers[teacher_key]["expertise_courses"]:
                teachers[teacher_key]["expertise_courses"].append(course_id)

            if course_id not in courses:
                courses[course_id] = {
                    "id": course_id,
                    "name": f"{code} {title}",
                    "type": "lab" if is_lab else "theory",
                    "duration": duration,
                    "credit_hours": credit_hours,
                    "contact_hours": 3 if is_lab else credit_hours,
                    "weekly_frequency": weekly_frequency,
                    "difficulty_level": difficulty,
                    "allowed_teachers": [teacher_key],
                }
            else:
                if teacher_key not in courses[course_id]["allowed_teachers"]:
                    courses[course_id]["allowed_teachers"].append(teacher_key)
            if course_id not in required_courses:
                required_courses.append(course_id)
            course_teachers[course_id] = teacher_key

        if required_courses:
            sections.append(
                {
                    "id": section_id,
                    "program": program_name,
                    "degree": degree,
                    "semester": semester,
                    "cohort": cohort,
                    "name": section_name,
                    "strength": 40,
                    "required_courses": required_courses,
                    "course_teachers": course_teachers,
                }
            )

    return {
        "institution": {
            "name": "NIIT Lahore",
            "portal_context": "SECTION-WISE auto import",
            "note": "Auto-imported from provided SECTION-WISE timetables.",
        },
        "sourceInsights": {
            "source": str(base_dir),
            "documents_count": len(documents),
            "programs_found": sorted({section["program"] for section in sections}),
            "sections_found": [section["name"] for section in sections],
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
            "observed_classrooms": ["101", "102", "103", "104", "121", "122", "123", "124", "204", "305"],
            "observed_lab_rooms": ["117", "119", "120", "142", "143"],
            "import_summary": {
                "courses": len(courses),
                "teachers": len(teachers),
                "sections": len(sections),
            },
        },
        "aiProfile": {
            "weights": {
                "compactness": 1.0,
                "early_release": 1.0,
                "day_fairness": 1.0,
                "teacher_balance": 1.0,
                "repeat_protection": 1.0,
            },
            "trained_runs": 0,
        },
        "programs": list(programs.values()),
        "timeSlots": build_time_slots(),
        "teachers": sorted(teachers.values(), key=lambda item: item["name"]),
        "courses": sorted(courses.values(), key=lambda item: item["name"]),
        "sections": sections,
        "rooms": _build_default_rooms(),
        "repeatStudents": [],
    }
