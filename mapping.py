from typing import Dict

# Example team mapping (replace with DB or config file later)
TEAM_MAP: Dict[str, str] = {
    "u101": "Team Alpha",
    "u102": "Team Alpha",
    "u201": "Team Beta",
    "u202": "Team Beta"
}

def get_team(member_id: str) -> str:
    """
    Maps a member ID to their respective team.
    
    Args:
        member_id (str): The unique ID of the team member.
        
    Returns:
        str: The team name or 'Unassigned' if not found.
    """
    return TEAM_MAP.get(member_id, "Unassigned")

def get_all_teams() -> list:
    """Returns a list of unique team names."""
    return list(set(TEAM_MAP.values()))
