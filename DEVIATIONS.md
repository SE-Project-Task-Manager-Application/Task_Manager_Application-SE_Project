# Deviations from Submitted Documents

**Project:** Task Manager Application  
**Baseline documents:** SRS, SAD v1.1 (09-10-2026), STP v1.0 (28-09-2026), and the course Part-2 deliverables schedule  
**Owner:** Syed (Scrum Master)

The submitted documents are the baseline and are not edited after submission. Every place where what we build or do differs from them is recorded here, with the reason, so it can be explained at the final demo.

**When to add an entry:** any time the product, the schedule, the test approach or the architecture differs from the SRS, SAD or STP.  
**How:** add the next ID (D-13, D-14, ...), keep each field to a sentence or two, and link the issue or PR where useful.  
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
- **What we are doing instead:** seed data contains test accounts, sample tasks and sample labels only.
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

### D-07 - Most notification types still use direct e-mail delivery
- **Logged:** 2026-10-15
- **Document:** SAD, section 4.1 (NotifModule data: "Notification / delivery status") and section 4.3
- **Planned:** notifications are delivered asynchronously and their delivery status is persisted.
- **What we are doing instead:** Issue #24 adds persisted, retriable notifications for shared-task updates. A recurring `deliver_notifications` command attempts pending messages every five minutes. Task assignment and account emails still use direct best-effort delivery; due-date reminders remain a separate story.
- **Why:** Sprint 0 only needs the interface to exist and TC-Task-01's "assignee is notified" to be checkable.
- **Impact:** requests for assignment and account emails can wait for the mail server for up to 5 seconds if it is unreachable, and failed sends for those types are not retried. TC-Task-01 is verified in MailHog (http://localhost:8025) or `django.core.mail.outbox`.
- **Status:** Partially superseded by Issue #24

### D-08 - Registration confirmation email is sent synchronously
- **Logged:** 2026-10-29
- **Document:** Issue #10 / ADR-003
- **Planned:** Registration confirmation e-mail is queued so the request does not wait for the mail server.
- **What we are doing instead:** Registration sends the confirmation e-mail directly after creating the account. If the mail server is unavailable, the account remains created, but the request may wait up to `EMAIL_TIMEOUT` (5 seconds). The existing in-memory queue has no background delivery runner, so using `enqueue()` alone would not deliver the e-mail.
- **Why:** Keep the confirmation e-mail deliverable while a background delivery mechanism is not available.
- **Impact:** Registration is best-effort: a mail failure is logged, the account stays active, and delivery is not retried.
- **Status:** Proposed (to be confirmed by the team)

### D-09 - Account e-mails sent directly; profile pictures on local disk
- **Logged:** 2026-11-06
- **Document:** SAD, ADR-003 (isolated, asynchronous notification delivery) and section 4.1 (StorageModule); SRS TM-F-004 and TM-F-005
- **Planned:** account e-mails are queued and delivered by a background job; stored files go through validation and scanning.
- **What we are doing instead:** password-reset and e-mail-change messages are sent directly through `NotificationService.send()`, which never raises and times out after 5 seconds. Profile pictures are stored on local disk (`MEDIA_ROOT`) and served through a login-required view. An upload is checked by extension, the 10 MB limit and the file's first bytes; it is not decoded or virus-scanned.
- **Why:** there is no background delivery runner (see D-07 and D-08), and the file-storage backend is an open SAD issue.
- **Impact:** a slow mail server can delay these requests by up to 5 seconds, and a failed mail is not retried (for an e-mail change the user is told when sending failed). File checks are weaker than a real scanner (see D-05).
- **Status:** Proposed (to be confirmed by the team)

### D-10 - No screen to change a user's role
- **Logged:** 2026-11-06
- **Document:** SRS 2.3 (the Administrator manages users and roles) and TM-F-050; SAD, section 4.1 (AdminModule)
- **Planned:** the Administrator can manage users and their roles.
- **What we are doing instead:** the user-management page lets the Administrator view, disable, enable and soft-delete accounts, as TM-F-050 lists. No screen changes a user's role, and the Django admin site does not register the User model at the time of writing. New accounts get the Team Member role; other roles come from the seed data or `createsuperuser`. Deleted accounts are soft-deleted and their e-mail address stays reserved.
- **Why:** TM-F-050 only requires view, disable and delete, and the time went to the 34 requirements.
- **Impact:** Project Manager and Administrator accounts cannot be created from the UI. The demo uses the seeded accounts.
- **Status:** Proposed (to be confirmed by the team)

### D-11 - Audit log does not record every login
- **Logged:** 2026-11-06
- **Document:** SAD, section 4.2 (Sequence 1 records login success, login failure and account lock); SRS TM-F-052
- **Planned:** security events, including successful and failed logins, appear in the audit log.
- **What we are doing instead:** audit records exist for account lockouts, user disable/enable/delete, and task events (created, updated, deleted, restored, assignment changes). Successful logins, failed attempts below the lockout threshold, and logouts are not recorded.
- **Why:** TM-F-003 only requires the lockout to be logged, and the audit-log story only requires actor, action, timestamp, search and immutability.
- **Impact:** the audit log is thinner than Sequence 1 shows. TM-F-052 is still met (searchable, with actor, action and timestamp, and immutable).
- **Status:** Proposed (to be confirmed by the team)

### D-12 - Developers and testers swapped for some stories
- **Logged:** 2026-11-06
- **Document:** STP, section 9 (Roles and Responsibilities)
- **Planned:** developers implement and fix defects; test engineers design and run the test cases.
- **What we are doing instead:** for several stories the test engineers wrote the code and the developers tested it. The person who wrote a story never tests it.
- **Why:** the work was divided this way so that every story is verified independently.
- **Impact:** none on the requirements. Each story's issue or pull request records who built it and who tested it.
- **Status:** Applied

### D-13 - Category restore action
- **Logged:** 2026-11-11
- **Document:** SRS 4.6, TM-F-051 (Manage categories)
- **Planned:** the Administrator can create, rename or archive global categories.
- **What we are doing instead:** the same, plus a Restore action that makes an archived category active again. Restoring writes a `label.restored` audit record. No screen deletes a category.
- **Why:** archiving with no way back would be a dead end for administrators.
- **Impact:** none on the acceptance criteria (archived categories still do not appear when creating a task). One extra action and one extra audit action name, both covered by TC-Admin-02 (PR #77).
- **Status:** Applied

<!-- Copy a block above for each new deviation. -->

---

## 2. Decisions on the SAD open issues (SAD section 4.6)

These are not deviations by themselves, because the SAD left them open. Each row follows the SAD's own list so every open issue has a recorded answer.

| SAD open issue | Decision | Status |
|---|---|---|
| Database | PostgreSQL 16, run in Docker Compose for development; the CI test job uses a `postgres:16` service. Django connects through the `DB_*` variables. | Applied |
| Test email server | MailHog, as named in the STP | Applied |
| Background jobs (reminders, queued e-mail) | A scheduled Django management command; no Celery | Proposed |
| Attachment scanning | A scanner stub behind an interface (extension and size checks, EICAR test file); no real antivirus integration (see D-05) | Proposed |
| REST/JSON endpoints | Not built; server-rendered Django views only | Proposed |
| Who can recover a soft-deleted task | The task owner | Applied |
| Who can assign tasks | The Project Manager role, to any active user (enforced in `TaskService`) | Applied |
| Who can change collaborator permissions | The task owner (per TM-F-030 and TM-F-032) | Proposed |
| Task status values | `todo`, `in_progress`, and `done`, as agreed by Dev A and Dev B and recorded in `docs/schema.md` | Applied |
| Password complexity policy (TM-F-001) | Django's four default validators apply to registration, reset and change: minimum length 8, not a common password, not entirely numeric, not too similar to the user's details. The seed password is set directly and bypasses them. | Proposed |
| Supported browser matrix | To be defined before UI testing | Open |
| Monitoring, backup and at-rest encryption | Not implemented in the course build; deployment-level controls (see D-04) | Proposed |
| Rate limiting for login and file upload | Not implemented in application code (a reverse-proxy concern). Account lockout (TM-F-003) and the 10 MB limit (TM-F-022) still apply | Proposed |
| Whether "projects" need their own entity | No Projects entity is built (see D-03) | Proposed |

---

## 3. Other decisions and gaps not covered by the documents

| Item | Decision | Status |
|---|---|---|
| How TM-SR-001 (TLS 1.2+) is verified | HTTPS is required in production and HTTP is allowed locally; decide where TLS is demonstrated | Open |
| Final schedule | Pull requests were still being merged after the 30-10-2026 freeze date (for example migrations generated on 2026-11-02 and 2026-11-05). Record the agreed final dates in D-01 and D-02, or log the overrun as a deviation | Open |

---

## 4. Scope cut or deferred

None so far.

If velocity requires cutting scope, the agreed order is: TM-F-031, TM-F-034, TM-F-041, then TM-F-051 (all Low priority in the SRS). Log each cut here with the date, the reason and the requirement ID.
