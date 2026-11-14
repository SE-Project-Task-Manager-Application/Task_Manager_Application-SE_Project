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
|  | `title` | Required, up to 200 characters. |
|  | `description` | Optional free text. |
|  | `priority` | One of `low`, `medium`, or `high`. New tasks start as `medium`. |
|  | `due_date` | Optional date and time (UTC). |
|  | `labels` | Zero or more labels (many-to-many). |
|  | `version` | Whole number, starts at 1. Used to reject stale edits (SAD 4.4). |
|  | `status` | One of `todo`, `in_progress`, or `done`. New tasks start as `todo`. |
|  | `deleted_at` | Empty unless the task has been soft-deleted. |
|  | `created_at` / `updated_at` | Creation time and most recent update time. |
| **Comment** | `task` | Reference to the task commented on (TM-F-033). |
|  | `author` | User who wrote the comment. Anyone who can view the task can comment. |
|  | `body` | Required text, up to 2000 characters, stored without leading or trailing spaces. |
|  | `created_at` | When the comment was posted (UTC). Each comment also writes a `task.commented` audit record with the comment's id, which the task activity history (TM-F-034) reads. |
| **Task assignment** | `task` | Reference to the task. |
|  | `user` | Reference to an assigned user. A task may have multiple assignment records, so it can have multiple assignees. |
|  | `assigned_by` | User who made the assignment. |
|  | `assigned_at` | When the assignment was made. |
| **Task share** | `task` | Reference to the task shared by its owner. |
|  | `user` | User who receives access to the task. |
|  | `permission` | `viewer` or `editor`; one share per task and user. |
|  | `shared_by` / `shared_at` | Owner who granted the share and when it was first granted. Later permission changes are timestamped in the audit record; soft-deleting the owner preserves the share and its owner reference. |
| **Audit record** | `actor` | User who performed the action; may be empty for a system action. |
|  | `action` | Stable action name, such as `task.created`, `task.status_changed`, or `task.assignee_added`. |
|  | `target_type` / `target_id` | The kind of record affected and its identifier, such as `task` and `42`. |
|  | `created_at` | When the action happened. |
|  | `details` | Optional information about the change, such as the old and new status or the assigned user. Never include passwords, tokens, or other secrets. |
| **System config** | `password_min_length` | Minimum length required for newly chosen passwords. |
|  | `session_timeout_seconds` | Inactivity timeout applied to authenticated sessions, capped at 86,400 seconds (24 hours). |
|  | `notifications_enabled` / `notification_sender` | Database-controlled notification defaults. |
| **Task attachment** | `task` / `uploaded_by` | The task and authenticated user associated with the upload. |
|  | `file` / `original_name` | Stored file and its original client filename. Files are limited to 10 MB, checked against an allowlist, and passed through the EICAR-detecting scanner stub before storage. |
|  | `size` / `content_type` / `uploaded_at` | Metadata retained for authorized retrieval and auditing. |
| **Label** | `name` | Required; unique ignoring upper/lower case. |
|  | `is_archived` | Archived labels are not offered when creating a task (TM-F-051). |

### Task access

Owners and assignees can view and edit a task. A Viewer share grants view access only; an Editor
share grants view and edit access. Only the owner can create or change shares. Soft-deleting an
account disables that account but preserves its task shares and audit references.
