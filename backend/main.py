from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer, Paragraph, Table, TableStyle

from .accounts import bootstrap_admin, bootstrap_demo
from .api_routes import router as account_router
from .config import settings
from .database import SessionLocal, init_database
from .models import User, Workspace
from .sectionwise_importer import import_sectionwise_dataset
from .scheduler import generate_timetable
from .schemas import DatasetImportPayload, EntityBatchPayload, EntityPayload
from .security import current_user, get_db, workspace_user
from .tenant_store import (
    ENTITY_NAMES,
    DatasetValidationError,
    get_constraint_settings,
    latest_run,
    load_dataset,
    replace_dataset,
    reset_workspace,
    save_ai_profile,
    save_entity_set,
    save_entity_sets,
    save_run,
    serialize_run,
    validate_dataset,
)


ROOT_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT_DIR / "static"


app = FastAPI(title="ReSched AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(account_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
def startup() -> None:
    init_database()
    with SessionLocal() as db:
        bootstrap_admin(db)
        bootstrap_demo(db)


def _default_ai_profile() -> dict[str, Any]:
    return {
        "weights": {
            "compactness": 1.0,
            "early_release": 1.0,
            "day_fairness": 1.0,
            "teacher_balance": 1.0,
            "repeat_protection": 1.0,
        },
        "trained_runs": 0,
    }


def _update_ai_profile(dataset: dict[str, Any], run_result: dict[str, Any]) -> dict[str, Any]:
    profile = dataset.get("aiProfile") or _default_ai_profile()
    weights = dict(profile.get("weights", {}))
    quality = run_result.get("quality", {})
    for key in ["compactness", "early_release", "day_fairness", "teacher_balance", "repeat_protection"]:
        current = float(weights.get(key, 1.0))
        metric = float(quality.get(key, 100))
        gap = max(0.0, (100.0 - metric) / 100.0)
        weights[key] = round(min(2.5, current + gap * 0.08), 3)
    return {"weights": weights, "trained_runs": int(profile.get("trained_runs", 0)) + 1}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": "ReSched AI"}


@app.get("/api/data")
def get_data(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    dataset = load_dataset(db, user.id)
    workspace = db.query(Workspace).filter(Workspace.user_id == user.id).one()
    return {
        "dataset": dataset,
        "datasetVersion": workspace.dataset_version,
        "validation": validate_dataset(dataset),
        "latestRun": serialize_run(latest_run(db, user.id), workspace.dataset_version),
    }


@app.post("/api/seed")
def reset_seed(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    if not (settings.enable_demo_account and user.username == settings.demo_username):
        raise HTTPException(status_code=403, detail="Bundled sample data is available only in the demo account")
    dataset, version = reset_workspace(db, user.id, user.id)
    return {"dataset": dataset, "datasetVersion": version, "latestRun": None}


@app.post("/api/import/section-wise")
def import_section_wise(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    if not (settings.enable_demo_account and user.username == settings.demo_username):
        raise HTTPException(status_code=403, detail="Bundled sample import is available only in the demo account")
    section_wise_root = ROOT_DIR / "imports" / "section-wise" / "SECTION-WISE"
    if not section_wise_root.exists():
        raise HTTPException(status_code=404, detail=f"Folder not found: {section_wise_root}")
    dataset = import_sectionwise_dataset(section_wise_root)
    try:
        saved, version = replace_dataset(db, user.id, dataset, user.id)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "issues": exc.issues})
    return {"dataset": saved, "datasetVersion": version, "latestRun": None, "importPath": str(section_wise_root)}


@app.post("/api/import/dataset")
def import_dataset(body: DatasetImportPayload, db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    try:
        dataset, version = replace_dataset(db, user.id, body.dataset, user.id)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "issues": exc.issues})
    return {"dataset": dataset, "datasetVersion": version, "latestRun": None}


@app.put("/api/entities/{name}")
def update_entity_set(name: str, body: EntityPayload, db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    if name not in ENTITY_NAMES:
        raise HTTPException(status_code=404, detail=f"Unknown entity set: {name}")
    try:
        dataset, version = save_entity_set(db, user.id, name, body.payload, user.id)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "issues": exc.issues})
    return {"dataset": dataset, "datasetVersion": version, "latestRun": None}


@app.put("/api/entities")
def update_entity_sets(body: EntityBatchPayload, db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    try:
        dataset, version = save_entity_sets(db, user.id, body.entities, user.id)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=422, detail={"message": str(exc), "issues": exc.issues})
    return {"dataset": dataset, "datasetVersion": version, "latestRun": None}


@app.post("/api/generate")
def generate(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    dataset = load_dataset(db, user.id)
    issues = validate_dataset(dataset)
    if issues:
        raise HTTPException(status_code=422, detail={"message": "Dataset is not ready for scheduling", "issues": issues})
    constraints = get_constraint_settings(db, user.id)
    result = generate_timetable(dataset, constraints)
    profile = _update_ai_profile(dataset, result)
    result["aiProfile"] = profile
    save_ai_profile(db, user.id, profile)
    workspace = db.query(Workspace).filter(Workspace.user_id == user.id).one()
    run = save_run(db, user.id, workspace.dataset_version, result, user.id)
    return {"run": serialize_run(run, workspace.dataset_version)}


@app.get("/api/runs/latest")
def get_latest_run(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    workspace = db.query(Workspace).filter(Workspace.user_id == user.id).one()
    run = latest_run(db, user.id)
    if not run:
        raise HTTPException(status_code=404, detail="No timetable generated yet")
    return {"run": serialize_run(run, workspace.dataset_version)}


@app.get("/api/rooms/free")
def get_free_rooms(day: str, slot_id: str, db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> dict[str, Any]:
    run_row = latest_run(db, user.id)
    dataset = load_dataset(db, user.id)
    if not run_row:
        raise HTTPException(status_code=404, detail="No timetable generated yet")
    run = run_row.payload
    occupied_counts: dict[str, int] = {}
    for entry in run["entries"]:
        if entry["day"].lower() == day.lower() and slot_id in entry["slot_ids"]:
            occupied_counts[entry["room_id"]] = occupied_counts.get(entry["room_id"], 0) + 1
    free_rooms = [
        room for room in dataset["rooms"]
        if occupied_counts.get(room["id"], 0) < (2 if room.get("allow_parallel_sessions", False) else 1)
    ]
    return {"day": day, "slot_id": slot_id, "freeRooms": free_rooms, "count": len(free_rooms)}


@app.get("/api/data-policy")
def data_policy() -> dict[str, Any]:
    return {
        "source_of_truth": "local_project_dataset",
        "allowed_data_sources": [
            "project seed data",
            "SECTION-WISE import files provided by project team",
            "admin-entered AMS-approved records",
        ],
        "not_used_as_data_source": [
            "third-party/open-source repository databases",
        ],
        "repo_usage_policy": "Open-source repositories are used only for feature ideas, UX patterns, and algorithm inspiration.",
    }


@app.get("/api/export/timetable.csv")
def export_csv(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> StreamingResponse:
    run_row = latest_run(db, user.id)
    if not run_row:
        raise HTTPException(status_code=404, detail="No timetable generated yet")
    workspace = db.query(Workspace).filter(Workspace.user_id == user.id).one()
    if run_row.dataset_version != workspace.dataset_version:
        raise HTTPException(status_code=409, detail="The timetable is stale. Regenerate it before export.")
    run = run_row.payload
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "section_name",
            "course_name",
            "teacher_name",
            "room_name",
            "day",
            "start_time",
            "end_time",
            "course_type",
            "soft_score",
        ],
    )
    writer.writeheader()
    for entry in run["entries"]:
        writer.writerow({field: entry.get(field, "") for field in writer.fieldnames})
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=resched_ai_timetable.csv"},
    )


@app.get("/api/export/timetable.pdf")
def export_pdf(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> StreamingResponse:
    run_row = latest_run(db, user.id)
    if not run_row:
        raise HTTPException(status_code=404, detail="No timetable generated yet")
    workspace = db.query(Workspace).filter(Workspace.user_id == user.id).one()
    if run_row.dataset_version != workspace.dataset_version:
        raise HTTPException(status_code=409, detail="The timetable is stale. Regenerate it before export.")
    run = run_row.payload

    dataset = load_dataset(db, user.id)
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=landscape(A4), leftMargin=18, rightMargin=18, topMargin=16, bottomMargin=16)
    styles = getSampleStyleSheet()
    story = []
    for index, section_name in enumerate(sorted(run["views"]["section"].keys())):
        if index:
            story.append(PageBreak())
        story.extend(_section_pdf_story(section_name, run["views"]["section"][section_name], dataset, run, styles))
    document.build(story)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=resched_ai_timetable.pdf"},
    )


@app.get("/api/export/section-pdfs.zip")
def export_section_pdfs_zip(db: Session = Depends(get_db), user: User = Depends(workspace_user)) -> StreamingResponse:
    run_row = latest_run(db, user.id)
    if not run_row:
        raise HTTPException(status_code=404, detail="No timetable generated yet")
    workspace = db.query(Workspace).filter(Workspace.user_id == user.id).one()
    if run_row.dataset_version != workspace.dataset_version:
        raise HTTPException(status_code=409, detail="The timetable is stale. Regenerate it before export.")
    run = run_row.payload
    dataset = load_dataset(db, user.id)
    zip_buffer = io.BytesIO()
    with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as archive:
        for section_name, entries in sorted(run["views"]["section"].items()):
            pdf_buffer = io.BytesIO()
            document = SimpleDocTemplate(
                pdf_buffer,
                pagesize=landscape(A4),
                leftMargin=18,
                rightMargin=18,
                topMargin=16,
                bottomMargin=16,
            )
            styles = getSampleStyleSheet()
            document.build(_section_pdf_story(section_name, entries, dataset, run, styles))
            archive.writestr(f"{section_name.replace('/', '-')}.pdf", pdf_buffer.getvalue())
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=resched_ai_section_timetables.zip"},
    )


def _section_pdf_story(section_name: str, entries: list[dict[str, Any]], dataset: dict[str, Any], run: dict[str, Any], styles: Any) -> list[Any]:
    section = next((item for item in dataset["sections"] if item["name"] == section_name), {})
    title = Paragraph(
        "NASTP INSTITUTE OF INFORMATION TECHNOLOGY (NIIT): CLASSES SCHEDULE",
        styles["Title"],
    )
    subtitle_text = f"{section.get('semester', '')} Sem : {section.get('degree', section_name)}-{section.get('cohort', '')} | {section_name}"
    subtitle = Paragraph(subtitle_text, styles["Heading2"])
    score = Paragraph(
        f"ReSched AI | Quality Score: {run['quality']['overall']}/100 | Hard Conflicts: {run['report']['hard_conflicts']} | Timing: 09:00-16:30",
        styles["Normal"],
    )
    return [title, subtitle, score, Spacer(1, 8), _section_grid_table(entries, dataset), Spacer(1, 10), _section_course_table(section, entries, dataset)]


def _section_grid_table(entries: list[dict[str, Any]], dataset: dict[str, Any]) -> Table:
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods_by_index: dict[int, dict[str, Any]] = {}
    for slot in dataset["timeSlots"]:
        periods_by_index.setdefault(int(slot["period_index"]), slot)
    periods = [periods_by_index[index] for index in sorted(periods_by_index)]
    columns: list[dict[str, Any]] = []
    for period in periods:
        columns.append({"type": "slot", "period": period})
        if int(period["period_index"]) == 4:
            columns.append({"type": "break"})

    header = ["TIME"]
    for column in columns:
        if column["type"] == "break":
            header.append("Break\n1250-1320")
        else:
            period = column["period"]
            header.append(f"{period['start_time'].replace(':', '')}-{period['end_time'].replace(':', '')}")
    rows: list[list[Any]] = [header]
    cell_style = ParagraphStyle(
        "TimetableCell",
        fontName="Helvetica",
        fontSize=6.2,
        leading=7.0,
        alignment=1,
        wordWrap="CJK",
    )
    style_commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c7c7c7")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]
    col_by_period: dict[int, int] = {}
    for col_index, column in enumerate(columns, start=1):
        if column["type"] == "slot":
            col_by_period[int(column["period"]["period_index"])] = col_index
        else:
            style_commands.append(("BACKGROUND", (col_index, 1), (col_index, len(days)), colors.HexColor("#e5e7eb")))
            style_commands.append(("FONTNAME", (col_index, 1), (col_index, len(days)), "Helvetica-Bold"))

    for row_index, day in enumerate(days, start=1):
        row: list[Any] = [day[:3]]
        occupied: set[int] = set()
        day_entries = [entry for entry in entries if entry["day"] == day]
        starts = {int(entry["start_index"]): entry for entry in day_entries}
        for column in columns:
            if column["type"] == "break":
                row.append("BREAK")
                continue
            period_index = int(column["period"]["period_index"])
            if period_index in occupied:
                row.append("")
                continue
            entry = starts.get(period_index)
            if not entry:
                row.append("")
                continue
            text = f"<b>{entry['course_name']}</b><br/>{entry['teacher_name']}<br/>{entry['room_name']}"
            row.append(Paragraph(text, cell_style))
            start_col = col_by_period[int(entry["start_index"])]
            end_col = col_by_period[int(entry["end_index"])]
            if end_col > start_col:
                style_commands.append(("SPAN", (start_col, row_index), (end_col, row_index)))
            bg = "#fee8a6" if entry["course_type"] == "lab" else "#ffffff"
            style_commands.append(("BACKGROUND", (start_col, row_index), (end_col, row_index), colors.HexColor(bg)))
            occupied.update(range(int(entry["start_index"]) + 1, int(entry["end_index"]) + 1))
        rows.append(row)

    table = Table(rows, repeatRows=1, colWidths=[34, 78, 78, 78, 78, 42, 78, 78, 78])
    table.setStyle(TableStyle(style_commands))
    return table


def _section_course_table(section: dict[str, Any], entries: list[dict[str, Any]], dataset: dict[str, Any]) -> Table:
    courses = {course["id"]: course for course in dataset["courses"]}
    teachers = {teacher["id"]: teacher for teacher in dataset["teachers"]}
    rows: list[list[Any]] = [["S No", "Course Code", "Cr Hrs", "Cont Hrs", "Course Title", "Faculty"]]
    for index, course_id in enumerate(section.get("required_courses", []), start=1):
        course = courses.get(course_id, {})
        code, title = _split_course_name(course.get("name", course_id.upper()))
        scheduled_names = sorted({
            str(entry.get("teacher_name", "")).strip()
            for entry in entries
            if entry.get("course_id") == course_id and entry.get("teacher_name")
        })
        assigned_teacher = section.get("course_teachers", {}).get(course_id)
        configured_name = teachers.get(assigned_teacher, {}).get("name", "")
        faculty = ", ".join(scheduled_names) or configured_name
        rows.append(
            [
                f"{index}.",
                code,
                str(course.get("credit_hours", "")),
                str(course.get("contact_hours", 3 if course.get("type") == "lab" else course.get("credit_hours", ""))),
                title,
                faculty,
            ]
        )
    table = Table(rows, repeatRows=1, colWidths=[34, 70, 45, 52, 300, 150])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c7c7c7")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _split_course_name(name: str) -> tuple[str, str]:
    parts = name.split(" ", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1]
