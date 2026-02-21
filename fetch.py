import requests
from typing import List, Dict, Any

BASE_URL = "https://api.corpus.swecha.org/api/v1"

def fetch_records(token: str, category_id: str = None, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Fetches records from the Swecha Corpus API.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": limit}
    if category_id:
        params["category_id"] = category_id
        
    try:
        response = requests.get(f"{BASE_URL}/records/", headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching records: {e}")
        return []

def fetch_user_by_id(token: str, user_id: str) -> Dict[str, Any]:
    """
    Fetches details for a specific user by their UUID.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/users/{user_id}", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching user {user_id}: {e}")
        return {}

def fetch_users(token: str) -> List[Dict[str, Any]]:
    """
    Fetches all users (if permitted).
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/users/", headers=headers, params={"limit": 1000}, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error bulk fetching users: {e}")
        return []

def fetch_categories(token: str) -> List[Dict[str, Any]]:
    """
    Fetches available categories.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/categories/", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []
