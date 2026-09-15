# ReSched AI Implementation Status

Last updated: 2026-09-16

## Tenant onboarding and cloud persistence fix

- New approved accounts now receive an empty, isolated academic workspace instead of bundled sample records.
- Only the configured demo account can receive or restore the bundled sample dataset.
- Regular users retain full tenant-scoped Add/Edit/Delete and JSON import/export capabilities.
- Entity editing uses draft-friendly validation; strict room/readiness validation runs before schedule generation and full dataset import.
- Added tenant isolation tests covering empty onboarding, demo-only seeding, CRUD, deletion, and dataset import.
- Normalized provider PostgreSQL URLs to the Psycopg 3 dialect and disabled persistent SQLAlchemy pools on Vercel serverless functions.
- Made the demo dataset opt-in and assignable to one existing account without resetting that account's password; all other newly approved accounts start blank.
- Corrected the HTTP test-client dependency used by CI.

## Latest delivery: shared rooms and interface refinement

- Added a per-room **Shared at Same Time** opt-in. It is disabled by default and permits at most two overlapping sessions only for the selected room.
- Teacher and section collision protection remains active for shared rooms; a third concurrent session is rejected.
- Free-room lookup now accounts for single-session versus two-session occupancy.
- Added searchable entity tables, clearer toggle controls, compact navigation, responsive horizontal navigation on smaller screens, and a warmer professional visual system.
- Replaced academic/demo-style workspace wording with concise production-facing labels.
- Verified on localhost by enabling Room 101, saving it, and generating 54 sessions with zero hard conflicts (quality score 93/100).

## Completed

- Audited the original application, scheduler, importer, database, exports, security, and UI.
- Documented categorized constraints, product gaps, UI redesign, roadmap, and success criteria.
- Added environment-based production configuration with production safety checks.
- Added SQLAlchemy database support for SQLite development and PostgreSQL production.
- Added tenant-scoped users, workspaces, entity sets, constraint settings, schedule runs, sessions, and audit events.
- Added account signup with detailed organization/user profile and pending approval state.
- Added administrator request listing plus approve/deny workflow.
- Added scrypt password hashing and opaque server-side sessions in HttpOnly cookies.
- Protected private dataset, scheduling, room, and export APIs by authenticated account.
- Added a private seeded workspace for every approved account.
- Added dataset versioning and stale-run detection; stale schedules cannot be exported.
- Added atomic JSON dataset import and cross-entity validation.
- Added a categorized constraint catalog with locked integrity rules and account-specific policy/quality settings.
- Connected constraint settings and adaptive profile weights to the scheduler.
- Added deterministic multi-start scheduling, improving the imported legacy baseline from 146 to 147 scheduled sessions in testing.
- Added signup, login, admin request, and constraint-policy UI surfaces.
- Enforced strict role separation: administrators can only manage platform access, while university users own scheduling, data, constraints, reports, and exports.
- Removed academic-project language and algorithm demonstrations from active product screens; implementation details remain internal.
- Fixed the account-request tab crash caused by third-party icon DOM mutation and improved API validation messages.
- Backfilled course credit hours, contact hours, and weekly frequency for existing and new workspaces.
- Normalized table presentation for uppercase identifiers, title-cased types, and explicit missing-value markers.
- Replaced the blue/green visual base with a warmer burgundy, ivory, charcoal, and restrained status-color system.
- Added Docker/PostgreSQL deployment scaffolding and GitHub Actions CI.
- Added initial scheduler and validation regression tests.

## In progress / next

1. Replace multi-start greedy scheduling with bounded repair or CP-SAT to reach a complete 149/149 schedule when feasible.
2. Add detailed feasibility diagnostics and configurable parameters for each policy constraint.
3. Add manual timetable move/swap, teacher-wise editing, locks, undo, and immediate revalidation.
4. Normalize high-volume scheduling data and add Alembic migrations before public production deployment.
5. Move scheduling to a background job queue with progress/cancellation for concurrent users.
6. Replace runtime CDN/Babel frontend with Vite + React + TypeScript and pinned dependencies.
7. Complete the simplified responsive UI shell, role-specific navigation, dashboard, data tables, and mobile timetable.
8. Add run history/comparison, reports, scoped data export, audit-log UI, and account administration.
9. Add rate limiting, email verification/approval notifications, password reset, and optional MFA.
10. Run load, accessibility, browser, security, backup/restore, and deployment smoke tests.

## Known blockers / truthful status

- The imported 149-session legacy dataset is not yet completely scheduled: current multi-start result is 147/149 with zero hard conflicts.
- The frontend is still a transitional single-file JSX application and still uses public runtime CDNs.
- Database tables currently use create-on-start; migration tooling is still required for controlled production schema upgrades.
- Approval is visible in the application, but email delivery is not configured yet. Users log in with the password they selected after approval.
- A four-worker web deployment can support early testing, but CPU-heavy generation must move to workers before claiming reliable 300–500 concurrent-user scale.

## Decision log

- PostgreSQL is the production database; SQLite remains a local-development fallback.
- Each approved account owns an isolated workspace and dataset version history.
- Users choose credentials during signup; administrators approve access rather than creating or emailing plaintext passwords.
- Teacher, room, and section collision constraints cannot be disabled.
- Other hard policy constraints support Apply/Ignore; quality constraints support Apply/Ignore plus weight.
- Exports are blocked when the last schedule predates a data or constraint change.
