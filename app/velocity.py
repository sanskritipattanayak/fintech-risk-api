"""Velocity check: transactions per card per sliding window.

All timestamps must be timezone-aware; they are normalised to UTC. Naive
datetimes are rejected rather than guessed, because guessing a zone is how
boundary bugs near midnight UTC happen.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal


def to_utc(ts: datetime) -> datetime:
    """Return ``ts`` as UTC. Raises ValueError for naive datetimes."""
    if ts.tzinfo is None or ts.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return ts.astimezone(UTC)


def amount_exceeds_limit(amount: Decimal, limit: Decimal) -> bool:
    """True if ``amount`` is strictly greater than ``limit``. Money is Decimal."""
    if not isinstance(amount, Decimal) or not isinstance(limit, Decimal):
        raise TypeError("money values must be Decimal")
    return amount > limit


class VelocityChecker:
    """In-memory sliding-window counter of transactions per card.

    A transaction is declined when ``max_txns`` or more earlier transactions
    for the same card fall in the half-open window ``(ts - window, ts]``.
    Declined attempts are recorded too, so a burst keeps counting.
    """

    def __init__(self, max_txns: int = 5, window: timedelta = timedelta(minutes=10)) -> None:
        if max_txns < 1:
            raise ValueError("max_txns must be >= 1")
        if window <= timedelta(0):
            raise ValueError("window must be positive")
        self.max_txns = max_txns
        self.window = window
        self._events: dict[str, list[datetime]] = defaultdict(list)

    def check_and_record(self, card_id: str, ts: datetime) -> bool:
        """Record the attempt and return True if it is within velocity limits."""
        now = to_utc(ts)
        start = now - self.window
        events = self._events[card_id]
        recent = [e for e in events if start < e <= now]
        allowed = len(recent) < self.max_txns
        # Keep only events still relevant to later in-order requests.
        self._events[card_id] = [e for e in events if e > start]
        self._events[card_id].append(now)
        return allowed

    def count_in_window(self, card_id: str, ts: datetime) -> int:
        """Number of recorded transactions for ``card_id`` in ``(ts - window, ts]``."""
        now = to_utc(ts)
        start = now - self.window
        return sum(1 for e in self._events.get(card_id, []) if start < e <= now)
