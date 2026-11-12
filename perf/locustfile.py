"""TC-Perf-01 (TM-NF-001) and TC-Scale-01 (TM-NF-003): response-time load test.

Each simulated user logs in once, creates its own task, then repeatedly views the
task list (plain and filtered), creates tasks, and opens and saves an edit of its
own task. At the end the run prints a PASS/FAIL table: every action must have a
95th-percentile response time under 2 seconds and no failed requests.

See perf/README.md for how to run it.
"""

import itertools
import os
import re
import uuid

from locust import HttpUser, between, events, task

LIMIT_MS = 2000  # TM-NF-001: within 2 seconds
PERCENTILE = 0.95
PASSWORD = os.environ.get("PERF_PASSWORD", "SEPROG123")  # seed_test_data password
ACCOUNTS = os.environ.get("PERF_USERS", "member@example.com,pm@example.com").split(",")
_next_account = itertools.cycle(ACCOUNTS)

# The actions TM-NF-001 names (create, edit, view tasks). Login is reported but not judged.
CHECKED = [
    "View task list",
    "View filtered task list",
    "Open new-task form",
    "Create task",
    "Open edit form",
    "Save edit",
]

EDIT_LINK = re.compile(r'href="/tasks/(\d+)/edit/"')
VERSION = re.compile(r'name="expected_version"[^>]*value="(\d+)"')


class TaskManagerUser(HttpUser):
    # "Normal use": a person pauses between clicks.
    wait_time = between(1, 3)

    def on_start(self):
        self.email = next(_next_account).strip()
        self.client.get("/accounts/login/", name="Login page")
        response = self.client.post(
            "/accounts/login/",
            {
                "username": self.email,
                "password": PASSWORD,
                "csrfmiddlewaretoken": self.client.cookies.get("csrftoken", ""),
            },
            name="Login",
            allow_redirects=False,
        )
        if response.status_code != 302:
            raise RuntimeError(
                f"Login failed for {self.email} (HTTP {response.status_code}). "
                "Run `python manage.py seed_test_data` first."
            )
        self.own_task_id = self._create_own_task()

    def _csrf(self):
        return self.client.cookies.get("csrftoken", "")

    def _create_own_task(self):
        title = f"Perf {uuid.uuid4().hex[:10]}"
        self.client.post(
            "/tasks/new/",
            {"title": title, "priority": "medium", "csrfmiddlewaretoken": self._csrf()},
            name="Create task",
            allow_redirects=False,
        )
        page = self.client.get("/tasks/", params={"q": title}, name="View filtered task list")
        match = EDIT_LINK.search(page.text)
        return int(match.group(1)) if match else None

    @task(4)
    def view_task_list(self):
        self.client.get("/tasks/", name="View task list")

    @task(2)
    def view_filtered_task_list(self):
        self.client.get(
            "/tasks/",
            params={"q": "Perf", "priority": "medium", "sort": "due_date", "direction": "asc"},
            name="View filtered task list",
        )

    @task(1)
    def create_task(self):
        self.client.get("/tasks/new/", name="Open new-task form")
        with self.client.post(
            "/tasks/new/",
            {
                "title": f"Perf {uuid.uuid4().hex[:10]}",
                "priority": "low",
                "csrfmiddlewaretoken": self._csrf(),
            },
            name="Create task",
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code != 302:
                response.failure(f"Expected redirect, got HTTP {response.status_code}")

    @task(2)
    def edit_task(self):
        if not self.own_task_id:
            return
        url = f"/tasks/{self.own_task_id}/edit/"
        page = self.client.get(url, name="Open edit form")
        match = VERSION.search(page.text)
        if not match:
            return
        with self.client.post(
            url,
            {
                "title": f"Perf edited {uuid.uuid4().hex[:6]}",
                "description": "Edited by the TC-Perf-01 load test.",
                "priority": "high",
                "status": "in_progress",
                "expected_version": match.group(1),
                "csrfmiddlewaretoken": self._csrf(),
            },
            name="Save edit",
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code != 302:
                response.failure(f"Expected redirect, got HTTP {response.status_code}")


@events.quitting.add_listener
def judge_results(environment, **_kwargs):
    """Print the TM-NF-001 verdict and make the run fail if any action is too slow."""
    stats = environment.stats
    passed = True
    lines = [
        "",
        f"TM-NF-001 check: {int(PERCENTILE * 100)}th percentile must be under {LIMIT_MS} ms",
        f"{'Action':<26}{'Requests':>9}{'Failures':>9}{'Median':>9}{'95%':>9}{'Max':>9}  Result",
    ]
    for name in CHECKED:
        entry = next((e for e in stats.entries.values() if e.name == name), None)
        if entry is None or entry.num_requests == 0:
            lines.append(f"{name:<26}{'-':>9}{'-':>9}{'-':>9}{'-':>9}{'-':>9}  NOT RUN")
            passed = False
            continue
        p95 = entry.get_response_time_percentile(PERCENTILE)
        ok = p95 < LIMIT_MS and entry.num_failures == 0
        passed &= ok
        lines.append(
            f"{name:<26}{entry.num_requests:>9}{entry.num_failures:>9}"
            f"{entry.median_response_time:>9.0f}{p95:>9.0f}{entry.max_response_time:>9.0f}"
            f"  {'PASS' if ok else 'FAIL'}"
        )
    lines.append(f"Overall: {'PASS' if passed else 'FAIL'}")
    print("\n".join(lines))
    if not passed:
        environment.process_exit_code = 1
