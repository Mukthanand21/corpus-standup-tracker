import requests
from typing import List, Dict, Any

BASE_URL = "https://corpus-backend/api/standups"

def fetch_standups(date_str: str) -> List[Dict[str, Any]]:
    """
    Fetches standup submissions for a specific date from the Corpus API.
    
    Args:
        date_str (str): The date in YYYY-MM-DD format.
        
    Returns:
        List[Dict[str, Any]]: A list of standup submissions.
    """
    try:
        # Note: In a real-world scenario, you might need authentication headers
        response = requests.get(
            BASE_URL,
            params={"date": date_str},
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        # Logging the error or handling based on status code
        print(f"Error fetching standups for {date_str}: {e}")
        return []
