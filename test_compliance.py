import json
from compliance import calculate_compliance

# Mock submission data
mock_submissions = [
    # Team Alpha (u101, u102)
    # morning_standup: NO ONE on time, but Bob is late
    {"member_id": "u102", "name": "Bob", "timestamp": "2026-02-21T11:15:00", "label": "stand-up"},   # late (morning_standup)
    {"member_id": "u101", "name": "Alice", "timestamp": "2026-02-21T14:30:00", "label": "stand-up"}, # submitted
    # Team Beta (u201, u202)
    {"member_id": "u201", "name": "Charlie", "timestamp": "2026-02-21T09:30:00", "label": "stand-up"}, # submitted
    {"member_id": "u201", "name": "Charlie", "timestamp": "2026-02-21T12:30:00", "label": "stand-up"}, # submitted
    {"member_id": "u201", "name": "Charlie", "timestamp": "2026-02-21T14:30:00", "label": "stand-up"}, # submitted
    {"member_id": "u201", "name": "Charlie", "timestamp": "2026-02-21T17:30:00", "label": "stand-up"}, # submitted
]

def test_compliance_output():
    results = calculate_compliance(mock_submissions)
    
    print("Compliance Results JSON:")
    print(json.dumps(results, indent=2))
    
    # Simple assertions
    for team in results:
        if team["team_name"] == "Team Beta":
            assert team["completion"] == 100.0
            print("✅ Team Beta 100% check passed")
        if team["team_name"] == "Team Alpha":
            assert team["morning_standup"] == "late" # Bob was late, Alice missing
            assert team["afternoon_standup"] == "submitted"
            assert team["morning_recap"] == "missing"
            assert team["afternoon_recap"] == "missing"
            assert team["completion"] == 25.0 # Only 1/4 (late doesn't count for on-time %)
            print("✅ Team Alpha 'late' check passed")

if __name__ == "__main__":
    test_compliance_output()
