# TC-Perf-01 report: response time (TM-NF-001)

**Requirement:** Common actions (create, edit, view tasks) respond within 2 seconds under normal use.
**Pass rule:** for each of the six checked actions, the CSV `95%` column is below 2000 ms and `Failure Count` is zero. Login and login-page requests are reported but not judged by this rule.
**Evidence status:** Reconciled from committed historical artifacts on 2026-11-16; not a new load test and not acceptance of the current dev revision.

## Provenance and unresolved metadata

- Raw evidence: `perf/results/tc_perf_01_stats.csv`, unchanged by this reconciliation.
- First artifact commit: `2b2e01d0e30ed1c3b5c090b5b0ddfd4b224f4803` (author timestamp 2026-11-12). This is the commit that added the evidence, not proof of the app revision measured.
- Original tester label: "Tester B". The artifact commit is attributed to `sumedh007rao-prog`; no signed execution record binds that label to an operator.
- Execution date: Not recorded in the CSV or the original report; the artifact author date is not an execution timestamp.
- Tested app commit: Not recorded. The CSV contains no revision field, and the original report left the commit as a placeholder.
- Original PR: [#86](https://github.com/SE-Project-Task-Manager-Application/Task_Manager_Application-SE_Project/pull/86). PR prose is supporting context; where its numbers disagree, the committed CSV is used below.

## Environment and workload

These are the historical report/runner settings, not a recovered machine inventory. The CSV alone does not verify the user count, duration or environment.

| Item | Evidence / reported configuration |
|---|---|
| Machine (CPU / RAM) | Not recorded |
| OS version | Not recorded; original template named Windows but did not give a version |
| Python / Django | 3.13 / 6.1 reported in the original template/report; runtime versions not captured in CSV |
| Database | PostgreSQL 16 via Docker, as reported; server metadata not captured |
| App server | `python manage.py runserver --noreload`, development settings, DEBUG=True, as reported |
| Load | Locust `perf/locustfile.py`, 5 users, spawn rate 1/s, 2 minutes, 1-3 s waits, as reported |
| Accounts | Runner defaults to the seeded member and PM accounts; per-run overrides not captured |

Reported command (reproduction recipe, not a retained execution log):

```text
locust -f perf/locustfile.py --host http://127.0.0.1:8000 --headless -u 5 -r 1 -t 2m --csv perf/results/tc_perf_01 --html perf/results/tc_perf_01.html
```

## Results from the saved CSV

Median and 95% values are copied directly from their named CSV columns. Max values are rounded to the nearest whole millisecond; CSV percentiles are bucketed and need not equal the exact maximum.

| Action | Requests | Failures | Median (ms) | 95% (ms) | Max (ms) | Result |
|---|---|---|---|---|---|---|
| View task list | 115 | 0 | 99 | 140 | 150 | PASS |
| View filtered task list | 65 | 0 | 77 | 110 | 150 | PASS |
| Open new-task form | 27 | 0 | 78 | 93 | 110 | PASS |
| Create task | 32 | 0 | 54 | 92 | 108 | PASS |
| Open edit form | 73 | 0 | 91 | 130 | 136 | PASS |
| Save edit | 73 | 0 | 77 | 130 | 145 | PASS |

**Overall saved-run result: PASS.** Worst checked-action p95: 140 ms, below 2000 ms. All 395 requests, including login and login-page requests, have zero recorded failures. Aggregate rate: 3.40 requests/s. This is a recomputed CSV verdict, not evidence of the original process exit code.

Login POST: 5 requests, median 170 ms. Login page GET: 5 requests, median 7 ms. Neither is included in the six-action threshold verdict.

## Automated guard (separate evidence)

`tests/perf/test_tc_perf_01.py` defines five test functions. It times list, filtered list, create, edit-form and save-edit actions through Django's test client for five rounds, with 300 owner tasks plus 50 assigned PM tasks. It is not an HTTP load test and does not time the new-task form. Run `DJANGO_SETTINGS_MODULE=config.settings.test pytest tests/perf/test_tc_perf_01.py -v` for a current result. No historical pass count or current load-test result is inferred from the saved CSV.

## Reconciliation notes

PR #86 reports Create task p95 110 ms / max 270 ms and edit-form median 92 ms. The committed CSV instead records p95 92 ms / exact max 107.6203000266105 ms for Create task and edit-form median 91 ms. This report uses the CSV without rewriting the historical PR or raw data. The reason for those differences is not recorded.

## Limitations and follow-up

- Historical local development-server results, not production evidence or a test of the current dev head. No production-speed guarantee follows from them.
- Original scale report says Locust and the app shared one laptop. Machine specifications and OS version were not retained, so exact reproduction is not possible from these files alone.
- User counts and spawn/duration settings come from the reported commands. The runner uses separate sessions and creates a task per simulated user, but only two default account identities; this is not proof of 20 distinct accounts or a broad workload.
- The runner can skip editing if its task/form parsing fails. Saved rows show edit requests occurred, but aggregate statistics do not prove full business correctness, browser rendering time or every response's content.
- A repeat run should save the exact app SHA, execution timestamps, runtime/database versions, hardware/OS, effective command and users, exit log and CSVs. Report a rerun separately rather than replacing these historical artifacts.

## Bugs raised

No new application defect is established by these saved statistics. Historical report/CSV discrepancies are recorded above; this is not a claim that the application is defect-free.
