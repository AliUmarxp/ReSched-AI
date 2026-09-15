# ReSched

ReSched is a multi-tenant academic scheduling platform for universities and schools. It gives each approved institution a private workspace for academic data, scheduling policies, timetable generation, validation, reporting, and exports.

## Core capabilities

- Account-request workflow with administrator approval or denial
- Strictly separated administrator and registrar workspaces
- Isolated data, policies, schedules, and exports for every account
- Courses, teachers, sections, rooms/labs, repeat students, and section plans
- Dedicated program management with program code, degree, semester count, and department fields
- Credit hours, contact hours, weekly frequency, and session duration support
- Teacher availability and course eligibility controls
- Configurable scheduling constraints with clear applied/ignored states
- Theory-to-classroom and lab-to-laboratory enforcement
- Repeat-student, teacher, section, room, capacity, and availability protection
- Per-room opt-in for up to two simultaneous sessions; disabled by default
- Timetable views by section, teacher, room, and lab
- Availability lookup, quality reporting, CSV/PDF export, and per-section PDF bundles
- Dataset import/export, version tracking, stale-run protection, and audit events
- Guided Excel workbook import with linked Programs, Courses, Teachers, Sections, Rooms, and Repeat Students sheets

## Roles

### Platform administrator

Administrators review account requests and manage platform access. They cannot view or modify an institution's scheduling data.

### Registrar / institution user

Approved users manage their own institutional dataset, scheduling rules, timetable generation, reports, and exports.

## Local setup

Requirements: Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002
```

Open `http://127.0.0.1:8002`.

Development administrator credentials come from environment variables. Never deploy with sample credentials; configure a strong password and application secret in `.env` or through the hosting platform's secret manager.

## Tests

```powershell
python -m pytest -q
```

## Deployment

The repository includes:

- `Dockerfile` for the application image
- `docker-compose.yml` for application and PostgreSQL services
- `.github/workflows/ci.yml` for automated tests
- `.env.example` for documented configuration
- `render.yaml` for a GitHub-connected Render deployment

For production, use PostgreSQL, HTTPS, secure environment secrets, regular backups, health monitoring, and a reverse proxy or managed container host. Detailed instructions are in [DEPLOYMENT.md](DEPLOYMENT.md).

### Free online demo

The current no-cost preview architecture is Vercel connected to a Neon PostgreSQL database. SQLite is intended only for local development because serverless filesystems are not durable application storage. Institution records, account data, constraints, and schedule runs are stored in PostgreSQL through `DATABASE_URL`.

For a single sample-data account, set `ENABLE_DEMO_ACCOUNT=true` and point
`DEMO_USERNAME` at that account. An existing account keeps its current password.
Leave this disabled for normal deployments; every approved non-demo account starts
with an empty, isolated institutional workspace. `DEMO_PASSWORD` is only required
when the application must create a missing demo account automatically.

## API and exports

Authenticated users can export:

- Timetable CSV: `/api/export/timetable.csv`
- Timetable PDF: `/api/export/timetable.pdf`
- Per-section PDF bundle: `/api/export/section-pdfs.zip`

Schedules become stale when source data or constraints change and must be regenerated before export.

For bulk setup, download `/static/templates/resched-data-entry-template.xlsx` from the
Generate page. The workbook uses separate tabs because programs, courses, teachers,
sections, rooms, and repeat students have different fields but share IDs. ReSched
imports all populated tabs in one operation and validates their relationships.

## Project documentation

- [Implementation status](IMPLEMENTATION_STATUS.md)
- [Deployment guide](DEPLOYMENT.md)
- [Audit and improvement roadmap](PROJECT_AUDIT_AND_IMPROVEMENT_PLAN.md)
- [Data entry improvement plan](DATA_ENTRY_IMPROVEMENT_PLAN.md)

## Security notes

- Passwords are stored using scrypt hashing.
- Sessions use opaque server-side tokens in HttpOnly cookies.
- Scheduling and export APIs are tenant-scoped.
- Administrator routes and institution-user routes are role protected.
- Production mode requires secure configuration and must not use development defaults.

## License

No open-source license has been assigned yet. Add the intended license before distributing the project publicly.
