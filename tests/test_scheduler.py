from backend.constraints import default_constraint_rows
from backend.scheduler import generate_timetable
from backend.seed_data import get_seed_data
from backend.tenant_store import validate_dataset


def test_seed_dataset_is_valid():
    assert validate_dataset(get_seed_data()) == []


def test_scheduler_never_returns_hard_conflicts_for_seed():
    result = generate_timetable(get_seed_data(), default_constraint_rows())
    assert result["conflicts"] == []
    assert result["report"]["hard_conflicts"] == 0
    assert result["report"]["scheduled_sessions"] + result["report"]["unscheduled_sessions"] == result["report"]["total_sessions"]


def test_duplicate_ids_are_rejected():
    dataset = get_seed_data()
    dataset["rooms"].append(dict(dataset["rooms"][0]))
    issues = validate_dataset(dataset)
    assert any(issue["code"] == "duplicate_id" and issue["path"] == "rooms" for issue in issues)


def test_core_collision_constraints_are_locked():
    collision = next(row for row in default_constraint_rows() if row["constraint_key"] == "teacher_clashes")
    assert collision["enabled"] is True
    assert collision["mode"] == "hard"
