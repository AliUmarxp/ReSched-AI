# Data Entry Improvement Plan

Last updated: 2026-09-16

## 1. Complete the academic data model

- [x] Add a dedicated Programs workspace and manual editor.
- [x] Keep Programs, Courses, Teachers, Sections, Rooms, and Repeat Students tenant-scoped.
- [x] Add clear required fields, sensible defaults, numeric limits, and automatic IDs.

## 2. Simplify manual data entry

- [x] Replace comma-only teacher expertise entry with a searchable course picker.
- [x] Replace comma-only course faculty entry with a searchable faculty picker.
- [x] Synchronize course eligibility and faculty expertise in one atomic database update.
- [x] Let a section select an existing program or type a new program name.
- [x] Make new faculty available for all timetable slots by default and allow users to block exceptions.
- [x] Repair the new-record state so Add does not jump back to an existing record.

## 3. Add guided bulk import

- [x] Provide one Excel workbook with separate, related tabs for each entity type.
- [x] Add sample rows, input highlighting, dropdown validation, and relationship examples.
- [x] Import `.xlsx`, `.xls`, or the existing JSON dataset from the user workspace.
- [x] Keep imported data inside the signed-in tenant only.

## 4. Correct PDF output

- [x] Populate the Faculty column from the actual generated timetable assignments.
- [x] Fall back to a section's manual faculty assignment when a course has no generated entry.

## 5. Performance and verification

- [x] Remove one redundant workspace lookup from the normal dataset read path.
- [x] Add tests for atomic teacher/course updates, tenant isolation, and PDF faculty output.
- [ ] Move frontend CDN dependencies into a production build in the planned React/TypeScript migration.
- [ ] Add server-side background scheduling workers before high concurrent generation load.
