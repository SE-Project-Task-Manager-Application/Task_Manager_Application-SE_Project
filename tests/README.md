# Tests

Run all tests from the repo root:

```
pip install -r requirements-dev.txt
pytest
```

## Layout

One folder per test-case group in the Test Plan (STP). Each test-case ID gets
its own file, so a failing test points straight at its TC ID.

| Folder | TC IDs |
|---|---|
| `tests/auth/` | TC-Auth-01 to TC-Auth-06 |
| `tests/task/` | TC-Task-01 to TC-Task-05 |
| `tests/collab/` | TC-Collab-01 to TC-Collab-05 |
| `tests/dash/` | TC-Dash-01, TC-Dash-02 |
| `tests/admin/` | TC-Admin-01 to TC-Admin-04 |
| `tests/sec/` | TC-Sec-01 to TC-Sec-05 |
| `tests/accounts/` | User model rules (no TC ID; the TC-Auth tests are added by the auth stories) |
| `tests/foundation/` | No TC ID: ORM, service and layout tests for the setup stories (S-03 to S-05) |

Other groups (Org, Perf, Ops, Retention, Scale, UX) get their own folder when
their first test is written.

## Naming

File: `test_tc_<group>_<number>.py`, for example `tests/auth/test_tc_auth_01.py`.
Test functions inside it start with `test_`.

Shared fixtures (for example `make_user`) live in `tests/conftest.py`. Tests use
`config.settings.test`, so no environment variables are needed.
