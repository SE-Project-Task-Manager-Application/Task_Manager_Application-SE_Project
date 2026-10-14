| Record | Field | Proposed definition |
|---|---|---|
| **User** | `id` | Unique user identifier. |
|  | `email` | Required and unique; used to log in, as specified in the current requirements. |
|  | `password` | Django-managed password hash. Never store plain-text passwords. |
|  | `role` | One of `member`, `project_manager`, or `admin`. New signups get `member`; an authorized app admin changes roles. |
|  | `is_active` | Whether the account can log in. Set to false when the account is disabled or soft-deleted. |
|  | `deleted_at` | Empty unless the account has been soft-deleted. Keep the user record so existing tasks and audit history retain their references. |
| **Task** | `id` | Unique task identifier. |
|  | `owner` | Required reference to one user: the person who created the task. Only an authorized app admin can change the owner in the first version. |
|  | `status` | One of `todo`, `in_progress`, or `done`. New tasks start as `todo`. |
|  | `deleted_at` | Empty unless the task has been soft-deleted. |
|  | `created_at` / `updated_at` | Creation time and most recent update time. |
| **Task assignment** | `task` | Reference to the task. |
|  | `user` | Reference to an assigned user. A task may have multiple assignment records, so it can have multiple assignees. |
|  | `assigned_by` | User who made the assignment. |
|  | `assigned_at` | When the assignment was made. |
| **Audit record** | `actor` | User who performed the action; may be empty for a system action. |
|  | `action` | Stable action name, such as `task.created`, `task.status_changed`, or `task.assignee_added`. |
|  | `target_type` / `target_id` | The kind of record affected and its identifier, such as `task` and `42`. |
|  | `created_at` | When the action happened. |
|  | `details` | Optional information about the change, such as the old and new status or the assigned user. Never include passwords, tokens, or other secrets. |