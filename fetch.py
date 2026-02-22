import os
import requests
import streamlit as st
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env into os.environ

BASE_URL = os.getenv("BASE_URL", "https://api.corpus.swecha.org/api/v1")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_records(token: str, target_date: str = None, category_id: str = None, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetches records from the Swecha Corpus API.
    Results are cached for 5 minutes (ttl=300s) to avoid repeated API calls.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": limit}
    if category_id:
        params["category_id"] = category_id
    # Pass date to server if API supports it (reduces payload significantly)
    if target_date:
        params["date"] = target_date
        
    try:
        response = requests.get(
            f"{BASE_URL}/records/",
            headers=headers,
            params=params,
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        # Handle both list response and paginated {"items": [...]} response
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get("items", data.get("data", data.get("results", [])))
        return []
    except Exception as e:
        print(f"Error fetching records: {e}")
        return []

@st.cache_data(ttl=600, show_spinner=False)
def fetch_user_by_id(token: str, user_id: str) -> Dict[str, Any]:
    """
    Fetches details for a specific user by their UUID.
    Cached for 10 minutes.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/users/{user_id}", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching user {user_id}: {e}")
        return {}

@st.cache_data(ttl=600, show_spinner=False)
def fetch_users(token: str) -> List[Dict[str, Any]]:
    """
    Fetches all users (if permitted). Cached for 10 minutes.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/users/", headers=headers, params={"limit": 1000}, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error bulk fetching users: {e}")
        return []

@st.cache_data(ttl=600, show_spinner=False)
def fetch_categories(token: str) -> List[Dict[str, Any]]:
    """
    Fetches available categories. Cached for 10 minutes.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(f"{BASE_URL}/categories/", headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching categories: {e}")
        return []
