# Deviations from Submitted Documents

**Project:** Task Manager Application  
**Baseline documents:** SRS, SAD v1.1 (09-10-2026), STP v1.0 (28-09-2026), and the course Part-2 deliverables schedule  
**Owner:** Syed (Scrum Master)

The submitted documents are the baseline and are not edited after submission. Every place where what we build or do differs from them is recorded here, with the reason, so it can be explained at the final demo.

**When to add an entry:** any time the product, the schedule, the test approach or the architecture differs from the SRS, SAD or STP.  
**How:** add the next ID (D-06, D-07, ...), keep each field to a sentence or two, and link the issue or PR where useful.  
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
- **Why:** no requirement defines a Projects entity (also listed as a SAD open issue, see section 2), so none is being built.
- **Impact:** none on any of the 34 requirements.
- **Status:** Proposed (to be confirmed by the team)

### D-04 - Monitoring
- **Logged:** 2026-10-11
- **Document:** SAD, section 4.4 (Logging and monitoring) and section 3.6
- **Planned:** monitor response time, error rate, authentication failures and lockouts, notification failures, job failures, and database/storage health.
- **What we are doing instead:** application logging plus the audit and activity records. No separate monitoring tooling is set up.
- **Why:** there is no production deployment in this course build, and the time goes to the 34 requirements.
- **Impact:** response-time and concurrency targets (TM-NF-001, TM-NF-003) are verified by test runs rather than live monitoring.
- **Status:** Proposed (to be confirmed by the team)

### D-05 - Attachment malware scanning
- **Logged:** 2026-10-11
- **Document:** SAD, sections 3.9 and 4.1 (StorageModule); SRS TM-F-022 ("scanned before storage")
- **Planned:** attachments are validated and scanned for malware before storage.
- **What we are doing instead:** a scanner interface with a stub behind it: file-type and size checks plus detection of the EICAR test file. No full antivirus engine is integrated.
- **Why:** the SAD leaves the scanning mechanism open, and a real scanner needs infrastructure outside this course build.
- **Impact:** weaker protection than a real scanner. The interface lets a real scanner replace the stub later.
- **Status:** Proposed (to be confirmed by the team; remove this entry if a real scanner is used)

### D-06 - Task assignees stored as assignment records
- **Logged:** 2026-10-15
- **Document:** SAD, section 4.1 (TaskModule data: "Task (assignee, deleted_at)") and the data-model line in S-04
- **Planned:** a single `assignee` on the Task.
- **What we are doing instead:** a Task has one `owner` and any number of assignees, stored as TaskAssignment rows (task, user, assigned_by, assigned_at), as agreed in `docs/schema.md`.
- **Why:** the team agreed that a task may have several assignees and that who assigned, and when, must be recorded.
- **Impact:** assignment and reassignment (TC-Task-01/02) work on assignment records. Anything that read "the assignee" reads the task's assignment list instead.
- **Status:** Applied

### D-07 - Notification stub is not stored in the database
- **Logged:** 2026-10-15
- **Document:** SAD, section 4.1 (NotifModule data: "Notification / delivery status") and section 4.3
- **Planned:** notifications are delivered asynchronously and their delivery status is persisted.
- **What we are doing instead:** S-05 provides NotificationService as a thin stub. When a task is assigned, TaskService sends the e-mail directly after the database transaction commits (MailHog in development); `send()` never raises and the mail connection times out after `EMAIL_TIMEOUT` (5 seconds). `enqueue()` and `deliver_pending()` exist for a later background job but nothing calls them yet. No Notification record, retry, or due-date reminder exists yet; those come with the notification stories.
- **Why:** Sprint 0 only needs the interface to exist and TC-Task-01's "assignee is notified" to be checkable.
- **Impact:** a request that assigns a task waits for the mail server for up to 5 seconds if it is unreachable, and a failed mail is logged but not retried, so the STP 5.2 retry test waits for the later story. TC-Task-01 is verified in MailHog (http://localhost:8025) or `django.core.mail.outbox`.
- **Status:** Proposed (to be confirmed by the team)

<!-- Copy a block above for each new deviation. -->

---

## 2. Decisions on the SAD open issues (SAD section 4.6)

These are not deviations by themselves, because the SAD left them open. Each row follows the SAD's own list so every open issue has a recorded answer.

| SAD open issue | Decision | Status |
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
| Supported browser matrix | To be defined before UI testing | Open |
| Monitoring, backup and at-rest encryption | Not implemented in the course build; deployment-level controls (see D-04) | Proposed |
| Rate limiting for login and file upload | Not implemented in application code (a reverse-proxy concern). Account lockout (TM-F-003) and the 10 MB limit (TM-F-022) still apply | Proposed |
| Whether "projects" need their own entity | No Projects entity is built (see D-03) | Proposed |

---

## 3. Other decisions and gaps not covered by the documents

| Item | Decision | Status |
|---|---|---|
| How TM-SR-001 (TLS 1.2+) is verified | HTTPS is required in production and HTTP is allowed locally; decide where TLS is demonstrated | Open |

---

## 4. Scope cut or deferred

None so far.

If velocity requires cutting scope, the agreed order is: TM-F-031, TM-F-034, TM-F-041, then TM-F-051 (all Low priority in the SRS). Log each cut here with the date, the reason and the requirement ID.