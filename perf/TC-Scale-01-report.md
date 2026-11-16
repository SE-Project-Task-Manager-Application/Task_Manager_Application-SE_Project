# TC-Scale-01 report: concurrent users (TM-NF-003)

**Requirement:** Multiple concurrent users without noticeable slowdown. The Test Plan criterion uses 20 simultaneous users with the TM-NF-001 2-second threshold.
**Pass rule:** for each of the six checked actions, the CSV `95%` column is below 2000 ms and `Failure Count` is zero. Login and login-page requests are reported but not judged by this rule.
**Evidence status:** Reconciled from committed historical artifacts on 2026-11-16; not a new load test and not acceptance of the current dev revision.

## Provenance and unresolved metadata

- Raw evidence: `perf/results/tc_scale_01_stats.csv`, unchanged by this reconciliation.
- First artifact commit: `8826fa00aaed936bf585d85cd53a8b9d1f072b93` (author timestamp 2026-11-12). This is the commit that added the evidence, not proof of the app revision measured.
- Original tester label: "Tester B". The artifact commit is attributed to `sumedh007rao-prog`; no signed execution record binds that label to an operator.
- Execution date: 2026-11-12 is reported by the original scale report, not independently timestamped by the stats CSV.
- Tested app commit: Not recorded. The CSV contains no revision field, and the original report left the commit as a placeholder.
- Original PR: [#87](https://github.com/SE-Project-Task-Manager-Application/Task_Manager_Application-SE_Project/pull/87). PR prose is supporting context; where its numbers disagree, the committed CSV is used below.

## Environment and workload

These are the historical report/runner settings, not a recovered machine inventory. The CSV alone does not verify the user count, duration or environment.

| Item | Evidence / reported configuration |
|---|---|
| Machine (CPU / RAM) | Not recorded |
| OS version | Not recorded; original template named Windows but did not give a version |
| Python / Django / Locust | 3.13 / 6.1 / 2.47.0 reported in the original template/report; runtime versions not captured in CSV |
| Database | PostgreSQL 16 via Docker, as reported; server metadata not captured |
| App server | `python manage.py runserver --noreload`, development settings, DEBUG=True, as reported |
| Load | Locust `perf/locustfile.py`, 20 users, spawn rate 2/s, 2 minutes, 1-3 s waits, as reported |
| Accounts | Runner defaults to the seeded member and PM accounts; per-run overrides not captured |

Reported command (reproduction recipe, not a retained execution log):

```text
locust -f perf/locustfile.py --host http://127.0.0.1:8000 --headless -u 20 -r 2 -t 2m --csv perf/results/tc_scale_01 --html perf/results/tc_scale_01.html
```

## Results from the saved CSV

Median and 95% values are copied directly from their named CSV columns. Max values are rounded to the nearest whole millisecond; CSV percentiles are bucketed and need not equal the exact maximum.

| Action | Requests | Failures | Median (ms) | 95% (ms) | Max (ms) | Result |
|---|---|---|---|---|---|---|
| View task list | 488 | 0 | 110 | 290 | 533 | PASS |
| View filtered task list | 252 | 0 | 84 | 260 | 435 | PASS |
| Open new-task form | 108 | 0 | 80 | 160 | 297 | PASS |
| Create task | 128 | 0 | 74 | 180 | 222 | PASS |
| Open edit form | 242 | 0 | 91 | 190 | 485 | PASS |
| Save edit | 242 | 0 | 94 | 200 | 351 | PASS |

**Overall saved-run result: PASS.** Worst checked-action p95: 290 ms, below 2000 ms. All 1500 requests, including login and login-page requests, have zero recorded failures. Aggregate rate: 12.62 requests/s. This is a recomputed CSV verdict, not evidence of the original process exit code.

Login POST: 20 requests, median 350 ms. Login page GET: 20 requests, median 33 ms. Neither is included in the six-action threshold verdict.

## Comparison with the saved 5-user run

| Action | Median 5 users → 20 users (ms) | 95% 5 users → 20 users (ms) |
|---|---|---|
| View task list | 99 → 110 | 140 → 290 |
| View filtered task list | 77 → 84 | 110 → 260 |
| Open new-task form | 78 → 80 | 93 → 160 |
| Create task | 54 → 74 | 92 → 180 |
| Open edit form | 91 → 91 | 130 → 190 |
| Save edit | 77 → 94 | 130 → 200 |

Largest median increase: 20 ms (Create task). Largest p95 increase: 150 ms (View task list and View filtered task list). Both saved runs remain below the stated threshold. This numerical comparison is not a user-perception study or a controlled scalability benchmark: matching machine/configuration and tested app revisions cannot be independently confirmed from the artifacts.

## Reconciliation notes

The original comparison used Create task p95 110 ms and edit-form median 92 ms for the 5-user run. Its CSV has 92 ms and 91 ms respectively; the comparison above uses those CSV columns. PR #87 said machine/OS details had been filled, but its artifact commit and merged reports still contained placeholders. Those details remain unknown. The original claim that Locust exited with code 0 has no retained process log here, so the report states the recomputed CSV verdict instead.

## Limitations and follow-up

- Historical local development-server results, not production evidence or a test of the current dev head. No production-speed guarantee follows from them.
- Original scale report says Locust and the app shared one laptop. Machine specifications and OS version were not retained, so exact reproduction is not possible from these files alone.
- User counts and spawn/duration settings come from the reported commands. The runner uses separate sessions and creates a task per simulated user, but only two default account identities; this is not proof of 20 distinct accounts or a broad workload.
- The runner can skip editing if its task/form parsing fails. Saved rows show edit requests occurred, but aggregate statistics do not prove full business correctness, browser rendering time or every response's content.
- A repeat run should save the exact app SHA, execution timestamps, runtime/database versions, hardware/OS, effective command and users, exit log and CSVs. Report a rerun separately rather than replacing these historical artifacts.

## Bugs raised

No new application defect is established by these saved statistics. Historical report/CSV discrepancies are recorded above; this is not a claim that the application is defect-free.
