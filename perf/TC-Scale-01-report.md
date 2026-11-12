# TC-Scale-01 report: concurrent users (TM-NF-003)

**Requirement:** The system shall support multiple concurrent users without noticeable slowdown.
**Test Plan criterion:** 20 simultaneous users, with response time still within 2 seconds (TM-NF-001).
**Pass rule:** for every action, 95th-percentile response time under 2000 ms and no failed requests.
**Tester:** Tester B · **Date:** 2026-11-12 · **Commit:** `<git rev-parse --short HEAD>`

## Environment
| Item | Value |
|---|---|
| Machine | <CPU, RAM> |
| OS | Windows <version> |
| Python / Django / Locust | 3.13 / 6.1 / 2.47.0 |
| Database | PostgreSQL 16 (Docker, `docker compose up -d db`) |
| App server | `python manage.py runserver --noreload` (dev settings, DEBUG=True) |
| Load | Locust `perf/locustfile.py`, **20 users**, spawn rate 2/s, 2 minutes, 1–3 s wait between actions |

Command:

```
locust -f perf/locustfile.py --host http://127.0.0.1:8000 --headless -u 20 -r 2 -t 2m --csv perf/results/tc_scale_01 --html perf/results/tc_scale_01.html
```

## Results (20 users)
| Action | Requests | Failures | Median (ms) | 95% (ms) | Max (ms) | Result |
|---|---|---|---|---|---|---|
| View task list | 488 | 0 | 110 | 290 | 533 | PASS |
| View filtered task list | 252 | 0 | 84 | 260 | 435 | PASS |
| Open new-task form | 108 | 0 | 80 | 160 | 297 | PASS |
| Create task | 128 | 0 | 74 | 180 | 222 | PASS |
| Open edit form | 242 | 0 | 91 | 190 | 485 | PASS |
| Save edit | 242 | 0 | 94 | 200 | 351 | PASS |

Login (not judged): 20 requests, median 350 ms, max 568 ms.
Total: 1,500 requests, **0 failures**, about 12.6 requests per second.

**Overall:** PASS. The slowest 95th percentile is 290 ms (View task list), well under the 2000 ms limit. Locust exited with code 0.

Raw numbers: `perf/results/tc_scale_01_stats.csv`.

## Slowdown compared with normal use (TC-Perf-01, 5 users)
| Action | Median 5 users → 20 users (ms) | 95% 5 users → 20 users (ms) |
|---|---|---|
| View task list | 99 → 110 | 140 → 290 |
| View filtered task list | 77 → 84 | 110 → 260 |
| Open new-task form | 78 → 80 | 93 → 160 |
| Create task | 54 → 74 | 110 → 180 |
| Open edit form | 92 → 91 | 130 → 190 |
| Save edit | 77 → 94 | 130 → 200 |

With four times as many users, the typical (median) response time rose by at most 20 ms. The slowest 5% of requests rose from about 0.1 s to at most 0.3 s. Responses this short are not noticeable to a person, and every action stays far below the 2-second limit, so there is no noticeable slowdown.

## Limitations
- Measured on a development laptop with Django's development server and DEBUG=True, not a production server. A production server (gunicorn, DEBUG=False) is expected to be at least as fast.
- Locust and the app ran on the same machine, so they shared CPU.
- The simulated users log in with the two seeded accounts (member and PM). Each simulated user has its own session and edits only a task it created.

## Bugs raised
None.
