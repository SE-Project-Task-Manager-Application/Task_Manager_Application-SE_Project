# Deviations from Submitted Documents

**Project:** Task Manager Application
**Documents covered:** SRS, SAD, Test Plan (STP), and the course Part-2 deliverables schedule
**Owner:** Syed (Scrum Master)

This file records every place where what we build or do differs from what the submitted documents say, with the reason. The course asks us to document deviations and explain them at the final demo, so add an entry when the change happens, not at the end.

**When to add an entry:** any time the product, the schedule, the test approach or the architecture differs from the SRS, SAD or STP.
**How:** add the next ID (D-04, D-05, ...), keep each field to a sentence or two, and link the issue or PR where useful.
**Status values:** *Applied* (it has happened), *Proposed* (the team has not confirmed it yet), *Open* (still to be decided).

---

## 1. Deviations

### D-01 - Test schedule
- **Logged:** 2026-10-11
- **Document:** STP, Schedule
- **Planned:** test environment setup 03-10-2026; test execution 03-10-2026 to 20-10-2026; UAT / final review 31-10-2026.
- **What we are doing instead:** the test environment is built in Sprint 0 (from 10-10-2026, tasks S-06 and S-07a). Test execution runs inside Sprint 1 and Sprint 2 (19-10-2026 to 30-10-2026), at the same time as development, with each story tested as it lands. Final review happens before the 30-10-2026 development freeze.
- **Why:** no build existed on 03-10-2026, and the course Part-2 schedule fixes the sprint weeks and the freeze date.
- **Impact:** the test window is shorter and overlaps development. Every story carries a test-case checklist so coverage is still tracked in the RTM.
- **Status:** Applied

### D-02 - Development schedule compared with the course schedule
- **Logged:** 2026-10-11
- **Document:** Course Part-2 deliverables (not the SRS, SAD or STP; logged for transparency)
- **Planned (course):** dry run 12-10 to 16-10; Sprint 1 19-10 to 23-10; Sprint 2 26-10 to 30-10.
- **What we are doing instead:** development starts on 10-10-2026 with a Sprint 0 (foundation and dry run, 10-10 to 16-10). Sprint 2 runs from 23-10 to 30-10.
- **Why:** the extra days give the developers more implementation time.
- **Impact:** none on the deliverable dates. The 1-minute video is still due 23-10, the 2-minute video and the freeze are still 30-10.
- **Status:** Applied

### D-03 - Sample projects in the test data
- **Logged:** 2026-10-11
- **Document:** STP, Test Environment / Test Data
- **Planned:** seed data with sample projects and tasks in each status.
- **What we are doing instead:** seed data contains test accounts and sample tasks only.
- **Why:** no requirement defines a Projects entity, so none is being built.
- **Impact:** none on any of the 34 requirements.
- **Status:** Proposed (to be confirmed by the team)

<!-- Copy the block above for each new deviation. -->

---

## 2. Decisions on items the SAD left open

These are not deviations, because the SAD did not fix them. They are recorded here so the choices and reasons are easy to explain at the demo.

| Open item | Decision | Status |
|---|---|---|
| Database | S-01 uses SQLite. PostgreSQL 16 is defined in Docker Compose; connecting Django to PostgreSQL is deferred to S-02. | Applied |
| Test email server | MailHog, as named in the STP | Applied |
| Background jobs (reminders, queued e-mail) | A scheduled Django management command; no Celery | Proposed |
| Attachment scanning | A scanner stub behind an interface (extension and size checks, EICAR test file); no real antivirus integration | Proposed |
| REST/JSON endpoints | Not built; server-rendered Django views only | Proposed |
| Who can recover a soft-deleted task | The task owner | Proposed |
| Who can assign tasks | The Project Manager role, to any user | Proposed |
| Who can change collaborator permissions | The task owner (per TM-F-030 and TM-F-032) | Proposed |
| Task status values | `todo`, `in_progress`, and `done`, as agreed by Dev A and Dev B and recorded in `docs/schema.md` | Applied |
| Password complexity policy (TM-F-001) | The SRS refers to a policy but does not define it; Dev A to define it, and the seed password must comply | Open |

---

## 3. Scope cut or deferred

None so far.

If velocity requires cutting scope, the agreed order is: TM-F-031, TM-F-034, TM-F-041, then TM-F-051 (all Low priority in the SRS). Log each cut here with the date, the reason and the requirement ID.
