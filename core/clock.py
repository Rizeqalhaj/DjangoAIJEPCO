"""Centralized time utility with override support for testing.

In normal operation, now() returns django.utils.timezone.now().
When a time override is set (via the debug API), now() returns
the overridden datetime instead — letting you "time travel" to
test plan verifications, spike detection, etc.

This module also monkey-patches django.utils.timezone.now so that
Django internals (auto_now_add, auto_now, etc.) also respect the
override. This ensures created_at fields use the simulated date.
"""

import django.utils.timezone as _tz
from django.core.cache import cache

CACHE_KEY = "time_override"

_original_now = _tz.now


def now():
    """Return the current datetime, or the override if set."""
    override = cache.get(CACHE_KEY)
    return override if override else _original_now()


def set_override(dt):
    """Set a datetime override. All calls to now() will return this value."""
    cache.set(CACHE_KEY, dt, timeout=None)


def clear_override():
    """Clear the datetime override. now() returns real time again."""
    cache.delete(CACHE_KEY)


def get_override():
    """Return the current override datetime, or None if not set."""
    return cache.get(CACHE_KEY)


# Monkey-patch django.utils.timezone.now so Django internals
# (auto_now_add, auto_now, etc.) also use the override.
_tz.now = now
