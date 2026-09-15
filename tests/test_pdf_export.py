from backend.main import _section_course_table


def test_section_course_table_uses_scheduled_faculty_when_no_manual_assignment():
    section = {"required_courses": ["cs101"], "course_teachers": {}}
    entries = [{"course_id": "cs101", "teacher_id": "t-a", "teacher_name": "Dr. Ayesha"}]
    dataset = {
        "courses": [{"id": "cs101", "name": "CS101 Computing", "type": "theory", "credit_hours": 3, "contact_hours": 3}],
        "teachers": [{"id": "t-a", "name": "Dr. Ayesha"}],
    }

    table = _section_course_table(section, entries, dataset)

    assert table._cellvalues[1][5] == "Dr. Ayesha"
