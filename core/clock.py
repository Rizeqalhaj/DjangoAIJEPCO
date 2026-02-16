"""Centralized time utility with override support for testing.

In normal operation, now() returns django.utils.timezone.now().
When a time override is set (via the debug API), now() returns
the overridden datetime instead — letting you "time travel" to
test plan verifications, spike detection, etc.

This module also monkey-patches django.utils.timezone.now so that
Django internals (auto_now_add, auto_now, etc.) also respect the
override. This ensures created_at fields use the simulated date.

The override is stored on disk (a temp file) so it is shared across
all gunicorn workers without requiring Redis.
"""

import os
import tempfile
from datetime import datetime, timezone as dt_tz

import django.utils.timezone as _tz

_OVERRIDE_FILE = os.path.join(tempfile.gettempdir(), "kahrabaai_time_override")

_original_now = _tz.now


def now():
    """Return the current datetime, or the override if set."""
    override = get_override()
    return override if override else _original_now()


def set_override(dt):
    """Set a datetime override. All calls to now() will return this value."""
    with open(_OVERRIDE_FILE, "w") as f:
        f.write(dt.isoformat())


def clear_override():
    """Clear the datetime override. now() returns real time again."""
    try:
        os.remove(_OVERRIDE_FILE)
    except FileNotFoundError:
        pass


def get_override():
    """Return the current override datetime, or None if not set."""
    try:
        with open(_OVERRIDE_FILE, "r") as f:
            iso = f.read().strip()
        if not iso:
            return None
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_tz.utc)
        return dt
    except (FileNotFoundError, ValueError):
        return None


# Monkey-patch django.utils.timezone.now so Django internals
# (auto_now_add, auto_now, etc.) also use the override.
_tz.now = now
