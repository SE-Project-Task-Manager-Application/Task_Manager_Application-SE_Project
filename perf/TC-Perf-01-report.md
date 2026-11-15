# TC-Perf-01 report: response time (TM-NF-001)

**Requirement:** Common actions (create, edit, view tasks) respond within 2 seconds under normal use.
**Pass rule:** for every action, 95th-percentile response time under 2000 ms and no failed requests.
**Tester:** Tester B · **Date:** YYYY-MM-DD · **Commit:** `<git rev-parse --short HEAD>`

## Environment
| Item | Value |
|---|---|
| Machine | <CPU, RAM> |
| OS | Windows <version> |
| Python / Django | 3.13 / 6.1 |
| Database | PostgreSQL 16 (Docker, `docker compose up -d db`) |
| App server | `python manage.py runserver --noreload` (dev settings, DEBUG=True) |
| Load | Locust, 5 users, spawn rate 1/s, 2 minutes, 1–3 s wait between actions |

## Results (Locust)
| Action | Requests | Failures | Median (ms) | 95% (ms) | Max (ms) | Result |
|---|---|---|---|---|---|---|
| View task list | | | | | | |
| View filtered task list | | | | | | |
| Open new-task form | | | | | | |
| Create task | | | | | | |
| Open edit form | | | | | | |
| Save edit | | | | | | |

**Overall:** PASS / FAIL

Raw numbers: `perf/results/tc_perf_01_stats.csv`.

## Automated guard (CI)
`pytest tests/perf/test_tc_perf_01.py -v` → <N> passed (each action under 2 s over 5 rounds with 300 existing tasks).

## Limitations
- Measured on a development laptop with Django's development server and DEBUG=True, not a production server.
- "Normal use" is taken as 5 simultaneous users; the 20-user run is TC-Scale-01 (TM-NF-003).

## Bugs raised
None / <link to issue>
