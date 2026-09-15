from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models import User
from backend.seed_data import get_seed_data
from backend.tenant_store import ensure_workspace, load_dataset, replace_dataset, save_entity_set, save_entity_sets


def tenant_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)()


def add_user(db, username: str) -> User:
    user = User(
        username=username,
        email=f"{username}@example.edu",
        password_hash="test-only",
        role="user",
        status="approved",
        full_name=username.title(),
        institution_name=f"{username.title()} University",
    )
    db.add(user)
    db.flush()
    return user


def test_new_tenants_start_without_sample_academic_records():
    db = tenant_session()
    user = add_user(db, "new-registrar")
    ensure_workspace(db, user.id, seed=False)
    db.commit()

    dataset = load_dataset(db, user.id)
    assert dataset["institution"]["name"] == "New-Registrar University"
    assert dataset["teachers"] == []
    assert dataset["courses"] == []
    assert dataset["sections"] == []
    assert dataset["rooms"] == []
    assert dataset["timeSlots"]


def test_demo_workspace_is_the_only_explicitly_seeded_workspace():
    db = tenant_session()
    demo = add_user(db, "demo")
    regular = add_user(db, "regular")
    ensure_workspace(db, demo.id, seed=True)
    ensure_workspace(db, regular.id, seed=False)
    db.commit()

    assert len(load_dataset(db, demo.id)["courses"]) > 0
    assert load_dataset(db, regular.id)["courses"] == []


def test_crud_and_import_never_modify_another_tenant():
    db = tenant_session()
    first = add_user(db, "first")
    second = add_user(db, "second")
    ensure_workspace(db, first.id, seed=False)
    ensure_workspace(db, second.id, seed=False)
    db.commit()

    room = {"id": "room-a", "name": "Room A", "type": "classroom", "capacity": 40}
    save_entity_set(db, first.id, "rooms", [room], first.id)
    assert load_dataset(db, first.id)["rooms"] == [room]
    assert load_dataset(db, second.id)["rooms"] == []

    save_entity_set(db, first.id, "rooms", [], first.id)
    assert load_dataset(db, first.id)["rooms"] == []
    assert load_dataset(db, second.id)["rooms"] == []

    imported = get_seed_data()
    imported["institution"] = {"name": "First University"}
    replace_dataset(db, first.id, imported, first.id)
    assert load_dataset(db, first.id)["institution"]["name"] == "First University"
    assert load_dataset(db, second.id)["courses"] == []


def test_existing_demo_designation_keeps_password_and_seeds_only_that_account(monkeypatch):
    from types import SimpleNamespace

    from backend import accounts

    db = tenant_session()
    demo = add_user(db, "existing-demo")
    regular = add_user(db, "regular-account")
    original_password_hash = demo.password_hash
    monkeypatch.setattr(
        accounts,
        "settings",
        SimpleNamespace(
            enable_demo_account=True,
            demo_username="existing-demo",
            demo_email="unused@example.edu",
            demo_password="",
        ),
    )

    result = accounts.bootstrap_demo(db)

    assert result.id == demo.id
    assert result.password_hash == original_password_hash
    assert len(load_dataset(db, demo.id)["courses"]) > 0
    assert load_dataset(db, regular.id)["courses"] == []


def test_missing_demo_is_not_created_without_an_explicit_password(monkeypatch):
    from types import SimpleNamespace

    from backend import accounts

    db = tenant_session()
    monkeypatch.setattr(
        accounts,
        "settings",
        SimpleNamespace(
            enable_demo_account=True,
            demo_username="missing-demo",
            demo_email="missing@example.edu",
            demo_password="",
        ),
    )

    assert accounts.bootstrap_demo(db) is None
    assert db.query(User).count() == 0


def test_related_teacher_and_course_updates_are_atomic_and_tenant_scoped():
    db = tenant_session()
    first = add_user(db, "linked-first")
    second = add_user(db, "linked-second")
    ensure_workspace(db, first.id, seed=False)
    ensure_workspace(db, second.id, seed=False)
    db.commit()

    teacher = {"id": "t-a", "name": "Dr. A", "expertise_courses": ["cs101"], "availability_slots": [], "max_lectures_per_day": 3}
    course = {"id": "cs101", "name": "CS101 Computing", "type": "theory", "duration": 1, "credit_hours": 3, "contact_hours": 3, "weekly_frequency": 3, "difficulty_level": 2, "allowed_teachers": ["t-a"]}
    save_entity_sets(db, first.id, {"teachers": [teacher], "courses": [course]}, first.id)

    assert load_dataset(db, first.id)["teachers"][0]["expertise_courses"] == ["cs101"]
    assert load_dataset(db, first.id)["courses"][0]["allowed_teachers"] == ["t-a"]
    assert load_dataset(db, second.id)["teachers"] == []
