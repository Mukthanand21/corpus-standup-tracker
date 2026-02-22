from datetime import datetime, date, timezone, timedelta
from compliance import (
    team_has_standup_submission,
    get_team_slot_compliance,
    STANDUP_CATEGORY_ID,
    REQUIRED_SESSIONS,
)

UTC = timezone.utc
IST = timezone(timedelta(hours=5, minutes=30))
WRONG_CATEGORY = "00000000-0000-0000-0000-000000000000"


# ── helpers ──────────────────────────────────────────────────────────────
def _utc(year, month, day, hour, minute=0):
    """Shortcut to build a UTC datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=UTC)


def _ist_to_utc(year, month, day, hour, minute=0):
    """Build a datetime at the given IST hour, stored as UTC."""
    return datetime(year, month, day, hour, minute, tzinfo=IST).astimezone(UTC)


# ═══════════════════════════════════════════════════════════════════════
#  team_has_standup_submission (binary)
# ═══════════════════════════════════════════════════════════════════════

def test_no_submissions_returns_false():
    records_by_user = {"alice": [], "bob": []}
    assert team_has_standup_submission(
        ["alice", "bob"], records_by_user, date(2026, 2, 21)
    ) is False


def test_wrong_category_returns_false():
    records_by_user = {
        "alice": [{
            "category_ids": [WRONG_CATEGORY],
            "timestamp": _utc(2026, 2, 21, 7, 12),
        }]
    }
    assert team_has_standup_submission(
        ["alice"], records_by_user, date(2026, 2, 21)
    ) is False


def test_wrong_date_returns_false():
    records_by_user = {
        "alice": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _utc(2026, 2, 20, 10),
        }]
    }
    assert team_has_standup_submission(
        ["alice"], records_by_user, date(2026, 2, 21)
    ) is False


def test_valid_standup_submission_returns_true():
    records_by_user = {
        "bob": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _utc(2026, 2, 21, 7, 12),
        }]
    }
    assert team_has_standup_submission(
        ["bob"], records_by_user, date(2026, 2, 21)
    ) is True


def test_multiple_users_one_valid_returns_true():
    records_by_user = {
        "alice": [],
        "bob": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _utc(2026, 2, 21, 6, 2),
        }],
    }
    assert team_has_standup_submission(
        ["alice", "bob"], records_by_user, date(2026, 2, 21)
    ) is True


def test_user_not_in_records_returns_false():
    assert team_has_standup_submission(
        ["charlie"], {}, date(2026, 2, 21)
    ) is False


def test_missing_timestamp_skipped():
    records_by_user = {
        "alice": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": None,
        }]
    }
    assert team_has_standup_submission(
        ["alice"], records_by_user, date(2026, 2, 21)
    ) is False


def test_multiple_categories_match():
    records_by_user = {
        "alice": [{
            "category_ids": [WRONG_CATEGORY, STANDUP_CATEGORY_ID],
            "timestamp": _utc(2026, 2, 21, 14, 30),
        }]
    }
    assert team_has_standup_submission(
        ["alice"], records_by_user, date(2026, 2, 21)
    ) is True


def test_empty_category_ids_returns_false():
    records_by_user = {
        "bob": [{
            "category_ids": [],
            "timestamp": _utc(2026, 2, 21, 9),
        }]
    }
    assert team_has_standup_submission(
        ["bob"], records_by_user, date(2026, 2, 21)
    ) is False


# ═══════════════════════════════════════════════════════════════════════
#  get_team_slot_compliance (per-slot)
# ═══════════════════════════════════════════════════════════════════════

def test_slot_no_records_all_missing():
    """No records → every slot is 'missing'."""
    slots = get_team_slot_compliance(["alice"], {"alice": []}, date(2026, 2, 22))
    assert all(v == "missing" for v in slots.values())


def test_slot_morning_standup_submitted():
    """Standup at 10:00 IST → morning_standup = submitted, rest missing."""
    records_by_user = {
        "alice": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _ist_to_utc(2026, 2, 22, 10, 0),   # 10:00 IST
        }]
    }
    slots = get_team_slot_compliance(["alice"], records_by_user, date(2026, 2, 22))
    assert slots["morning_standup"] == "submitted"
    assert slots["morning_recap"] == "missing"
    assert slots["afternoon_standup"] == "missing"
    assert slots["afternoon_recap"] == "missing"


def test_slot_afternoon_recap_submitted():
    """Standup at 17:30 IST → afternoon_recap = submitted."""
    records_by_user = {
        "bob": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _ist_to_utc(2026, 2, 22, 17, 30),  # 17:30 IST
        }]
    }
    slots = get_team_slot_compliance(["bob"], records_by_user, date(2026, 2, 22))
    assert slots["afternoon_recap"] == "submitted"
    assert slots["morning_standup"] == "missing"


def test_slot_late_morning_standup():
    """Standup at 11:30 IST → morning_standup = late."""
    records_by_user = {
        "alice": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _ist_to_utc(2026, 2, 22, 11, 30),  # 11:30 IST
        }]
    }
    slots = get_team_slot_compliance(["alice"], records_by_user, date(2026, 2, 22))
    assert slots["morning_standup"] == "late"
    assert slots["morning_recap"] == "missing"


def test_slot_wrong_category_ignored():
    """Submission with wrong category → all missing even if time matches."""
    records_by_user = {
        "alice": [{
            "category_ids": [WRONG_CATEGORY],
            "timestamp": _ist_to_utc(2026, 2, 22, 10, 0),
        }]
    }
    slots = get_team_slot_compliance(["alice"], records_by_user, date(2026, 2, 22))
    assert all(v == "missing" for v in slots.values())


def test_slot_wrong_date_ignored():
    """Standup on a different date → all missing."""
    records_by_user = {
        "alice": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _ist_to_utc(2026, 2, 21, 10, 0),
        }]
    }
    slots = get_team_slot_compliance(["alice"], records_by_user, date(2026, 2, 22))
    assert all(v == "missing" for v in slots.values())


def test_slot_multiple_submissions_multiple_slots():
    """Multiple submissions filling different slots."""
    records_by_user = {
        "alice": [
            {
                "category_ids": [STANDUP_CATEGORY_ID],
                "timestamp": _ist_to_utc(2026, 2, 22, 9, 30),   # morning_standup
            },
            {
                "category_ids": [STANDUP_CATEGORY_ID],
                "timestamp": _ist_to_utc(2026, 2, 22, 14, 15),  # afternoon_standup
            },
        ]
    }
    slots = get_team_slot_compliance(["alice"], records_by_user, date(2026, 2, 22))
    assert slots["morning_standup"] == "submitted"
    assert slots["afternoon_standup"] == "submitted"
    assert slots["morning_recap"] == "missing"
    assert slots["afternoon_recap"] == "missing"


def test_slot_late_does_not_overwrite_submitted():
    """If one user is on time and another late, slot stays 'submitted'."""
    records_by_user = {
        "alice": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _ist_to_utc(2026, 2, 22, 10, 0),   # on-time
        }],
        "bob": [{
            "category_ids": [STANDUP_CATEGORY_ID],
            "timestamp": _ist_to_utc(2026, 2, 22, 11, 30),  # late
        }],
    }
    slots = get_team_slot_compliance(
        ["alice", "bob"], records_by_user, date(2026, 2, 22)
    )
    assert slots["morning_standup"] == "submitted"


if __name__ == "__main__":
    # Binary tests
    test_no_submissions_returns_false()
    test_wrong_category_returns_false()
    test_wrong_date_returns_false()
    test_valid_standup_submission_returns_true()
    test_multiple_users_one_valid_returns_true()
    test_user_not_in_records_returns_false()
    test_missing_timestamp_skipped()
    test_multiple_categories_match()
    test_empty_category_ids_returns_false()
    # Per-slot tests
    test_slot_no_records_all_missing()
    test_slot_morning_standup_submitted()
    test_slot_afternoon_recap_submitted()
    test_slot_late_morning_standup()
    test_slot_wrong_category_ignored()
    test_slot_wrong_date_ignored()
    test_slot_multiple_submissions_multiple_slots()
    test_slot_late_does_not_overwrite_submitted()
    print("✅ All tests passed!")
