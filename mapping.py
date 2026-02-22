import json
import os
from typing import Dict, List

TEAMS_FILE = "teams.json"

def load_teams() -> Dict[str, List[Dict]]:
    """Loads teams from teams.json."""
    if not os.path.exists(TEAMS_FILE):
        return {"teams": []}
    try:
        with open(TEAMS_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading teams: {e}")
        return {"teams": []}

def save_teams(teams_data: Dict[str, List[Dict]]):
    """Saves teams to teams.json."""
    try:
        with open(TEAMS_FILE, "w") as f:
            json.dump(teams_data, f, indent=4)
    except Exception as e:
        print(f"Error saving teams: {e}")

def get_team_map() -> Dict[str, str]:
    """Returns a flat mapping of username -> team_name."""
    data = load_teams()
    mapping = {}
    for team in data.get("teams", []):
        name = team.get("name")
        for username in team.get("members", []):
            mapping[username] = name
    return mapping

def get_team(username: str) -> str:
    """Returns the team name for a given username."""
    mapping = get_team_map()
    return mapping.get(username, "Unassigned")

def get_all_teams() -> List[str]:
    """Returns a list of all unique team names."""
    data = load_teams()
    return [t.get("name") for t in data.get("teams", [])]

def update_team_membership(team_name: str, usernames: List[str]):
    """Updates members (usernames) of a team."""
    data = load_teams()
    found = False
    for team in data["teams"]:
        if team["name"] == team_name:
            team["members"] = list(set(usernames))
            found = True
            break
    if not found:
        data["teams"].append({"name": team_name, "members": usernames})
    save_teams(data)

def delete_team(team_name: str):
    """Deletes a team."""
    data = load_teams()
    data["teams"] = [t for t in data["teams"] if t["name"] != team_name]
    save_teams(data)
