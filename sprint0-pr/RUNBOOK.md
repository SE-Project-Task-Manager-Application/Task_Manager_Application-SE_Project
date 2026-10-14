# Apply and submit (run in the VS Code terminal, repo root)

1. Wait until PR #56 (S-01) and the S-02 (User model) PR are merged into `dev`.
2. `git checkout dev && git pull`
3. `git checkout -b feature/15-task-foundation-and-create-task`
4. For n in 1..4 (from the folder holding this runbook's `patches/`):
   `git apply --3way --index patches/000n-*.patch` then `git commit -F commit_messages/commit-n.txt`
   (If a conflict shows, fix the marked files, `git add` them, then commit.)
5. Adjust `tests/conftest.py::make_user` if S-02's User manager differs.
6. `pip install -r requirements.txt -r requirements-dev.txt`, `ruff check .`, `pytest`.
7. `git push -u origin feature/15-task-foundation-and-create-task`
8. Open the PR to `dev`, paste PR_DESCRIPTION.md, request review from the repo owner.
