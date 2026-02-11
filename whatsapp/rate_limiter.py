"""Rate limiter using Django cache (works with LocMemCache and Redis)."""

import logging
from django.core.cache import cache

logger = logging.getLogger("whatsapp")

MAX_MESSAGES_PER_HOUR = 30
RATE_LIMIT_WINDOW_SECONDS = 3600


def check_rate_limit(phone: str) -> bool:
    """
    Check if a phone number has exceeded the rate limit.

    Returns True if the message is ALLOWED, False if rate-limited.
    """
    key = f"rate:{phone}"
    current = cache.get(key)

    if current is None:
        cache.set(key, 1, RATE_LIMIT_WINDOW_SECONDS)
        return True

    if current >= MAX_MESSAGES_PER_HOUR:
        logger.warning("Rate limit exceeded for %s (%d msgs)", phone, current)
        return False

    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, RATE_LIMIT_WINDOW_SECONDS)

    return True
