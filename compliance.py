from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

STANDUP_CATEGORY_ID = "4dd053f4-6323-43d4-87a3-ce1816bd9459"

# IST is UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

REQUIRED_SESSIONS = [
    "morning_standup",
    "morning_recap",
    "afternoon_standup",
    "afternoon_recap",
]

# Time windows for sessions — IST hours (Start inclusive, End exclusive)
SESSION_WINDOWS = {
    "morning_standup": (9, 11),  # 09:00–10:59 IST
    "morning_recap": (12, 13),  # 12:00–12:59 IST
    "afternoon_standup": (14, 16),  # 14:00–15:59 IST
    "afternoon_recap": (17, 18),  # 17:00–17:59 IST
}

# Late windows — IST hours (submissions outside on-time but attributable)
LATE_WINDOWS = {
    "morning_standup": (11, 12),  # 11:00–11:59 IST
    "morning_recap": (13, 14),  # 13:00–13:59 IST
    "afternoon_standup": (16, 17),  # 16:00–16:59 IST
    "afternoon_recap": (18, 24),  # 18:00–23:59 IST
}


def _to_ist(dt: datetime) -> datetime:
    """Convert a datetime to IST.  Naïve datetimes are assumed UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)


def _is_standup_on_date(record: dict[str, Any], target_date: date) -> bool:
    """Return True if *record* is a Stand-Up contribution on *target_date* (IST)."""
    ts = record.get("timestamp")
    if not isinstance(ts, datetime):
        return False
    if STANDUP_CATEGORY_ID not in record.get("category_ids", []):
        return False
    return _to_ist(ts).date() == target_date


# ── Binary helper (kept for any code that still calls it) ────────────────
def team_has_standup_submission(
    team_usernames: list[str],
    records_by_user: dict[str, list[dict[str, Any]]],
    target_date: date,
) -> bool:
    """Return True if ANY member has at least one Stand-Up contribution on
    *target_date*.  Short-circuits on first match.  Pure function."""
    for username in team_usernames:
        for record in records_by_user.get(username, []):
            if _is_standup_on_date(record, target_date):
                return True
    return False


# ── Per-slot compliance (the primary function used by the dashboard) ─────
def get_team_slot_compliance(
    team_usernames: list[str],
    records_by_user: dict[str, list[dict[str, Any]]],
    target_date: date,
) -> dict[str, str]:
    """
    Pure function — checks each session slot independently.

    For every team member's contributions on *target_date*:
      • If the IST hour falls inside a slot's on-time window → "submitted"
      • Else if it falls inside the late window → "late" (only if not already submitted)
      • Otherwise slot stays "missing"

    Returns dict like::

        {
            "morning_standup":   "submitted" | "late" | "missing",
            "morning_recap":     ...,
            "afternoon_standup": ...,
            "afternoon_recap":   ...,
        }

    No I/O, no API calls, no Streamlit dependency.
    """
    slots: dict[str, str] = {s: "missing" for s in REQUIRED_SESSIONS}

    for username in team_usernames:
        for record in records_by_user.get(username, []):
            if not _is_standup_on_date(record, target_date):
                continue

            ist_hour = _to_ist(record["timestamp"]).hour

            # Check on-time windows first
            for session, (start, end) in SESSION_WINDOWS.items():
                if start <= ist_hour < end:
                    slots[session] = "submitted"
                    break
            else:
                # Not in any on-time window → check late windows
                for session, (start, end) in LATE_WINDOWS.items():
                    if start <= ist_hour < end and slots[session] == "missing":
                        slots[session] = "late"
                        break

    return slots
