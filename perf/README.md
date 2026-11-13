# Performance tests (TM-NF-001, TM-NF-003)

| Test case | Requirement | What runs it |
|---|---|---|
| TC-Perf-01 | TM-NF-001: create, edit and view tasks respond within 2 s under normal use | `tests/perf/test_tc_perf_01.py` in CI on every PR, plus the Locust run below |
| TC-Scale-01 | TM-NF-003: multiple concurrent users without noticeable slowdown | The same Locust run with 20 users (Test Plan criterion) |

The pytest test is a fast guard: it times each action through Django with 300 existing tasks and fails if any of 5 rounds takes 2 s or more. The Locust run is the formal measurement over HTTP with several simulated users.

## Running TC-Perf-01 with Locust (Windows PowerShell)

Locust is kept out of `requirements-dev.txt` so CI stays fast. Install it once:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r perf/requirements.txt
```

Terminal 1, start the app with the seed accounts:

```powershell
docker compose up -d db
python manage.py migrate
python manage.py seed_test_data
python manage.py runserver --noreload
```

Terminal 2, run 5 users ("normal use") for 2 minutes:

```powershell
.\venv\Scripts\Activate.ps1
locust -f perf/locustfile.py --host http://127.0.0.1:8000 --headless -u 5 -r 1 -t 2m --csv perf/results/tc_perf_01 --html perf/results/tc_perf_01.html
```

At the end Locust prints a `TM-NF-001 check` table with PASS or FAIL for each action and an overall verdict, and exits with code 1 on FAIL. Record the numbers in `perf/TC-Perf-01-report.md`. Only `perf/results/*_stats.csv` is committed; the HTML report is for viewing locally.

For TC-Scale-01, run the same command with `-u 20 -r 2` and `--csv perf/results/tc_scale_01`.

Options: `PERF_USERS` (comma-separated emails, default the seeded member and PM) and `PERF_PASSWORD` (default `SEPROG123`) set which accounts log in.

## Notes
- `runserver` is Django's development server with `DEBUG=True`, so production (gunicorn, `DEBUG=False`) should be at least as fast. This is recorded as a limitation in the report.
- Each simulated user edits only a task it created, so concurrent edits never hit the stale-version check (TM-F-011).
