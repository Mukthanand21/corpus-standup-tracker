from datetime import datetime
from typing import List, Dict, Any
from mapping import get_team, get_all_teams

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
    
    Args:
        timestamp_str (str): ISO format timestamp.
        
    Returns:
        str: Session name or 'late'.
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

def calculate_compliance(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculates standup compliance for each team based on submissions.
    
    Args:
        submissions (List[Dict[str, Any]]): Raw submission data from API.
        
    Returns:
        List[Dict[str, Any]]: Structured JSON-like output for dashboard.
    """
    # Initialize data for all known teams
    teams = get_all_teams()
    team_data = {
        team: {s: "missing" for s in REQUIRED_SESSIONS} 
        for team in teams
    }

    # Process submissions
    for sub in submissions:
        member_id = sub.get("member_id")
        timestamp = sub.get("timestamp")
        
        if not member_id or not timestamp:
            continue

        team = get_team(member_id)
        
        # If team is not in our initial map, but has submissions, we track it
        if team not in team_data:
            team_data[team] = {s: "missing" for s in REQUIRED_SESSIONS}

        session = classify_session(timestamp)

        # If it matches a required session window, mark as submitted.
        # If it was previously 'missing' and now it's 'late', we might want to prioritize 'submitted'
        # windows if there are multiple submissions.
        if session in REQUIRED_SESSIONS:
            team_data[team][session] = "submitted"
        elif session == "late":
            # Determine which session it was intended for (simple heuristic: closest previous session)
            # For simplicity, we can just mark the first 'missing' session as 'late' if it's outside all windows
            # Or as per user spec: just mark it 'late' in the output if needed.
            # However, the user wants: "Mark session status: submitted (within), late (outside), missing (not submitted)"
            # This implies each session should have one of these 3 statuses.
            # To handle 'late', we need to know which session it WAS for.
            # Let's refine: if it's late, we'll try to guess the session based on sequence or just keep a 'late' flag.
            
            # Logic: If timestamp is between morning_standup and morning_recap, it's a late morning_standup
            # [9-11] Standup, [11-12] Late Standup, [12-13] Recap, etc.
            
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            hour = dt.hour
            
            late_session = None
            if 11 <= hour < 12:
                late_session = "morning_standup"
            elif 13 <= hour < 14:
                late_session = "morning_recap"
            elif 16 <= hour < 17:
                late_session = "afternoon_standup"
            elif 18 <= hour <= 23:
                late_session = "afternoon_recap"
            
            if late_session and team_data[team][late_session] == "missing":
                team_data[team][late_session] = "late"

    # Calculate completion %
    results = []
    for team, sessions in team_data.items():
        # 'submitted' counts as 1, 'late' counts as 0.5 (or according to policy, user just wants %)
        # Usually, % is based on 'submitted'.
        completed = sum(1 for s in sessions.values() if s == "submitted")
        completion = (completed / len(REQUIRED_SESSIONS)) * 100

        results.append({
            "team_name": team,
            **sessions,
            "completion": completion
        })

    return results
