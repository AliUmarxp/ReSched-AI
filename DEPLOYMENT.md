# Deployment Guide

## Target architecture

- GitHub repository with CI on every push and pull request.
- Dockerized FastAPI application behind a TLS reverse proxy/load balancer.
- Managed PostgreSQL database with automated backups and point-in-time recovery.
- Four web workers for initial deployment; separate scheduling workers are required before high concurrent generation load.
- Static frontend served from the application initially, then optionally moved to a CDN after the Vite migration.

## Local development

1. Copy `.env.example` to `.env` and set local values.
2. Install dependencies with `python -m pip install -r requirements.txt`.
3. Run `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8002 --reload`.
4. Open `http://127.0.0.1:8002`.
5. Run tests with `pytest -q`.

## Docker deployment

Create a `.env` file containing strong unique values:

```text
POSTGRES_PASSWORD=<strong-random-password>
APP_SECRET_KEY=<at-least-32-random-characters>
ADMIN_EMAIL=<administrator-email>
ADMIN_PASSWORD=<strong-administrator-password>
ALLOWED_ORIGINS=https://your-domain.example
```

Then run:

```text
docker compose up --build -d
```

Never commit `.env` or real credentials. Terminate TLS at a reverse proxy or managed platform and keep `SESSION_COOKIE_SECURE=true` in production.

## Free preview: Render + Neon

1. Create a Neon PostgreSQL project and copy its pooled connection string.
2. In Render, create a Blueprint from this GitHub repository. Render detects `render.yaml`.
3. Set `DATABASE_URL` to the Neon connection string, changing the scheme to `postgresql+psycopg://` when necessary.
4. Set `ADMIN_USERNAME`, `ADMIN_EMAIL`, and a strong `ADMIN_PASSWORD`.
5. Set `ALLOWED_ORIGINS` to the final Render HTTPS URL.
6. Deploy and verify `/api/health`, account request, approval, login, dataset save, timetable generation, and export.

The free architecture is for demonstration and acceptance testing. Render free services sleep when inactive, while free database limits and backup policies can change. Upgrade compute and database backup coverage before accepting real university production data.

## GitHub workflow

1. Initialize Git in the project folder if it is not already a repository.
2. Create a private GitHub repository.
3. Commit the source without `.env` or local database files.
4. Push `main`; `.github/workflows/ci.yml` compiles the backend and runs tests.
5. Connect the repository to the selected host and configure environment secrets there.

## Production gates before public launch

- Add Alembic migrations; do not rely on `create_all` for upgrades.
- Complete the built frontend migration so there are no runtime CDN dependencies.
- Add background scheduling workers, queue limits, progress, cancellation, and per-account quotas.
- Add rate limiting, verified email, password reset, session management, and optional MFA.
- Test tenant isolation, authorization, upload limits, and common OWASP risks.
- Run load tests using realistic 300–500-account behavior and concurrent generation jobs.
- Configure database backups, restore drills, health checks, logs, metrics, alerts, and run retention.
- Publish privacy, retention, acceptable-use, and support policies.
