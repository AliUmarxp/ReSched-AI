# ReSched AI — Project Audit and Improvement Plan

Date: 2026-09-15

## 1. Executive assessment

ReSched AI is a functional academic scheduling prototype with a clear domain focus: section-course scheduling, repeat-student clash protection, teacher/room constraints, timetable views, and PDF/CSV exports. Its strongest parts are the real SECTION-WISE dataset, explainable placement notes, and a compact end-to-end Python/SQLite/React implementation.

It is not yet production-ready. The highest-risk issue is correctness: the active scheduler uses a one-pass greedy assignment even though a recursive search method exists, and the current dataset produces 146/149 sessions rather than the documented 149/149. The adaptive weight profile is updated but never consumed by candidate scoring. Authentication is presentation-only, entity payloads are unvalidated, destructive actions have no confirmation, and edited data can leave the displayed latest run stale.

The UI is usable as a technical demo but not yet shaped around an administrator's workflow. It has dense navigation, undifferentiated panels, wide tables/grids that depend on horizontal scrolling, weak status/error feedback, and a detail panel that disappears below very large desktop widths.

Recommended sequence: fix scheduler truthfulness and data safety first; then redesign the shell and core scheduling workflow; then add manual scheduling, comparison, roles, and operational features.

## 2. Current architecture

### Frontend

- One 1,724-line JSX file loaded through Babel in the browser.
- React 18, ReactDOM, Tailwind runtime, Babel, and Lucide are fetched from public CDNs.
- No build pipeline, package manifest, component tests, routing library, or frontend type checking.
- State is local React state; the login identity is stored in `localStorage`.

### Backend

- FastAPI application with synchronous endpoints.
- SQLite stores entire entity sets and run results as JSON blobs.
- Scheduling engine is a custom constraint checker plus heuristic candidate scorer.
- DOCX import reads Word XML directly from a fixed project folder.
- CSV, combined PDF, and per-section PDF ZIP exports are generated server-side.

### Current dataset and verified runtime result

- 4 programs, 12 sections, 52 courses, 37 teachers, 15 rooms/labs, 35 time slots, and 7 repeat-student records.
- Latest stored run: 146 scheduled, 3 unscheduled, 0 conflicts, overall quality 86/100.
- A fresh generation reproduced the same result in about one second.
- The database contains 23 stored run payloads and is about 13 MB, with no retention or cleanup policy.
- Python modules compile successfully, but there is no automated test suite.

## 3. Constraints by category

### A. Hard academic and collision constraints currently enforced

These reject a candidate placement:

1. Teacher cannot be double-booked.
2. Room/lab cannot be double-booked.
3. Section cannot be double-booked.
4. Repeat students' current-section sessions cannot overlap their repeated-course sessions.
5. Teacher must list the course in expertise and be allowed for that course.
6. Teacher must be available for every slot in a multi-slot session.
7. Same section-course keeps the same teacher across weekly sessions.
8. Repeated meetings of the same section-course must occur on different days.
9. Theory uses classrooms; labs use lab rooms.
10. Room capacity must meet section strength.
11. Sessions cannot cross the configured midday break.
12. Friday periods 4 and 5 are protected as a prayer/break window.
13. A section's internal daily gap cannot exceed the calculated limit.

### B. Structural/contact-hour constraints currently enforced

1. Lab courses become one continuous three-period session.
2. Three-credit theory courses become a two-period block plus a one-period meeting.
3. Two-credit theory courses become one continuous two-period block.
4. Other theory courses become one-period meetings up to a capped frequency.
5. Only contiguous time windows of one, two, or three periods are candidates.

### C. Soft optimization constraints currently scored or reported

1. Compact section days and fewer internal gaps.
2. Earlier release and preference for earlier difficult courses.
3. Fair distribution of section load across days.
4. Teacher daily load balance.
5. Teacher and section consecutive-session warnings.
6. Section daily span/overstretch warnings.
7. Daily concentration of difficult courses.
8. Reduced room-capacity waste.
9. Continuous/morning lab preference.
10. Teacher idle-time and back-to-back considerations.

Important wording correction: teacher daily and consecutive loads are soft warnings/penalties, not hard caps, despite the current UI saying they are capped.

### D. Data and import constraints

1. SECTION-WISE import reads only `.docx` files from one fixed local directory.
2. It assumes the second Word table is the course table and expects at least six columns.
3. Program and semester are inferred from folder/file naming conventions.
4. Teacher identity is derived mainly from the last name, so collisions are possible.
5. Imported room capacities and section strengths are defaults, not extracted authoritative values.
6. Imported teacher availability is set to all slots rather than extracted from source data.
7. Repeat-student records generated by the importer are samples, not enrollment-authoritative records.
8. Import writes entity sets one by one and is not atomic.
9. There is no import preview, validation summary, duplicate-resolution flow, or rollback.

### E. Technical/architecture constraints

1. The active generation method is greedy; the recursive `_search` method is not called.
2. Adaptive AI weights are persisted but not applied to candidate scores.
3. Entity sets are schema-less JSON payloads with no referential validation.
4. Mutable IDs can silently break references between teachers, courses, sections, and runs.
5. Any entity edit can make the latest run stale, but the UI does not mark or invalidate it.
6. Run payloads duplicate large views/explanations and grow SQLite indefinitely.
7. Frontend operation depends on internet availability for four CDN scripts.
8. Browser-side Babel and development React are unsuitable for a production deployment.
9. The application has no migrations, environment configuration, structured logging, metrics, or background job queue.
10. There are no unit, integration, API, scheduler regression, import fixture, accessibility, or end-to-end tests.

### F. Security and governance constraints

1. Credentials are hard-coded in backend source and demo credentials are shown in the UI.
2. Login returns identity data but no signed session/token; API endpoints remain unauthenticated.
3. All CORS origins, methods, and headers are allowed.
4. There is no role enforcement even though the response labels the user as admin.
5. There is no audit trail for entity changes, imports, generation, resets, or exports.
6. Reset, import, update, and generation endpoints lack CSRF/session protection and authorization.
7. User-provided JSON entity payloads have no domain validation or size limits.
8. There is no secrets/configuration separation for development versus deployment.

### G. UI, responsive, and accessibility constraints

1. Ten top-level navigation items expose the data model instead of the admin workflow.
2. The same page title and global actions dominate every screen, reducing contextual clarity.
3. The dashboard shows totals but not actionable readiness, blockers, stale-data state, or next steps.
4. Entity tables have no search, filter, sort, pagination, bulk actions, inline validation, dirty-state warning, or undo.
5. Delete and Restore Seed execute without confirmation.
6. Success/error messages are passive header boxes rather than accessible toasts or an `aria-live` region.
7. The timetable has a fixed minimum width around 960 px and relies on horizontal scrolling.
8. At widths below 1024 px the sidebar becomes a long full-width block instead of a mobile drawer/bottom navigation.
9. The AI explanation panel is hidden below the `2xl` breakpoint, leaving no equivalent detail interaction for most laptops/tablets.
10. Lab/theory differentiation leans heavily on color and lacks a persistent legend/filter strategy.
11. Dense tiny text, truncation, and wide matrices make scanning and keyboard use difficult.
12. Row selection is click-only; table rows are not semantic buttons and have no keyboard interaction.
13. Icon-only remove buttons rely on `title` rather than an accessible label.
14. Loading states do not provide skeletons/progress and long actions lack cancellation.
15. No empty/search/no-result states exist for most data pages.

## 4. Functionality that is missing or needs strengthening

### P0 — correctness, safety, and truthful behavior

1. Activate a bounded backtracking/repair strategy or adopt an optimizer such as OR-Tools CP-SAT.
2. Guarantee that a “successful” run schedules all required sessions and report infeasibility clearly when it cannot.
3. Feed `aiProfile.weights` into scoring or remove the adaptive-learning claim.
4. Add dataset schemas and cross-entity validation before save/generation.
5. Make imports transactional and add preview, warnings, and rollback.
6. Mark schedules stale whenever source entities change; require regeneration before authoritative export.
7. Replace demo authentication with hashed credentials, signed sessions/tokens, endpoint authorization, and restricted CORS.
8. Reconcile README/TODO/UI claims with verified runtime behavior and slot definitions.
9. Add scheduler regression tests for the shipped 149-session fixture.

### P1 — core administrator workflow

1. Readiness checker showing invalid references, missing teachers, unavailable rooms, and capacity bottlenecks before generation.
2. Run history with timestamps, dataset version, score, scheduled count, status, and compare action.
3. Manual drag/drop or edit of a class with immediate constraint revalidation and undo.
4. Lock/pin approved sessions before regeneration.
5. Conflict resolution suggestions for unscheduled sessions, including the constraints that could be relaxed.
6. Search, filter, sort, bulk edit/import, and pagination for all master-data screens.
7. Teacher workload, room utilization, section gap, and repeat-student coverage reports.
8. Configurable academic calendar, slot templates, breaks, holidays, and department-specific rules.
9. Real student enrollment import for exact repeat/elective clash protection.
10. Export controls for selected sections/teachers/rooms and branded print templates.

### P2 — scale, governance, and advanced optimization

1. Department Scheduler, Reviewer, and Read-only roles with approval workflow.
2. Audit log, versioned datasets, rollback, and run reproducibility.
3. Multiple optimizer strategies/seeds with side-by-side comparison.
4. Room feature requirements, campus/building travel time, shared cohorts, electives, and linked lecture/lab rules.
5. Teacher preference levels, minimum/maximum weekly load, lunch windows, and fairness across semesters.
6. Notifications and publish workflow to AMS/student/teacher portals.
7. Background scheduling jobs, progress reporting, cancellation, concurrency control, and performance benchmarks.
8. API documentation for AMS integration plus import/export contracts.

## 5. UI/GUI redesign plan

### Design direction

Use a calm academic operations aesthetic: deep navy navigation, warm off-white workspace, teal as the main action color, amber for warnings, red only for blocking conflicts, and blue for informational states. Reduce card borders/shadows, increase spacing and text hierarchy, and reserve strong color for status and action.

The interface should answer three questions immediately:

1. Is the scheduling data ready?
2. Can a complete timetable be generated?
3. What requires attention before publishing?

### Information architecture

Replace ten equal top-level items with five workflow areas:

1. **Overview** — readiness, latest run, blockers, utilization, and recent activity.
2. **Academic Data** — grouped sub-navigation for sections, courses, teachers, rooms, repeat students, and time rules.
3. **Schedule Workspace** — generate, compare runs, inspect timetable, manually adjust, and lock sessions.
4. **Reports & Exports** — conflicts, quality, utilization, repeat protection, and export center.
5. **Settings** — institution, term, roles, data sources, optimization weights, and integrations.

### Global shell

- Collapsible 240 px desktop sidebar with grouped items and clear active state.
- Mobile/tablet drawer triggered by a persistent top bar; never render the full sidebar above content.
- Contextual page header with breadcrumb, page title, status chip, and only relevant primary action.
- Global dataset/term selector and “Last saved / Schedule stale” indicator.
- Toast system with `aria-live`, plus inline field and page-level error summaries.
- Confirmation dialogs for delete, reset, overwrite import, and publish actions.

### Overview dashboard

- Top status banner: Ready, Warnings, or Blocked, with direct “Review issues” action.
- Primary KPIs: scheduled/required, hard conflicts, unscheduled sessions, overall quality.
- “Next best action” card driven by readiness and run status.
- Quality trend and last five runs rather than only static progress bars.
- Compact teacher-load and room-utilization charts.
- Recent activity/audit summary.
- Remove technical marketing panels from the daily operations dashboard; move algorithm explanations to Help/About.

### Academic Data workspace

- Reusable data-table pattern: search, filters, sort, column visibility, pagination, multi-select, bulk actions.
- Split-panel editor on desktop; full-screen drawer on tablet/mobile.
- Read-only stable IDs; generate IDs internally and show them only in an advanced section.
- Inline validation, required markers, dependency impact, and unsaved-change guard.
- Human-readable selectors instead of comma-separated ID textareas.
- Import center with upload/drop zone, mapping preview, row-level issues, duplicate resolution, and commit summary.

### Schedule Workspace

- Three-step flow: Validate Data → Configure Run → Generate & Review.
- Show hard/soft constraints as configurable policy groups with descriptions and priority.
- Generation state with progress, elapsed time, strategy, cancel button, and clear completion status.
- Timetable toolbar: view type, entity search, department/semester filters, legend, zoom/density, print/export.
- Desktop week grid with sticky day/time headers and a bottom/right details drawer.
- Tablet daily/three-day mode and mobile agenda mode instead of forcing the desktop grid.
- Click/keyboard-select a class to open details and explanation on every breakpoint.
- Manual move drawer shows valid alternatives and reasons invalid slots are blocked.
- Lock icon on approved sessions and a regeneration option that respects locks.

### Reports & Exports

- Separate blocking conflicts, soft warnings, quality metrics, and audit evidence.
- Make every metric drillable to affected sessions/entities.
- Replace raw rejection counts as primary KPIs; counts of internal candidate rejections are diagnostic, not user outcomes.
- Add workload and utilization tables/charts with filters.
- Export center with format, scope, branding, and preview controls.

### Visual system

- Typography: 16 px base, 14 px dense table text, 12 px only for metadata; consistent 1.4–1.6 line height.
- Spacing: 4/8/12/16/24/32 scale.
- Radii: 8 px controls, 12 px cards/dialogs.
- Shadows: one subtle elevation for overlays; use borders/background contrast for panels.
- Status chips: neutral, info, success, warning, critical with icon + text, never color alone.
- Timetable entries: course color family plus visible Lab/Theory tag, duration, and conflict/lock state.
- Add an always-visible legend and meet WCAG AA contrast targets.

### Accessibility and responsive acceptance criteria

- All functionality operable by keyboard with a visible focus indicator.
- Semantic buttons/links for selectable rows and timetable entries.
- Every icon-only control has an accessible name.
- Errors are associated with fields and announced.
- 200% zoom remains usable without lost controls.
- Desktop: 1280 px and above; tablet: 768–1279 px; mobile: 360–767 px.
- No page-level horizontal scrolling. Only intentionally scrollable data regions may scroll.
- Mobile timetable defaults to an agenda/day list.
- Explanation/details remain reachable at every viewport.

## 6. Implementation roadmap

### Phase 0 — establish a reliable baseline

- Add project configuration, pinned frontend dependencies, environment settings, and a repeatable run command.
- Add tests around dataset validation, hard constraints, imports, and the shipped scheduling fixture.
- Update documentation to the verified 146/149 baseline until the solver is corrected.

Acceptance: one command runs checks; documentation and UI report exactly what the engine returns.

### Phase 1 — correctness and data safety

- Replace the greedy active path with bounded search/repair or CP-SAT.
- Apply configured weights to scoring.
- Introduce Pydantic entity/dataset schemas and referential checks.
- Add dataset versioning, stale-run detection, atomic import, and confirmation dialogs.

Acceptance: the shipped fixture is either 149/149 with zero hard conflicts or produces a reproducible infeasibility explanation; invalid datasets cannot be committed.

### Phase 2 — frontend foundation and shell

- Add a production frontend build (recommended: Vite + React + TypeScript).
- Split API, state, layout, table, forms, timetable, reports, and dialogs into modules.
- Implement tokens, responsive shell, toast/dialog system, error boundary, and loading states.

Acceptance: no runtime CDN/Babel dependency; all main pages work at 360, 768, 1280, and 1440 px.

### Phase 3 — core UX redesign

- Build Overview, Academic Data, Import Center, and Generate/Review workflow.
- Add searchable data tables and validated drawers.
- Build responsive timetable modes and universal details drawer.

Acceptance: an administrator can import/check data, fix issues, generate, inspect, and export without editing raw IDs.

### Phase 4 — operational scheduling features

- Add manual moves, valid-alternative suggestions, locks, undo, run history, and comparison.
- Add workload/utilization/repeat-protection reports and scoped export preview.

Acceptance: manual changes are revalidated immediately and every published schedule is traceable to a dataset/run version.

### Phase 5 — production hardening

- Implement real authentication/roles, restricted CORS, audit logging, migrations, retention, monitoring, and background jobs.
- Add deployment packaging and AMS integration contracts.

Acceptance: protected endpoints, recoverable data changes, observable jobs, and documented deployment/backup procedures.

## 7. Recommended first implementation slice

The first build iteration should remain deliberately narrow:

1. Add regression tests and dataset validation.
2. Fix the active scheduler so the shipped dataset does not lose three sessions.
3. Make adaptive weights real or remove the claim.
4. Add stale-run detection and truthful statuses.
5. Build the new responsive shell, Overview readiness banner, and Schedule Workspace timetable/details drawer.
6. Add confirmation dialogs and accessible toast/error feedback.

This slice removes the largest trust risks while creating the visual foundation for the later data-management and reporting redesign.

## 8. Success metrics

- 100% of required sessions scheduled for the accepted fixture, or explicit proven infeasibility.
- Zero hard conflicts after generation and after every manual move.
- No stale schedule can be exported without a warning/override.
- Core administrator flow completed without raw ID entry.
- Main screens pass keyboard and WCAG AA checks.
- No unintended page-level horizontal scroll at target viewports.
- Automated regression coverage for every hard constraint and import fixture.
- Run history remains bounded through a documented retention policy.
