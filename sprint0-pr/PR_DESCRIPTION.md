## Linked story
Closes #3
Closes #4
Closes #5
Closes #15

## What changed
- **S-03 (#3):** responsive base template with skip link, landmarks and a role-aware main menu; reusable form component with an error summary; CSS with visible focus, 44px targets and checked AA contrast.
- **S-04 (#4):** `Task`, `TaskAssignment` and `Label` models with migrations, registered in the admin. Follows `docs/schema.md` (owner plus assignment records, soft delete, `version`).
- **S-05 (#5):** `AuditService.record(...)` writing append-only `AuditRecord` rows, and a `NotificationService` stub (`enqueue` / `send` / `deliver_pending`).
- **TM-F-010 (#15):** signed-in users create a task (title, description, due date, priority, labels) and see it in the task list. Only a Project Manager can assign; the assignee is notified after commit; every create/assign writes an audit record in the same transaction.

Commits are one per story so they can be reviewed separately.

## How to test
1. `pip install -r requirements.txt -r requirements-dev.txt`, then `pytest` (61 tests; no env variables needed) and `ruff check .`.
2. Manual (follow SETUP.md, `python manage.py migrate`, `runserver`): sign in as `member@example.com`, open `/tasks/new/`, create a task, see it at `/tasks/`. Sign in as `pm@example.com` and confirm the "Assign to" checkboxes appear and the assignee gets a mail in MailHog (http://localhost:8025) once mail is wired to it.
3. Layout: resize to ~360px wide; press Tab through the page (skip link first, focus always visible).
4. Test case: **TC-Task-01** (`tests/task/test_tc_task_01.py`).

## Test-case checklist
- [x] Test case(s) run: TC-Task-01
- [x] Acceptance criteria from the issue are met
- [x] No new Critical/High bugs introduced

## Author checklist
- [x] Branch name is feature/<issue-number>-short-name
- [x] PR targets `dev`
- [ ] GitHub Actions checks pass (confirm after pushing)
- [x] Any deviation from the SRS/SAD/STP is noted in DEVIATIONS.md (D-06, D-07)

## Notes for the reviewer
- Depends on S-01 (#56) and S-02 (custom `User` with `email`, `role`, `deleted_at`). Tests build users through `tests/conftest.py::make_user`; adjust there if the `User` manager differs.
- Assumptions: due date is optional and stored as date-time; assignment is Project Manager only (SAD 4.3), so Administrators cannot assign; the task list shows tasks the user owns or is assigned to.
- Not in scope: edit/delete/complete tasks (TM-F-011 to 013), login pages, sharing.
- `config/settings/test.py` is new so tests need no `DJANGO_SECRET_KEY`.
