"""
auth.py – Corpus authentication helpers.

Provides ``login()`` for phone+password auth against the Corpus API,
and ``fetch_current_user()`` for retrieving the logged-in user's profile.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://api.corpus.swecha.org/api/v1")


def login(phone: str, password: str) -> dict:
    """
    Authenticate against the Corpus API.

    Returns
    -------
    dict
        On success: ``{"success": True, "token": "<access_token>", "user": {...}}``
        On failure: ``{"success": False, "message": "..."}``
    """
    try:
        resp = requests.post(
            f"{BASE_URL}/auth/login",
            json={"phone": phone, "password": password},
            timeout=15,
        )
        data = resp.json()

        if resp.status_code == 200:
            token = (
                data.get("access_token")
                or data.get("token")
                or data.get("data", {}).get("access_token")
                or data.get("data", {}).get("token")
            )
            if token:
                return {"success": True, "token": token}
            return {
                "success": False,
                "message": "Login succeeded but no token found in response.",
            }

        msg = data.get("message") or data.get("detail") or resp.text[:200]
        return {"success": False, "message": msg}

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot reach the Corpus API. Check your network."}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Login request timed out. Try again."}
    except Exception as exc:
        return {"success": False, "message": f"Unexpected error: {exc}"}


def fetch_current_user(token: str) -> dict:
    """
    Fetch the currently authenticated user's profile via ``/auth/me``.

    Returns the user dict on success, or an empty dict on failure.
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return {}
