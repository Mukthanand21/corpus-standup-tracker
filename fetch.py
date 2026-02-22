import os
from datetime import UTC, datetime
from typing import Any

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env into os.environ

BASE_URL = os.getenv("BASE_URL", "https://api.corpus.swecha.org/api/v1")


def _parse_timestamp(ts_str: str) -> datetime:
    """Parse an ISO-8601 timestamp string into a timezone-aware UTC datetime."""
    dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


@st.cache_data(ttl=600, show_spinner=False)
def fetch_user_by_id(token: str, user_id: str) -> dict[str, Any]:
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
def search_users(token: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Search users by similarity with username.
    Endpoint: GET /api/v1/users/search?query={query}&limit={limit}

    Returns a list of users matching the query.
    Cached for 10 minutes.
    """
    headers = {"Authorization": f"Bearer {token}"}
    params = {"query": query, "limit": min(limit, 100)}
    try:
        response = requests.get(
            f"{BASE_URL}/users/search", headers=headers, params=params, timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error searching users with query '{query}': {e}")
        return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_categories(token: str) -> list[dict[str, Any]]:
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


@st.cache_data(ttl=300, show_spinner=False)
def fetch_user_audio_contributions(token: str, username: str) -> list[dict[str, Any]]:
    """
    Fetches audio contributions for a specific user by **username**.
    Endpoint: GET /api/v1/users/{username}/contributions/audio

    The API response is expected to be ``{"contributions": [...]}``.
    Each contribution's ``timestamp`` field is converted from an ISO-8601
    string to a timezone-aware UTC ``datetime`` object.

    Returns the raw list of contribution dicts (unfiltered).
    Cached for 5 minutes.
    """
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{BASE_URL}/users/{username}/contributions/audio",
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        # Extract the contributions list from the response envelope
        if isinstance(data, dict):
            records = data.get("contributions", [])
        elif isinstance(data, list):
            records = data
        else:
            records = []

        # Parse timestamp strings -> datetime objects & tag username
        for record in records:
            ts = record.get("timestamp")
            if isinstance(ts, str):
                record["timestamp"] = _parse_timestamp(ts)
            record.setdefault("username", username)
        return records
    except requests.exceptions.RequestException as e:
        print(f"Error fetching audio contributions for user {username}: {e}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Error parsing response for user {username}: {e}")
        return []
