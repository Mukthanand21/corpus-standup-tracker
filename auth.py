"""
auth.py – Corpus login helper.

Reads CORPUS_PHONE and CORPUS_PASSWORD from .env and auto-authenticates
against the Corpus API at startup.  No interactive login required.
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
        On success: ``{"success": True, "token": "<access_token>"}``
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
            return {"success": False, "message": "Login succeeded but no token found in response."}

        msg = data.get("message") or data.get("detail") or resp.text[:200]
        return {"success": False, "message": msg}

    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot reach the Corpus API. Check your network."}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Login request timed out. Try again."}
    except Exception as exc:
        return {"success": False, "message": f"Unexpected error: {exc}"}


def get_token() -> str:
    """
    Auto-login using credentials from .env and return a fresh Bearer token.

    Reads ``CORPUS_PHONE`` and ``CORPUS_PASSWORD`` environment variables,
    calls the login endpoint, and returns the access token string.
    Raises ``RuntimeError`` if credentials are missing or login fails.
    """
    phone = os.getenv("CORPUS_PHONE", "")
    password = os.getenv("CORPUS_PASSWORD", "")

    if not phone or not password:
        raise RuntimeError(
            "CORPUS_PHONE and CORPUS_PASSWORD must be set in .env"
        )

    result = login(phone, password)
    if result["success"]:
        return result["token"]
    raise RuntimeError(f"Auto-login failed: {result['message']}")
