# ReSched AI

Repeat-student aware university timetable optimizer for NIIT-style academic scheduling. The app uses the local project dataset, SECTION-WISE import files, or admin-entered AMS-approved records as the data source; third-party repositories are only used for feature and UX inspiration.

## Project Deliverables

- Source code: `backend/`, `static/`
- Extracted demo dataset: `data/section-wise-extracted-data.json`, `data/section-wise-course-rows.csv`
- Final report and presentation: `presentation pptx and report word file/`
- Project notes: `TODO.txt`, `docs/section-wise-extraction.md`
- License: `LICENSE`

## Run

### Fresh Clone

After cloning, the project can run locally without copying the SQLite database manually. The app creates `data/resched_ai.sqlite3` automatically from the included seed data when it starts.

Requirements on the computer:

- Python 3.10 or newer
- Internet connection for first-time `pip install`

One-command setup:

```powershell
.\RUN_PROJECT.ps1
```

Manual setup:

Create a virtual environment if needed:

```powershell
python -m venv .venv
.\.venv\Scripts\pip.exe install -r requirements.txt
```

Start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8002
```

Open:

```text
http://127.0.0.1:8002
```

Login:

```text
admin / admin123
```

The local SQLite database is generated automatically and is intentionally not committed to Git.

## What It Demonstrates

- CSP-style modeling for section-course sessions
- Heuristic/backtracking assignment with hard-constraint rejection
- Teacher, room, section, lab, capacity, expertise, availability, and repeat-student protection
- Same section-course teacher consistency across all weekly lectures
- 3-credit theory courses use a hard 2+1 weekly split
- 2-credit theory courses use a continuous 2-hour block where feasible
- Labs stay one continuous 3-slot block
- Section day gaps are capped so students are not held from morning to late day unnecessarily
- Same course for a section is spread across different days where possible
- Friday prayer and midday break protection
- Teacher daily load and consecutive-lecture warnings
- Heuristic scoring for compactness, early release, teacher balance, day fairness, difficult course timing, and continuous lab blocks
- Explainable AI panel for every scheduled class
- Section Subject Plan page for mapping sections to semester subjects
- Matrix-style teacher availability and course-picker admin inputs
- Real SECTION-WISE plan extraction notes in `docs/section-wise-extraction.md`

## Current Demo Result

After importing `SECTION-WISE` docs, the dataset schedules 149/149 weekly sessions with 0 hard conflicts and 85/100 quality. Labs are exported as continuous three-slot blocks, 3-credit theory courses are split as 2+1, and 2-credit theory courses are exported as 2-hour blocks.

## Export

- CSV: `/api/export/timetable.csv`
- PDF: `/api/export/timetable.pdf`
- Per-section PDF ZIP: `/api/export/section-pdfs.zip`

## Extracted Files

- `data/section-wise-extracted-data.json`
- `data/section-wise-course-rows.csv`

Generated local outputs such as SQLite database files and timetable ZIP exports are ignored by Git.

## Repository Notes

Raw SECTION-WISE DOCX import files are ignored because they may contain institution-specific academic records. The project keeps the cleaned extracted JSON/CSV dataset for demo and evaluation use.

## Fresh Clone Checklist

- Code: included
- Cleaned demo dataset: included
- Report and presentation: included
- Local SQLite database: auto-generated on first run
- Raw import documents: not included
- Virtual environment: created locally by `RUN_PROJECT.ps1`
