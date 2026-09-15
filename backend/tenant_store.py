from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .constraints import CATALOG_BY_KEY, CONSTRAINT_CATALOG, default_constraint_rows
from .database import utcnow
from .models import AuditEvent, ConstraintSetting, EntitySet, ScheduleRun, User, Workspace
from .seed_data import build_time_slots, get_seed_data


ENTITY_NAMES = {
    "institution",
    "sourceInsights",
    "aiProfile",
    "programs",
    "timeSlots",
    "teachers",
    "courses",
    "sections",
    "rooms",
    "repeatStudents",
}


def audit(db: Session, action: str, actor_id: str | None, subject_id: str | None = None, **details: Any) -> None:
    db.add(
        AuditEvent(
            action=action,
            actor_user_id=actor_id,
            subject_user_id=subject_id,
            details=details,
        )
    )


def empty_dataset(institution_name: str = "") -> dict[str, Any]:
    """Return an operational tenant shell without sample academic records."""
    return {
        "institution": {"name": institution_name, "portal_context": "", "note": ""},
        "sourceInsights": {},
        "aiProfile": {"weights": {}, "trained_runs": 0},
        "programs": [],
        "timeSlots": build_time_slots(),
        "teachers": [],
        "courses": [],
        "sections": [],
        "rooms": [],
        "repeatStudents": [],
    }


def ensure_workspace(db: Session, user_id: str, seed: bool = False) -> Workspace:
    workspace = db.scalar(select(Workspace).where(Workspace.user_id == user_id))
    if workspace:
        return workspace
    workspace = Workspace(user_id=user_id, dataset_version=1)
    db.add(workspace)
    user = db.get(User, user_id)
    initial = get_seed_data() if seed else empty_dataset(user.institution_name if user else "")
    for name, payload in initial.items():
        if name in ENTITY_NAMES:
            db.add(EntitySet(user_id=user_id, name=name, payload=payload))
    for row in default_constraint_rows():
        db.add(ConstraintSetting(user_id=user_id, **row))
    db.flush()
    return workspace


def load_dataset(db: Session, user_id: str) -> dict[str, Any]:
    ensure_workspace(db, user_id)
    rows = db.scalars(select(EntitySet).where(EntitySet.user_id == user_id)).all()
    dataset = {row.name: row.payload for row in rows}
    user = db.get(User, user_id)
    for key, value in empty_dataset(user.institution_name if user else "").items():
        dataset.setdefault(key, value)
    for course in dataset.get("courses", []):
        if not isinstance(course, dict):
            continue
        is_lab = course.get("type") == "lab"
        course.setdefault("credit_hours", 1 if is_lab else 3)
        course.setdefault("contact_hours", 3 if is_lab else course["credit_hours"])
        course.setdefault("weekly_frequency", 1 if is_lab else course["credit_hours"])
        course["duration"] = 3 if is_lab else int(course.get("duration") or 1)
    for room in dataset.get("rooms", []):
        if isinstance(room, dict):
            room.setdefault("allow_parallel_sessions", False)
    return dataset


def _duplicates(rows: list[dict[str, Any]]) -> list[str]:
    counts = Counter(str(row.get("id", "")).strip() for row in rows)
    return sorted(key for key, count in counts.items() if key and count > 1)


def validate_dataset(dataset: dict[str, Any], require_schedule_ready: bool = True) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    list_entities = ["programs", "timeSlots", "teachers", "courses", "sections", "rooms", "repeatStudents"]
    for name in list_entities:
        if not isinstance(dataset.get(name), list):
            issues.append({"path": name, "code": "invalid_type", "message": "Must be a list"})
            continue
        for duplicate in _duplicates(dataset[name]):
            issues.append({"path": name, "code": "duplicate_id", "message": f"Duplicate ID: {duplicate}"})

    teachers = {row.get("id") for row in dataset.get("teachers", []) if isinstance(row, dict)}
    courses = {row.get("id") for row in dataset.get("courses", []) if isinstance(row, dict)}
    sections = {row.get("id") for row in dataset.get("sections", []) if isinstance(row, dict)}
    rooms = dataset.get("rooms", [])
    slots = {row.get("id") for row in dataset.get("timeSlots", []) if isinstance(row, dict)}

    if require_schedule_ready and not any(row.get("type") == "classroom" for row in rooms if isinstance(row, dict)):
        issues.append({"path": "rooms", "code": "missing_classroom", "message": "At least one classroom is required"})
    if require_schedule_ready and any(course.get("type") == "lab" for course in dataset.get("courses", []) if isinstance(course, dict)) and not any(
        row.get("type") == "lab" for row in rooms if isinstance(row, dict)
    ):
        issues.append({"path": "rooms", "code": "missing_lab", "message": "At least one lab room is required"})

    for teacher in dataset.get("teachers", []):
        if not isinstance(teacher, dict):
            continue
        for course_id in teacher.get("expertise_courses", []):
            if course_id not in courses:
                issues.append({"path": f"teachers.{teacher.get('id')}.expertise_courses", "code": "unknown_course", "message": f"Unknown course: {course_id}"})
        for slot_id in teacher.get("availability_slots", []):
            if slot_id not in slots:
                issues.append({"path": f"teachers.{teacher.get('id')}.availability_slots", "code": "unknown_slot", "message": f"Unknown slot: {slot_id}"})

    for course in dataset.get("courses", []):
        if not isinstance(course, dict):
            continue
        for teacher_id in course.get("allowed_teachers", []):
            if teacher_id not in teachers:
                issues.append({"path": f"courses.{course.get('id')}.allowed_teachers", "code": "unknown_teacher", "message": f"Unknown teacher: {teacher_id}"})

    for section in dataset.get("sections", []):
        if not isinstance(section, dict):
            continue
        if int(section.get("strength") or 0) <= 0:
            issues.append({"path": f"sections.{section.get('id')}.strength", "code": "invalid_strength", "message": "Section strength must be positive"})
        for course_id in section.get("required_courses", []):
            if course_id not in courses:
                issues.append({"path": f"sections.{section.get('id')}.required_courses", "code": "unknown_course", "message": f"Unknown course: {course_id}"})
        for course_id, teacher_id in section.get("course_teachers", {}).items():
            if course_id not in courses or teacher_id not in teachers:
                issues.append({"path": f"sections.{section.get('id')}.course_teachers", "code": "invalid_assignment", "message": f"Invalid assignment: {course_id} -> {teacher_id}"})

    for student in dataset.get("repeatStudents", []):
        if not isinstance(student, dict):
            continue
        if student.get("current_section") not in sections:
            issues.append({"path": f"repeatStudents.{student.get('id')}.current_section", "code": "unknown_section", "message": "Current section does not exist"})
        for repeated in student.get("repeated_courses", []):
            if repeated.get("section_id") not in sections or repeated.get("course_id") not in courses:
                issues.append({"path": f"repeatStudents.{student.get('id')}.repeated_courses", "code": "invalid_repeat_course", "message": "Repeated course references an unknown section or course"})
    return issues


def save_entity_set(db: Session, user_id: str, name: str, payload: Any, actor_id: str) -> tuple[dict[str, Any], int]:
    if name not in ENTITY_NAMES:
        raise ValueError(f"Unknown entity set: {name}")
    workspace = ensure_workspace(db, user_id)
    candidate = load_dataset(db, user_id)
    candidate[name] = payload
    issues = validate_dataset(candidate, require_schedule_ready=False)
    if issues:
        raise DatasetValidationError(issues)
    entity = db.scalar(select(EntitySet).where(EntitySet.user_id == user_id, EntitySet.name == name))
    if entity:
        entity.payload = payload
        entity.updated_at = utcnow()
    else:
        db.add(EntitySet(user_id=user_id, name=name, payload=payload))
    workspace.dataset_version += 1
    workspace.updated_at = utcnow()
    audit(db, "entity.updated", actor_id, user_id, entity=name, dataset_version=workspace.dataset_version)
    db.commit()
    return load_dataset(db, user_id), workspace.dataset_version


def replace_dataset(db: Session, user_id: str, dataset: dict[str, Any], actor_id: str) -> tuple[dict[str, Any], int]:
    unknown = sorted(set(dataset) - ENTITY_NAMES)
    if unknown:
        raise DatasetValidationError([{"path": "dataset", "code": "unknown_entities", "message": f"Unknown entity sets: {', '.join(unknown)}"}])
    merged = load_dataset(db, user_id)
    merged.update(dataset)
    issues = validate_dataset(merged)
    if issues:
        raise DatasetValidationError(issues)
    workspace = ensure_workspace(db, user_id)
    for name, payload in dataset.items():
        entity = db.scalar(select(EntitySet).where(EntitySet.user_id == user_id, EntitySet.name == name))
        if entity:
            entity.payload = payload
            entity.updated_at = utcnow()
        else:
            db.add(EntitySet(user_id=user_id, name=name, payload=payload))
    workspace.dataset_version += 1
    audit(db, "dataset.imported", actor_id, user_id, entities=sorted(dataset), dataset_version=workspace.dataset_version)
    db.commit()
    return load_dataset(db, user_id), workspace.dataset_version


def reset_workspace(db: Session, user_id: str, actor_id: str) -> tuple[dict[str, Any], int]:
    workspace = ensure_workspace(db, user_id, seed=False)
    db.execute(delete(EntitySet).where(EntitySet.user_id == user_id))
    for name, payload in get_seed_data().items():
        if name in ENTITY_NAMES:
            db.add(EntitySet(user_id=user_id, name=name, payload=payload))
    workspace.dataset_version += 1
    audit(db, "dataset.reset", actor_id, user_id, dataset_version=workspace.dataset_version)
    db.commit()
    return load_dataset(db, user_id), workspace.dataset_version


def clear_workspace(db: Session, user_id: str, actor_id: str) -> tuple[dict[str, Any], int]:
    workspace = ensure_workspace(db, user_id, seed=False)
    user = db.get(User, user_id)
    db.execute(delete(EntitySet).where(EntitySet.user_id == user_id))
    for name, payload in empty_dataset(user.institution_name if user else "").items():
        db.add(EntitySet(user_id=user_id, name=name, payload=payload))
    workspace.dataset_version += 1
    audit(db, "dataset.cleared", actor_id, user_id, dataset_version=workspace.dataset_version)
    db.commit()
    return load_dataset(db, user_id), workspace.dataset_version


def get_constraint_settings(db: Session, user_id: str) -> list[dict[str, Any]]:
    ensure_workspace(db, user_id)
    settings = {row.constraint_key: row for row in db.scalars(select(ConstraintSetting).where(ConstraintSetting.user_id == user_id)).all()}
    result = []
    for item in CONSTRAINT_CATALOG:
        row = settings.get(item["key"])
        result.append({**item, "enabled": row.enabled if row else True, "mode": row.mode if row else item["default_mode"], "weight": row.weight if row else item["default_weight"], "parameters": row.parameters if row else {}})
    return result


def update_constraint_settings(db: Session, user_id: str, updates: list[dict[str, Any]], actor_id: str) -> list[dict[str, Any]]:
    current = {row.constraint_key: row for row in db.scalars(select(ConstraintSetting).where(ConstraintSetting.user_id == user_id)).all()}
    workspace = ensure_workspace(db, user_id)
    for update in updates:
        key = update["constraint_key"]
        catalog = CATALOG_BY_KEY.get(key)
        if not catalog:
            raise ValueError(f"Unknown constraint: {key}")
        if catalog["locked"] and (not update["enabled"] or update["mode"] != "hard"):
            raise ValueError(f"{catalog['name']} is a core integrity constraint and cannot be disabled")
        if catalog["default_mode"] == "hard" and update["mode"] == "soft":
            raise ValueError(f"{catalog['name']} supports Apply or Ignore, not soft weighting")
        row = current.get(key)
        if not row:
            row = ConstraintSetting(user_id=user_id, constraint_key=key)
            db.add(row)
        row.enabled = update["enabled"] and update["mode"] != "off"
        row.mode = update["mode"]
        row.weight = update["weight"]
        row.parameters = update.get("parameters", {})
    workspace.dataset_version += 1
    audit(db, "constraints.updated", actor_id, user_id, count=len(updates), dataset_version=workspace.dataset_version)
    db.commit()
    return get_constraint_settings(db, user_id)


def latest_run(db: Session, user_id: str) -> ScheduleRun | None:
    return db.scalar(select(ScheduleRun).where(ScheduleRun.user_id == user_id).order_by(ScheduleRun.created_at.desc()).limit(1))


def save_run(db: Session, user_id: str, dataset_version: int, payload: dict[str, Any], actor_id: str) -> ScheduleRun:
    run = ScheduleRun(user_id=user_id, dataset_version=dataset_version, status=payload.get("status", "partial"), payload=payload)
    db.add(run)
    audit(db, "schedule.generated", actor_id, user_id, status=run.status, dataset_version=dataset_version)
    db.commit()
    db.refresh(run)
    return run


def save_ai_profile(db: Session, user_id: str, profile: dict[str, Any]) -> None:
    entity = db.scalar(select(EntitySet).where(EntitySet.user_id == user_id, EntitySet.name == "aiProfile"))
    if entity:
        entity.payload = profile
        entity.updated_at = utcnow()
    else:
        db.add(EntitySet(user_id=user_id, name="aiProfile", payload=profile))
    db.flush()


def serialize_run(run: ScheduleRun | None, current_dataset_version: int) -> dict[str, Any] | None:
    if not run:
        return None
    payload = dict(run.payload)
    payload.update({"id": run.id, "created_at": run.created_at.isoformat(), "dataset_version": run.dataset_version, "is_stale": run.dataset_version != current_dataset_version})
    return payload


class DatasetValidationError(ValueError):
    def __init__(self, issues: list[dict[str, str]]):
        super().__init__("Dataset validation failed")
        self.issues = issues
