"""AuditService (S-05): the single place that writes audit/activity records.

SAD 4.3: AuditService.record(actor, action, target, timestamp) creates an immutable
record; timestamps are stored in UTC. SAD 4.4: callers write the audit record inside
the same database transaction as the change it describes.
"""

import re
from datetime import UTC, datetime

from .models import AuditRecord

# Stable action names look like "task.created" or "task.status_changed".
ACTION_PATTERN = re.compile(r"^[a-z][a-z_]*(\.[a-z][a-z_]*)+$")

# Detail keys containing any of these are never stored (docs/schema.md: no secrets).
SENSITIVE_KEY_PARTS = ("password", "token", "secret", "authorization", "cookie", "session")
REDACTED = "[redacted]"


def _scrub(value):
    """Return a copy of `value` with the values of sensitive-looking keys replaced."""
    if isinstance(value, dict):
        return {
            key: REDACTED
            if any(part in str(key).lower() for part in SENSITIVE_KEY_PARTS)
            else _scrub(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_scrub(item) for item in value]
    return value


def _target_parts(target):
    """Accept a model instance or a (type, id) pair; return (target_type, target_id)."""
    if hasattr(target, "pk") and hasattr(target, "_meta"):
        if target.pk is None:
            raise ValueError("Audit target must be saved before it is recorded.")
        return target._meta.model_name, str(target.pk)
    try:
        target_type, target_id = target
    except (TypeError, ValueError):
        raise ValueError("Audit target must be a model instance or a (type, id) pair.") from None
    return str(target_type), str(target_id)


class AuditService:
    @staticmethod
    def record(actor, action, target, timestamp=None, details=None):
        """Append one audit record and return it.

        actor      -- the acting user, or None for a system action.
        action     -- stable dotted name, e.g. "task.created".
        target     -- the affected model instance, or a (type, id) pair.
        timestamp  -- timezone-aware datetime (stored in UTC); defaults to now.
        details    -- optional dict; values under password/token/secret-like keys are redacted.
        """
        if not ACTION_PATTERN.match(action or ""):
            raise ValueError(f"Invalid audit action name: {action!r}")
        if actor is not None and not getattr(actor, "pk", None):
            raise ValueError("Audit actor must be a saved user or None.")
        if timestamp is None:
            timestamp = datetime.now(UTC)
        elif timestamp.tzinfo is None:
            raise ValueError("Audit timestamp must be timezone-aware.")
        target_type, target_id = _target_parts(target)
        return AuditRecord.objects.create(
            actor=actor,
            action=action,
            target_type=target_type,
            target_id=target_id,
            created_at=timestamp.astimezone(UTC),
            details=_scrub(details or {}),
        )
