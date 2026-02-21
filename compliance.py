from datetime import datetime
from typing import List, Dict, Any
from mapping import get_team

REQUIRED_SESSIONS = [
    "morning_standup",
    "morning_recap",
    "afternoon_standup",
    "afternoon_recap"
]

# Time windows for sessions (Start Hour inclusive, End Hour exclusive)
SESSION_WINDOWS = {
    "morning_standup": (9, 11),
    "morning_recap": (12, 13),
    "afternoon_standup": (14, 16),
    "afternoon_recap": (17, 18),
}

def classify_session(timestamp_str: str) -> str:
    """
    Classifies a submission into a session or marks it as 'late' based on the timestamp.
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        hour = dt.hour

        for session, (start, end) in SESSION_WINDOWS.items():
            if start <= hour < end:
                return session
        
        return "late"
    except Exception:
        return "invalid"

def calculate_compliance(records: List[Dict[str, Any]], target_date: str, all_teams: List[str]) -> List[Dict[str, Any]]:
    """
    Calculates standup compliance for each team based on records and a target date.
    
    Args:
        records (List[Dict[str, Any]]): Raw record data from Swecha API.
        target_date (str): The date to filter for (YYYY-MM-DD).
        all_teams (List[str]): List of all team names from teams.json.
        
    Returns:
        List[Dict[str, Any]]: Structured status for each team.
    """
    # Initialize all created teams with "missing"
    team_data = {team: {s: "missing" for s in REQUIRED_SESSIONS} for team in all_teams}

    # Process records
    for record in records:
        # Swecha schema: user_id and created_at
        user_id = record.get("user_id")
        created_at = record.get("created_at")
        
        if not user_id or not created_at:
            continue

        # Filter for target date
        if not created_at.startswith(target_date):
            continue

        team = get_team(user_id)
        
        # If team is not in created list, but has active uploads, add it to data
        if team not in team_data:
            team_data[team] = {s: "missing" for s in REQUIRED_SESSIONS}

        session = classify_session(created_at)

        if session in REQUIRED_SESSIONS:
            team_data[team][session] = "submitted"
        elif session == "late":
            # Heuristic for late classification
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            hour = dt.hour
            
            late_session = None
            if 11 <= hour < 12: late_session = "morning_standup"
            elif 13 <= hour < 14: late_session = "morning_recap"
            elif 16 <= hour < 17: late_session = "afternoon_standup"
            elif 18 <= hour <= 23: late_session = "afternoon_recap"
            
            if late_session and team_data[team][late_session] == "missing":
                team_data[team][late_session] = "late"

    # Format results
    results = []
    for team, sessions in team_data.items():
        completed = sum(1 for s in sessions.values() if s == "submitted")
        completion = (completed / len(REQUIRED_SESSIONS)) * 100

        results.append({
            "team_name": team,
            **sessions,
            "completion": completion
        })

    return results
