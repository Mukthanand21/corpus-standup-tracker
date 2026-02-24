import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import date, datetime, timedelta, timezone
from dotenv import load_dotenv
from fetch import fetch_user_by_id, fetch_user_audio_contributions, search_users
from compliance import get_team_slot_compliance, REQUIRED_SESSIONS
from mapping import load_teams, save_teams, delete_team, get_all_teams
import os

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://api.corpus.swecha.org/api/v1")

# Initialize session state for login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "api_token" not in st.session_state:
    st.session_state["api_token"] = None
if "user_phone" not in st.session_state:
    st.session_state["user_phone"] = None
if "user_name" not in st.session_state:
    st.session_state["user_name"] = None


def fetch_current_user(token: str) -> dict:
    """Fetch the currently logged-in user's profile."""
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


def login(phone: str, password: str) -> dict:
    """Authenticate against the Corpus API."""
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
            # Try to extract the user's name from the login response
            user_data = data.get("user") or data.get("data", {}).get("user") or data
            name = (
                user_data.get("name")
                or user_data.get("username")
                or user_data.get("full_name")
                or user_data.get("display_name")
                or ""
            )
            if token:
                return {"success": True, "token": token, "name": name}
            return {"success": False, "message": "Login succeeded but no token found in response."}
        msg = data.get("message") or data.get("detail") or resp.text[:200]
        return {"success": False, "message": msg}
    except requests.exceptions.ConnectionError:
        return {"success": False, "message": "Cannot reach the Corpus API. Check your network."}
    except requests.exceptions.Timeout:
        return {"success": False, "message": "Login request timed out. Try again."}
    except Exception as exc:
        return {"success": False, "message": f"Unexpected error: {exc}"}


# Set page config
st.set_page_config(
    page_title="Standup Tracker · Viswam.Ai",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN PAGE  – styled to match main app
# ══════════════════════════════════════════════════════════════════════════════
if not st.session_state.get("logged_in"):

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Nunito:wght@400;600;700&display=swap');

    html, body, [class*="css"] {
        background: #070d1a !important;
        color: #e8edf8 !important;
        font-family: 'Nunito', sans-serif !important;
    }
    .stApp { background: #070d1a !important; }
    #MainMenu, footer, header { visibility: hidden; }
    [data-testid="stToolbar"] { display: none; }

    .block-container {
        max-width: 460px !important;
        padding-top: 10vh !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }

    .stTextInput input {
        background: #111d35 !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 10px !important;
        color: #e8edf8 !important;
        font-family: 'Nunito', sans-serif !important;
        font-size: 14px !important;
    }
    .stTextInput input:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.18) !important;
    }
    .stTextInput input::placeholder { color: #556080 !important; }
    .stTextInput label {
        color: #8899bb !important;
        font-family: 'Syne', sans-serif !important;
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.9px !important;
    }
    .stFormSubmitButton > button {
        font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        border-radius: 10px !important;
        border: none !important;
        background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
        color: white !important;
        box-shadow: 0 4px 20px rgba(37,99,235,0.4) !important;
        width: 100% !important;
        letter-spacing: 0.4px !important;
    }
    .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #1e40af, #1d4ed8) !important;
        box-shadow: 0 6px 28px rgba(37,99,235,0.55) !important;
        transform: translateY(-2px) !important;
    }
    .stSuccess { background: rgba(16,185,129,0.12) !important; border-color: #10b981 !important; color: #34d399 !important; }
    .stError   { background: rgba(239,68,68,0.12)  !important; border-color: #ef4444 !important; color: #f87171 !important; }
    .stSpinner > div { border-top-color: #3b82f6 !important; }
    </style>
    """, unsafe_allow_html=True)

    # Icon + title using plain Streamlit
    st.markdown("# ⚡ Standup Tracker")
    st.markdown("##### Welcome back")
    st.caption("Sign in to your Corpus account")
    st.markdown("---")

    with st.form("login_form", clear_on_submit=False):
        st.markdown("Phone Number")
        col_prefix, col_number = st.columns([1, 4])
        with col_prefix:
            st.text_input(
                "Prefix",
                value="+91",
                disabled=True,
                label_visibility="collapsed",
            )
        with col_number:
            phone_number = st.text_input(
                "Number",
                placeholder="9999999999",
                label_visibility="collapsed",
            )
        phone = f"+91{phone_number}" if phone_number else ""
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password",
        )
        st.markdown("<br>", unsafe_allow_html=True)
        submit_button = st.form_submit_button("Sign In →", use_container_width=True)

    if submit_button:
        if not phone_number or not password:
            st.error("Please enter both phone number and password.")
        else:
            with st.spinner("Authenticating…"):
                result = login(phone, password)
                if result["success"]:
                    st.session_state["logged_in"] = True
                    st.session_state["api_token"] = result["token"]
                    st.session_state["user_phone"] = phone
                    # Get user name from login response or fetch profile
                    name = result.get("name", "")
                    if not name:
                        profile = fetch_current_user(result["token"])
                        name = (
                            profile.get("name")
                            or profile.get("username")
                            or profile.get("full_name")
                            or profile.get("display_name")
                            or ""
                        )
                    st.session_state["user_name"] = name or phone
                    st.rerun()
                else:
                    st.error(f"❌ {result['message']}")

    st.stop()

# Get API token after login
api_token: str = st.session_state.get("api_token", "")

# ─────────────────────────────────────────────────────────────────────────────
# MAIN APP (shown after successful login)
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# MASTER STYLESHEET
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;700&family=Nunito:wght@300;400;500;600;700&display=swap');

:root {
  --bg:        #070d1a;
  --surface:   #0d1629;
  --surface2:  #111d35;
  --surface3:  #162440;
  --border:    rgba(255,255,255,0.07);
  --border2:   rgba(255,255,255,0.12);
  --text:      #e8edf8;
  --text2:     #8899bb;
  --text3:     #556080;
  --amber:     #f59e0b;
  --amber2:    #fbbf24;
  --green:     #10b981;
  --green2:    #34d399;
  --red:       #ef4444;
  --red2:      #f87171;
  --blue:      #3b82f6;
  --blue2:     #60a5fa;
  --violet:    #8b5cf6;
}

html, body, [class*="css"] {
  font-family: 'Nunito', sans-serif;
  background: var(--bg) !important;
  color: var(--text) !important;
}

.stApp { background: var(--bg) !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: var(--surface) !important;
  border-right: 1px solid var(--border2) !important;
}
[data-testid="stSidebar"] > div { padding-top: 24px; }
[data-testid="stSidebar"] * { color: var(--text2) !important; }
[data-testid="stSidebar"] strong, [data-testid="stSidebar"] h3 { color: var(--text) !important; }
[data-testid="stSidebar"] hr { border-color: var(--border2) !important; margin: 16px 0; }
[data-testid="stSidebar"] table { width: 100%; border-collapse: collapse; }
[data-testid="stSidebar"] th { color: var(--text3) !important; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; padding: 6px 8px; border-bottom: 1px solid var(--border) !important; }
[data-testid="stSidebar"] td { padding: 8px; font-size: 12px; border-bottom: 1px solid var(--border) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--surface2) !important;
  border-radius: 14px !important;
  padding: 6px !important;
  gap: 4px !important;
  border: 1px solid var(--border2) !important;
}
.stTabs [data-baseweb="tab"] {
  border-radius: 10px !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 600 !important;
  font-size: 13px !important;
  color: var(--text3) !important;
  padding: 8px 20px !important;
  transition: all 0.2s !important;
}
.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, #1a2d5a, #1e3a8a) !important;
  color: #fff !important;
  box-shadow: 0 4px 16px rgba(59,130,246,0.3) !important;
}

/* ── Buttons ── */
.stButton > button {
  font-family: 'Syne', sans-serif !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  border-radius: 10px !important;
  border: 1px solid var(--border2) !important;
  background: var(--surface3) !important;
  color: var(--text) !important;
  transition: all 0.2s !important;
  letter-spacing: 0.3px;
}
.stButton > button:hover {
  background: var(--surface2) !important;
  border-color: var(--blue) !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 20px rgba(59,130,246,0.2) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #1d4ed8, #2563eb) !important;
  border: none !important;
  color: white !important;
  box-shadow: 0 4px 20px rgba(37,99,235,0.4) !important;
}
.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #1e40af, #1d4ed8) !important;
  box-shadow: 0 6px 28px rgba(37,99,235,0.55) !important;
  transform: translateY(-2px) !important;
}

/* ── Inputs ── */
.stTextInput input, .stSelectbox > div > div, .stDateInput input,
.stNumberInput input, .stMultiSelect > div > div {
  background: var(--surface2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
  font-family: 'Nunito', sans-serif !important;
  font-size: 14px !important;
}
.stTextInput input:focus { border-color: var(--blue) !important; box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important; }
.stSelectbox > div > div { padding: 2px 10px !important; }
div[data-baseweb="select"] > div { background: var(--surface2) !important; border-color: var(--border2) !important; }
div[data-baseweb="popover"] { background: var(--surface2) !important; border: 1px solid var(--border2) !important; }
li[role="option"] { color: var(--text) !important; background: var(--surface2) !important; }
li[role="option"]:hover { background: var(--surface3) !important; }

/* ── Labels / text ── */
label, .stTextInput label, .stSelectbox label, .stDateInput label,
.stMultiSelect label, .stNumberInput label {
  color: var(--text2) !important;
  font-family: 'Syne', sans-serif !important;
  font-size: 12px !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.8px !important;
}
p, li, .stMarkdown p { color: var(--text2) !important; font-size: 14px; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; color: var(--text) !important; }

/* ── Expander ── */
.streamlit-expanderHeader {
  background: var(--surface2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
  font-family: 'Syne', sans-serif !important;
  font-weight: 700 !important;
  font-size: 14px !important;
  padding: 12px 16px !important;
  transition: all 0.2s !important;
}
.streamlit-expanderHeader:hover {
  border-color: var(--blue) !important;
  background: var(--surface3) !important;
}
.streamlit-expanderContent {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-top: none !important;
  border-radius: 0 0 12px 12px !important;
  padding: 16px !important;
}

/* ── Spinner / misc ── */
.stSpinner > div { border-top-color: var(--blue) !important; }
.stSuccess { background: rgba(16,185,129,0.12) !important; border-color: var(--green) !important; color: var(--green2) !important; }
.stWarning { background: rgba(245,158,11,0.12) !important; border-color: var(--amber) !important; color: var(--amber2) !important; }
.stInfo { background: rgba(59,130,246,0.1) !important; border-color: var(--blue) !important; color: var(--blue2) !important; }
.stError { background: rgba(239,68,68,0.12) !important; border-color: var(--red) !important; color: var(--red2) !important; }
hr { border-color: var(--border2) !important; }

/* ── streamlit-searchbox dark theme ── */
div[data-testid="stForm"],
.searchbox-container,
[data-baseweb="input"],
[data-baseweb="base-input"] {
  background: var(--surface2) !important;
  border-color: var(--border2) !important;
  color: var(--text) !important;
}
div[data-baseweb="input"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
}
div[data-baseweb="input"]:focus-within {
  border-color: var(--blue) !important;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
}
div[data-baseweb="input"] input {
  background: transparent !important;
  color: var(--text) !important;
  font-family: 'Nunito', sans-serif !important;
  font-size: 14px !important;
  caret-color: var(--blue) !important;
}
div[data-baseweb="input"] input::placeholder { color: var(--text3) !important; }
ul[data-baseweb="menu"],
div[data-baseweb="menu"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
  box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
}
li[data-baseweb="menu-item"],
button[data-baseweb="menu-item"] {
  background: var(--surface2) !important;
  color: var(--text) !important;
  font-family: 'Nunito', sans-serif !important;
  font-size: 13px !important;
}
li[data-baseweb="menu-item"]:hover,
button[data-baseweb="menu-item"]:hover {
  background: var(--surface3) !important;
  color: var(--blue2) !important;
}
div[data-baseweb="input"] svg { fill: var(--text3) !important; }
[data-baseweb="tag"] {
  background: rgba(59,130,246,0.15) !important;
  border-color: rgba(59,130,246,0.3) !important;
  color: var(--blue2) !important;
  border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# HERO HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="
  background: linear-gradient(135deg, #0a1628 0%, #0f2044 40%, #0d1a38 100%);
  border: 1px solid rgba(59,130,246,0.2);
  border-radius: 20px;
  padding: 32px 40px;
  margin-bottom: 28px;
  position: relative;
  overflow: hidden;
">
  <div style="position:absolute;top:-40px;right:-40px;width:200px;height:200px;
    background:radial-gradient(circle, rgba(59,130,246,0.15) 0%, transparent 70%);border-radius:50%;"></div>
  <div style="position:absolute;bottom:-60px;left:20%;width:300px;height:300px;
    background:radial-gradient(circle, rgba(245,158,11,0.06) 0%, transparent 70%);border-radius:50%;"></div>
  <div style="display:flex;align-items:center;gap:20px;position:relative;z-index:1;">
    <div style="
      width:60px;height:60px;
      background:linear-gradient(135deg,#1d4ed8,#3b82f6);
      border-radius:16px;
      display:flex;align-items:center;justify-content:center;
      font-size:28px;
      box-shadow:0 8px 24px rgba(59,130,246,0.4);
    ">⚡</div>
    <div>
      <div style="
        font-family:'Syne',sans-serif;font-size:28px;font-weight:800;
        color:#f1f5f9;letter-spacing:-0.5px;line-height:1;
      ">Standup Compliance Tracker</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
      border-radius:12px;padding:12px;margin-bottom:20px;">
      <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:12px;color:#8899bb;
        margin-bottom:4px;">Logged in as</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:13px;color:#60a5fa;
        margin-bottom:8px;">{st.session_state.get('user_name') or st.session_state.get('user_phone', 'Unknown')}</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["api_token"] = None
        st.session_state["user_phone"] = None
        st.session_state["user_name"] = None
        st.rerun()

    st.markdown("---")

    st.markdown("""
    <div style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;
      color:#e8edf8;margin-bottom:4px;letter-spacing:-0.3px;">Session Windows</div>
    <div style="font-size:11px;color:#556080;font-family:'JetBrains Mono',monospace;
      letter-spacing:0.5px;margin-bottom:16px;">ALL TIMES IN IST</div>
    """, unsafe_allow_html=True)

    sessions = [
        ("🌅", "Morning Standup",   "09:00–09:30", "09:30–10:30"),
        ("🔄", "Morning Recap",     "12:00–12:30", "12:30–13:30"),
        ("☀️", "Afternoon Standup", "13:30–14:00", "14:00–15:00"),
        ("🌆", "Afternoon Recap",   "16:30–17:00", "17:00–00:00"),
    ]
    for icon, name, on_time, late in sessions:
        st.markdown(f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);
          border-radius:10px;padding:10px 12px;margin-bottom:8px;">
          <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:12px;color:#8899bb;
            margin-bottom:6px;">{icon} {name}</div>
          <div style="display:flex;gap:8px;">
            <div style="flex:1;background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.2);
              border-radius:6px;padding:3px 8px;font-family:'JetBrains Mono',monospace;
              font-size:10px;color:#34d399;">✓ {on_time}</div>
            <div style="flex:1;background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.2);
              border-radius:6px;padding:3px 8px;font-family:'JetBrains Mono',monospace;
              font-size:10px;color:#fbbf24;">⚡ {late}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'Syne',sans-serif;font-size:11px;font-weight:700;
      color:#556080;letter-spacing:1px;text-transform:uppercase;margin-bottom:10px;">Legend</div>
    """, unsafe_allow_html=True)
    for icon, label, color in [
        ("✅", "Submitted — On time",     "#10b981"),
        ("⚠️", "Late — Grace window",     "#f59e0b"),
        ("❌", "Missing — No submission", "#ef4444"),
    ]:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
          <span>{icon}</span>
          <span style="font-size:12px;color:{color};">{label}</span>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab_dash, tab_analytics, tab_teams = st.tabs([
    "⚡  Compliance",
    "📊  Analytics",
    "👥  Team Management",
])

# ══════════════════════════════════════════════════════════════════════════════
#  COMPLIANCE DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab_dash:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1629,#111d35);
      border:1px solid rgba(255,255,255,0.08);border-radius:16px;
      padding:20px 24px;margin-bottom:24px;">
      <div style="font-family:'Syne',sans-serif;font-size:11px;font-weight:700;
        color:#4d6fa0;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px;">
        Filter Controls
      </div>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns([1, 1.5, 1])
    with fc1:
        selected_date = st.date_input("Select Date", date.today(), key="dash_date")
    with fc2:
        all_teams_list = get_all_teams()
        filter_team = st.multiselect("Filter Teams", ["All"] + all_teams_list, default=["All"], key="dash_teams")
    with fc3:
        st.write("")
        run = st.button("⚡  Run Compliance Check", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if run:
        teams_data    = load_teams()
        all_usernames = list({u for t in teams_data.get("teams", []) for u in t.get("members", [])})

        if not all_usernames:
            st.warning("No members found. Add members in Team Management first.")
        else:
            with st.spinner("Fetching contributions…"):
                records_by_user = {u: fetch_user_audio_contributions(api_token, u) for u in all_usernames}

            results = []
            for team in teams_data.get("teams", []):
                slots     = get_team_slot_compliance(team.get("members", []), records_by_user, selected_date)
                submitted = sum(1 for v in slots.values() if v == "submitted")
                late      = sum(1 for v in slots.values() if v == "late")
                missing   = len(REQUIRED_SESSIONS) - submitted - late
                results.append({
                    "team_name": team["name"], **slots,
                    "submitted": submitted, "late": late, "missing": missing,
                    "completion": (submitted / len(REQUIRED_SESSIONS)) * 100,
                })

            df = pd.DataFrame(results)
            if "All" not in filter_team:
                df = df[df["team_name"].isin(filter_team)]

            if df.empty:
                st.info("No matching teams.")
            else:
                session_cols = ["morning_standup", "morning_recap", "afternoon_standup", "afternoon_recap"]
                tot_sub   = int((df[session_cols] == "submitted").sum().sum())
                tot_late  = int((df[session_cols] == "late").sum().sum())
                tot_miss  = int((df[session_cols] == "missing").sum().sum())
                avg_pct   = df["completion"].mean()
                n_perfect = int((df["completion"] == 100).sum())

                # KPI Strip
                kpis = [
                    ("⚡", "Teams",         str(len(df)),       "#3b82f6", "rgba(59,130,246,0.12)",  "rgba(59,130,246,0.25)"),
                    ("✅", "Submitted",     str(tot_sub),       "#10b981", "rgba(16,185,129,0.12)",  "rgba(16,185,129,0.25)"),
                    ("⚠️", "Late",          str(tot_late),      "#f59e0b", "rgba(245,158,11,0.12)",  "rgba(245,158,11,0.25)"),
                    ("❌", "Missing",       str(tot_miss),      "#ef4444", "rgba(239,68,68,0.12)",   "rgba(239,68,68,0.25)"),
                    ("🏆", "Perfect Teams", str(n_perfect),     "#8b5cf6", "rgba(139,92,246,0.12)",  "rgba(139,92,246,0.25)"),
                    ("📊", "Avg Complete",  f"{avg_pct:.0f}%",  "#f59e0b", "rgba(245,158,11,0.12)",  "rgba(245,158,11,0.25)"),
                ]
                cols = st.columns(6)
                for col, (icon, label, val, clr, bg, brd) in zip(cols, kpis):
                    col.markdown(f"""
                    <div style="background:{bg};border:1px solid {brd};border-radius:14px;
                      padding:18px 16px;text-align:center;transition:all 0.2s;">
                      <div style="font-size:22px;margin-bottom:6px;">{icon}</div>
                      <div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
                        color:{clr};line-height:1;">{val}</div>
                      <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:6px;
                        text-transform:uppercase;letter-spacing:1px;font-weight:700;">{label}</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Compliance Table
                st.markdown("""
                <div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
                  color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px;">
                  ◈ Team Compliance Matrix
                </div>""", unsafe_allow_html=True)

                def badge(val):
                    if val == "submitted":
                        return '<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(16,185,129,0.15);border:1px solid rgba(16,185,129,0.3);color:#34d399;border-radius:20px;padding:4px 12px;font-size:11px;font-weight:700;font-family:\'JetBrains Mono\',monospace;letter-spacing:0.3px;">✓ ON TIME</span>'
                    elif val == "late":
                        return '<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(245,158,11,0.15);border:1px solid rgba(245,158,11,0.3);color:#fbbf24;border-radius:20px;padding:4px 12px;font-size:11px;font-weight:700;font-family:\'JetBrains Mono\',monospace;letter-spacing:0.3px;">⚡ LATE</span>'
                    return '<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.25);color:#f87171;border-radius:20px;padding:4px 12px;font-size:11px;font-weight:700;font-family:\'JetBrains Mono\',monospace;letter-spacing:0.3px;">✕ MISSING</span>'

                def pbar(pct):
                    if pct >= 100:   fill = "linear-gradient(90deg,#059669,#10b981)"
                    elif pct >= 50:  fill = "linear-gradient(90deg,#b45309,#f59e0b)"
                    else:            fill = "linear-gradient(90deg,#b91c1c,#ef4444)"
                    return f'''<div style="background:rgba(255,255,255,0.06);border-radius:100px;height:28px;overflow:hidden;min-width:130px;position:relative;">
                      <div style="width:{pct:.0f}%;height:100%;background:{fill};border-radius:100px;display:flex;align-items:center;justify-content:flex-end;padding-right:10px;">
                        <span style="font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:700;color:white;">{pct:.0f}%</span>
                      </div>
                    </div>'''

                session_labels = ["Morning Standup", "Morning Recap", "Afternoon Standup", "Afternoon Recap"]
                th_style = "padding:12px 16px;font-family:'Syne',sans-serif;font-size:10px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#4d6fa0;text-align:center;border-bottom:1px solid rgba(255,255,255,0.06);"
                th_first = th_style.replace("text-align:center", "text-align:left")

                thead = f'<tr><th style="{th_first}">Team</th>'
                for lbl in session_labels:
                    thead += f'<th style="{th_style}">{lbl}</th>'
                thead += f'<th style="{th_style}">Completion</th></tr>'

                tbody = ""
                for idx, (_, row) in enumerate(df.iterrows()):
                    bg  = "rgba(255,255,255,0.015)" if idx % 2 else "transparent"
                    pct = row["completion"]
                    td_base = "padding:12px 16px;border-bottom:1px solid rgba(255,255,255,0.04);text-align:center;vertical-align:middle;"
                    tbody += f'<tr style="background:{bg};transition:background 0.15s;" onmouseover="this.style.background=\'rgba(59,130,246,0.05)\'" onmouseout="this.style.background=\'{bg}\'">'
                    tbody += f'<td style="{td_base}text-align:left;"><div style="font-family:\'Syne\',sans-serif;font-weight:800;font-size:14px;color:#e8edf8;">{row["team_name"]}</div></td>'
                    for col in session_cols:
                        tbody += f'<td style="{td_base}">{badge(row[col])}</td>'
                    tbody += f'<td style="{td_base}">{pbar(pct)}</td>'
                    tbody += "</tr>"

                st.markdown(f"""
                <div style="overflow-x:auto;background:linear-gradient(135deg,#0d1629,#111d35);
                  border:1px solid rgba(255,255,255,0.08);border-radius:16px;overflow:hidden;">
                  <table style="width:100%;border-collapse:collapse;font-family:'Nunito',sans-serif;">
                    <thead style="background:rgba(255,255,255,0.03);">{thead}</thead>
                    <tbody>{tbody}</tbody>
                  </table>
                </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Bar Chart
                st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
                  color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:12px;">
                  ◈ Session Status Overview</div>""", unsafe_allow_html=True)

                fig = go.Figure()
                names = df["team_name"].tolist()
                fig.add_trace(go.Bar(name="✅ On Time", x=names, y=df["submitted"].tolist(),
                    marker=dict(color="#10b981", line=dict(width=0)), marker_cornerradius=6))
                fig.add_trace(go.Bar(name="⚡ Late", x=names, y=df["late"].tolist(),
                    marker=dict(color="#f59e0b", line=dict(width=0)), marker_cornerradius=6))
                fig.add_trace(go.Bar(name="✕ Missing", x=names, y=df["missing"].tolist(),
                    marker=dict(color="#ef4444", line=dict(width=0)), marker_cornerradius=6))
                fig.update_layout(
                    barmode="group", height=320,
                    plot_bgcolor="rgba(13,22,41,0.8)", paper_bgcolor="rgba(13,22,41,0.0)",
                    font=dict(family="JetBrains Mono", size=11, color="#8899bb"),
                    legend=dict(orientation="h", y=1.15, x=0, font=dict(size=11, color="#8899bb"), bgcolor="rgba(0,0,0,0)"),
                    margin=dict(l=0, r=0, t=40, b=0),
                    xaxis=dict(showgrid=False, tickfont=dict(size=12, color="#8899bb"), linecolor="rgba(255,255,255,0.06)"),
                    yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", tickfont=dict(size=11, color="#556080"), zeroline=False, title="Sessions"),
                )
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
with tab_analytics:
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0d1629,#111d35);
      border:1px solid rgba(255,255,255,0.08);border-radius:16px;
      padding:20px 24px;margin-bottom:24px;">
      <div style="font-family:'Syne',sans-serif;font-size:11px;font-weight:700;
        color:#4d6fa0;letter-spacing:1px;text-transform:uppercase;margin-bottom:14px;">
        Analytics Filters
      </div>
    """, unsafe_allow_html=True)

    ac1, ac2, ac3 = st.columns([1, 1.5, 1])
    with ac1:
        period = st.selectbox("Time Period", ["Last 7 days", "Last 30 days", "Last 3 months", "Last 6 months"], index=1)
    with ac2:
        all_teams_list2 = get_all_teams()
        analytics_teams = st.multiselect("Teams", ["All"] + all_teams_list2, default=["All"], key="an_teams")
    with ac3:
        st.write("")
        run_an = st.button("📊  Load Analytics", type="primary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if run_an:
        days_map = {"Last 7 days": 7, "Last 30 days": 30, "Last 3 months": 90, "Last 6 months": 180}
        days     = days_map[period]
        today    = date.today()
        start_dt = today - timedelta(days=days)
        IST      = timezone(timedelta(hours=5, minutes=30))

        teams_data    = load_teams()
        teams_to_show = teams_data.get("teams", [])
        if "All" not in analytics_teams:
            teams_to_show = [t for t in teams_to_show if t["name"] in analytics_teams]

        all_members    = list({u for t in teams_to_show for u in t.get("members", [])})
        member_to_team = {u: t["name"] for t in teams_to_show for u in t.get("members", [])}

        if not all_members:
            st.warning("No members found.")
        else:
            with st.spinner("Loading analytics data…"):
                records_by_user = {u: fetch_user_audio_contributions(api_token, u) for u in all_members}

            rows = []
            submitted_w = [(9.0, 9.5), (12.0, 12.5), (13.5, 14.0), (16.5, 17.0)]
            late_w      = [(9.5, 10.5), (12.5, 13.5), (14.0, 15.0), (17.0, 24.0)]

            def classify_h(h):
                for s, e in submitted_w:
                    if s <= h < e: return "submitted"
                for s, e in late_w:
                    if s <= h < e: return "late"
                return "other"

            for uid, records in records_by_user.items():
                for r in records:
                    ts = r.get("timestamp")
                    if isinstance(ts, datetime):
                        if ts.tzinfo is None: ts = ts.replace(tzinfo=timezone.utc)
                        ts_ist   = ts.astimezone(IST)
                        rec_date = ts_ist.date()
                        if start_dt <= rec_date <= today:
                            h = ts_ist.hour + ts_ist.minute / 60
                            rows.append({
                                "user":     uid,
                                "team":     member_to_team.get(uid, "Unassigned"),
                                "date":     rec_date,
                                "hour":     h,
                                "hour_int": int(h),
                                "status":   classify_h(h),
                            })

            if not rows:
                st.info("No audio uploads found for the selected period.")
            else:
                df_all = pd.DataFrame(rows)
                total  = len(df_all)
                n_sub  = int((df_all["status"] == "submitted").sum())
                n_late = int((df_all["status"] == "late").sum())
                n_oth  = total - n_sub - n_late
                active = df_all["user"].nunique()

                kpis2 = [
                    ("🎙️", "Total Uploads",  str(total),                                    "#3b82f6", "rgba(59,130,246,0.12)",  "rgba(59,130,246,0.25)"),
                    ("✅", "On Time",        str(n_sub),                                    "#10b981", "rgba(16,185,129,0.12)",  "rgba(16,185,129,0.25)"),
                    ("⚡", "Late",           str(n_late),                                   "#f59e0b", "rgba(245,158,11,0.12)",  "rgba(245,158,11,0.25)"),
                    ("🕐", "Outside Window", str(n_oth),                                    "#ef4444", "rgba(239,68,68,0.12)",   "rgba(239,68,68,0.25)"),
                    ("👥", "Active Members", str(active),                                   "#8b5cf6", "rgba(139,92,246,0.12)",  "rgba(139,92,246,0.25)"),
                    ("📈", "On-Time Rate",   f"{n_sub/total*100:.1f}%" if total else "0%",  "#10b981", "rgba(16,185,129,0.12)",  "rgba(16,185,129,0.25)"),
                ]
                cols2 = st.columns(6)
                for col, (icon, label, val, clr, bg, brd) in zip(cols2, kpis2):
                    col.markdown(f"""
                    <div style="background:{bg};border:1px solid {brd};border-radius:14px;
                      padding:18px 16px;text-align:center;">
                      <div style="font-size:22px;margin-bottom:6px;">{icon}</div>
                      <div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
                        color:{clr};line-height:1;">{val}</div>
                      <div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:6px;
                        text-transform:uppercase;letter-spacing:1px;font-weight:700;">{label}</div>
                    </div>""", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Row 1: Daily trend + Donut
                r1c1, r1c2 = st.columns([2, 1])
                with r1c1:
                    st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
                      color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">
                      ◈ Daily Upload Trend</div>""", unsafe_allow_html=True)

                    daily = df_all.groupby(["date", "status"]).size().reset_index(name="cnt")
                    dpiv  = daily.pivot_table(index="date", columns="status", values="cnt", fill_value=0).reset_index()
                    for c in ["submitted", "late", "other"]:
                        if c not in dpiv.columns: dpiv[c] = 0

                    fig_d = go.Figure()
                    fig_d.add_trace(go.Scatter(x=dpiv["date"], y=dpiv["submitted"], name="✅ On Time",
                        fill="tozeroy", line=dict(color="#10b981", width=2.5),
                        fillcolor="rgba(16,185,129,0.12)", mode="lines+markers",
                        marker=dict(size=5, color="#10b981")))
                    fig_d.add_trace(go.Scatter(x=dpiv["date"], y=dpiv["late"], name="⚡ Late",
                        fill="tozeroy", line=dict(color="#f59e0b", width=2.5),
                        fillcolor="rgba(245,158,11,0.08)", mode="lines+markers",
                        marker=dict(size=5, color="#f59e0b")))
                    fig_d.update_layout(
                        height=280, plot_bgcolor="rgba(13,22,41,0.0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="JetBrains Mono", size=11, color="#8899bb"),
                        legend=dict(orientation="h", y=1.2, x=0, bgcolor="rgba(0,0,0,0)"),
                        margin=dict(l=0, r=0, t=40, b=0),
                        xaxis=dict(showgrid=False, linecolor="rgba(255,255,255,0.05)"),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False),
                    )
                    st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})

                with r1c2:
                    st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
                      color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">
                      ◈ Status Split</div>""", unsafe_allow_html=True)

                    fig_pie = go.Figure(go.Pie(
                        labels=["On Time", "Late", "Other"],
                        values=[n_sub, n_late, n_oth],
                        marker=dict(colors=["#10b981", "#f59e0b", "#475569"],
                                    line=dict(color="#070d1a", width=3)),
                        hole=0.62,
                        textfont=dict(family="JetBrains Mono", size=11),
                        textinfo="percent",
                        hovertemplate="<b>%{label}</b><br>%{value} uploads<br>%{percent}<extra></extra>",
                    ))
                    fig_pie.add_annotation(text=f"<b>{total}</b><br>total", x=0.5, y=0.5,
                        font=dict(size=16, color="#e8edf8", family="Syne"), showarrow=False)
                    fig_pie.update_layout(
                        height=280, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="JetBrains Mono", size=11, color="#8899bb"),
                        legend=dict(orientation="h", y=-0.15, x=0.1, bgcolor="rgba(0,0,0,0)"),
                        margin=dict(l=0, r=0, t=10, b=0),
                        showlegend=True,
                    )
                    st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

                st.markdown("<br>", unsafe_allow_html=True)

                # Row 2: Hour heatmap + Per-team
                r2c1, r2c2 = st.columns([1, 1])
                with r2c1:
                    st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
                      color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">
                      ◈ Upload Hour Distribution (IST)</div>""", unsafe_allow_html=True)

                    hc     = df_all.groupby("hour_int").size().reset_index(name="cnt")
                    all_h  = pd.DataFrame({"hour_int": range(0, 24)})
                    hc     = all_h.merge(hc, on="hour_int", how="left").fillna(0)

                    def hclr(h):
                        for s, e in [(9, 9), (12, 12), (13, 13), (16, 16)]:
                            if s <= h <= e: return "#10b981"
                        for s, e in [(9, 10), (12, 13), (14, 14), (17, 23)]:
                            if s <= h <= e: return "#f59e0b"
                        return "#2d3f5e"

                    colors = [hclr(h) for h in hc["hour_int"]]
                    fig_h  = go.Figure(go.Bar(
                        x=[f"{h:02d}h" for h in hc["hour_int"]],
                        y=hc["cnt"], marker_color=colors,
                        marker_line_width=0, marker_cornerradius=4,
                    ))
                    fig_h.update_layout(
                        height=260, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="JetBrains Mono", size=10, color="#556080"),
                        margin=dict(l=0, r=0, t=10, b=0),
                        xaxis=dict(showgrid=False, tickangle=-45, linecolor="rgba(255,255,255,0.05)"),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False),
                    )
                    st.plotly_chart(fig_h, use_container_width=True, config={"displayModeBar": False})
                    st.markdown("""<div style="font-size:11px;color:#556080;font-family:'JetBrains Mono',monospace;margin-top:-12px;">
                      🟢 On-time windows &nbsp;·&nbsp; 🟡 Late windows &nbsp;·&nbsp; ⚫ Outside all windows</div>""", unsafe_allow_html=True)

                with r2c2:
                    st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
                      color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;">
                      ◈ Uploads per Team</div>""", unsafe_allow_html=True)

                    ts_grp = df_all.groupby(["team", "status"]).size().reset_index(name="cnt")
                    tp     = ts_grp.pivot_table(index="team", columns="status", values="cnt", fill_value=0).reset_index()
                    for c in ["submitted", "late", "other"]:
                        if c not in tp.columns: tp[c] = 0

                    fig_t = go.Figure()
                    fig_t.add_trace(go.Bar(name="✅ On Time", x=tp["team"], y=tp["submitted"],
                        marker=dict(color="#10b981", line=dict(width=0)), marker_cornerradius=4))
                    fig_t.add_trace(go.Bar(name="⚡ Late", x=tp["team"], y=tp["late"],
                        marker=dict(color="#f59e0b", line=dict(width=0)), marker_cornerradius=4))
                    fig_t.add_trace(go.Bar(name="✕ Other", x=tp["team"], y=tp["other"],
                        marker=dict(color="#475569", line=dict(width=0)), marker_cornerradius=4))
                    fig_t.update_layout(
                        barmode="stack", height=260,
                        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="JetBrains Mono", size=10, color="#556080"),
                        legend=dict(orientation="h", y=1.2, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
                        margin=dict(l=0, r=0, t=40, b=0),
                        xaxis=dict(showgrid=False),
                        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)", zeroline=False),
                    )
                    st.plotly_chart(fig_t, use_container_width=True, config={"displayModeBar": False})

                # Member Activity Heatmap
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown("""<div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
                  color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:4px;">
                  ◈ Member Activity Heatmap</div>
                  <div style="font-size:12px;color:#556080;font-family:'JetBrains Mono',monospace;
                  margin-bottom:14px;">audio uploads per person · per day · grouped by team</div>
                """, unsafe_allow_html=True)

                unique_teams = sorted(df_all["team"].unique().tolist())
                hm_team      = st.selectbox(
                    "Select team to view heatmap",
                    options=["All Teams"] + unique_teams,
                    key="hm_team_sel",
                    label_visibility="collapsed",
                )

                hm_df = df_all.copy() if hm_team == "All Teams" else df_all[df_all["team"] == hm_team].copy()

                if hm_df.empty:
                    st.info("No data for this team in the selected period.")
                else:
                    uid_to_name = {}
                    for uid in hm_df["user"].unique():
                        ud   = fetch_user_by_id(api_token, uid) if api_token else {}
                        name = ud.get("name") or ud.get("full_name") or ud.get("username") or uid
                        uid_to_name[uid] = name

                    hm_df["member"] = hm_df["user"].map(uid_to_name)

                    hm_pivot       = hm_df.groupby(["member", "date"]).size().reset_index(name="uploads")
                    all_dates      = sorted(hm_df["date"].unique())
                    all_members_hm = sorted(hm_df["member"].unique())

                    full_idx = pd.MultiIndex.from_product([all_members_hm, all_dates], names=["member", "date"])
                    hm_full  = (
                        hm_pivot.set_index(["member", "date"])
                        .reindex(full_idx, fill_value=0)
                        .reset_index()
                    )
                    matrix = hm_full.pivot(index="member", columns="date", values="uploads")

                    hover_text = []
                    for mem in matrix.index:
                        row_hover = []
                        for d in matrix.columns:
                            cnt = int(matrix.loc[mem, d])
                            sb  = hm_df[(hm_df["member"] == mem) & (hm_df["date"] == d)]["status"].value_counts().to_dict()
                            row_hover.append(
                                f"<b>{mem}</b><br>📅 {d}<br>🎙️ Total: {cnt}<br>"
                                f"✅ On-time: {sb.get('submitted',0)}  ⚡ Late: {sb.get('late',0)}  🕐 Other: {sb.get('other',0)}"
                            )
                        hover_text.append(row_hover)

                    date_labels = [str(d) for d in matrix.columns]
                    cell_h      = max(36, min(56, 400 // max(len(all_members_hm), 1)))
                    fig_hm_h    = max(300, len(all_members_hm) * cell_h + 120)

                    fig_hm = go.Figure(go.Heatmap(
                        z=matrix.values.tolist(),
                        x=date_labels,
                        y=matrix.index.tolist(),
                        text=hover_text,
                        hovertemplate="%{text}<extra></extra>",
                        colorscale=[
                            [0.0,  "rgba(13,22,41,1)"],
                            [0.01, "rgba(21,36,70,1)"],
                            [0.25, "rgba(29,78,216,0.6)"],
                            [0.5,  "rgba(16,185,129,0.75)"],
                            [0.75, "rgba(245,158,11,0.85)"],
                            [1.0,  "rgba(239,68,68,1)"],
                        ],
                        showscale=True,
                        colorbar=dict(
                            title=dict(text="Uploads", font=dict(size=11, color="#8899bb", family="JetBrains Mono")),
                            tickfont=dict(size=10, color="#8899bb", family="JetBrains Mono"),
                            bgcolor="rgba(0,0,0,0)",
                            outlinecolor="rgba(255,255,255,0.08)",
                            outlinewidth=1,
                            thickness=12, len=0.8,
                        ),
                        xgap=3, ygap=3,
                    ))
                    fig_hm.update_layout(
                        height=fig_hm_h,
                        plot_bgcolor="rgba(7,13,26,1)", paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="JetBrains Mono", size=11, color="#8899bb"),
                        margin=dict(l=0, r=60, t=20, b=60),
                        xaxis=dict(showgrid=False, tickangle=-45, tickfont=dict(size=10, color="#556080"),
                                   linecolor="rgba(255,255,255,0.05)",
                                   title=dict(text="Date", font=dict(size=11, color="#4d6fa0"))),
                        yaxis=dict(showgrid=False, tickfont=dict(size=11, color="#8899bb"),
                                   autorange="reversed",
                                   title=dict(text="Member", font=dict(size=11, color="#4d6fa0"))),
                    )
                    st.plotly_chart(fig_hm, use_container_width=True, config={"displayModeBar": False})

                    st.markdown("""
                    <div style="display:flex;gap:20px;align-items:center;margin-top:-8px;flex-wrap:wrap;">
                      <div style="font-family:'JetBrains Mono',monospace;font-size:11px;color:#556080;">Color scale:</div>
                      <div style="display:flex;align-items:center;gap:6px;">
                        <div style="width:14px;height:14px;border-radius:3px;background:rgba(13,22,41,1);border:1px solid rgba(255,255,255,0.1);"></div>
                        <span style="font-size:11px;color:#556080;font-family:'JetBrains Mono',monospace;">0 uploads</span>
                      </div>
                      <div style="display:flex;align-items:center;gap:6px;">
                        <div style="width:14px;height:14px;border-radius:3px;background:rgba(29,78,216,0.7);"></div>
                        <span style="font-size:11px;color:#556080;font-family:'JetBrains Mono',monospace;">low</span>
                      </div>
                      <div style="display:flex;align-items:center;gap:6px;">
                        <div style="width:14px;height:14px;border-radius:3px;background:rgba(16,185,129,0.8);"></div>
                        <span style="font-size:11px;color:#556080;font-family:'JetBrains Mono',monospace;">medium</span>
                      </div>
                      <div style="display:flex;align-items:center;gap:6px;">
                        <div style="width:14px;height:14px;border-radius:3px;background:rgba(245,158,11,0.9);"></div>
                        <span style="font-size:11px;color:#556080;font-family:'JetBrains Mono',monospace;">high</span>
                      </div>
                      <div style="display:flex;align-items:center;gap:6px;">
                        <div style="width:14px;height:14px;border-radius:3px;background:rgba(239,68,68,1);"></div>
                        <span style="font-size:11px;color:#556080;font-family:'JetBrains Mono',monospace;">very high</span>
                      </div>
                    </div>
                    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
#  TEAM MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════════
with tab_teams:
    left, right = st.columns([1, 1.5], gap="large")

    with left:
        # Create team card
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0d1629,#111d35);
          border:1px solid rgba(255,255,255,0.08);border-radius:16px;
          padding:22px;margin-bottom:20px;">
          <div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
            color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px;">
            ◈ Create New Team
          </div>
        """, unsafe_allow_html=True)

        nt = st.text_input("Team name", placeholder="e.g. Alpha Squad", key="new_team", label_visibility="collapsed")
        if st.button("＋  Create Team", type="primary", use_container_width=True):
            td = load_teams()
            if nt.strip() and nt.strip() not in [t["name"] for t in td["teams"]]:
                td["teams"].append({"name": nt.strip(), "members": []})
                save_teams(td)
                st.success(f"Team **{nt.strip()}** created!")
                st.rerun()
            elif not nt.strip():
                st.warning("Enter a team name.")
            else:
                st.warning("Team already exists.")
        st.markdown("</div>", unsafe_allow_html=True)

        # Search + Add member card
        st.markdown("""
        <div style="background:linear-gradient(135deg,#0d1629,#111d35);
          border:1px solid rgba(255,255,255,0.08);border-radius:16px;
          padding:22px;">
          <div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
            color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:14px;">
            ◈ Add Member
          </div>
        """, unsafe_allow_html=True)

        try:
            from streamlit_searchbox import st_searchbox

            def _sfn(query: str):
                if not query or not query.strip() or not api_token: return []
                raw    = search_users(api_token, query.strip())
                labels, rmap = [], {}
                for u in raw:
                    uname   = u.get("username") or u.get("id") or ""
                    display = u.get("name") or u.get("full_name") or uname
                    lbl     = f"{display} (@{uname})" if display and display != uname else uname
                    if lbl and lbl not in rmap:
                        labels.append(lbl)
                        rmap[lbl] = u
                st.session_state["_rmap"] = rmap
                return labels

            sel_lbl = st_searchbox(_sfn, key="sb",
                placeholder="Type name or username…",
                label="Search user", clear_on_submit=False, debounce=350)

            if sel_lbl:
                import re
                rmap    = st.session_state.get("_rmap", {})
                matched = rmap.get(sel_lbl, {})
                m_re    = re.search(r"@(\w+)", sel_lbl)
                uguess  = matched.get("username") or (m_re.group(1) if m_re else sel_lbl.strip())
                idguess = matched.get("id") or uguess
                if idguess != st.session_state.get("_last_sb", ""):
                    st.session_state["_last_sb"] = idguess
                    with st.spinner("Fetching profile…"):
                        f = fetch_user_by_id(api_token, idguess)
                    if f:
                        if not f.get("id"): f["id"] = idguess
                        st.session_state["sel_user"] = f
                    else:
                        st.error("Could not fetch profile.")

        except ImportError:
            st.caption("Install `streamlit-searchbox` for typeahead")
            uq = st.text_input("Search", placeholder="Type name or username…", key="uq_input", label_visibility="collapsed")
            if uq and uq.strip() and uq.strip() != st.session_state.get("_lq", ""):
                st.session_state["_lq"] = uq.strip()
                st.session_state.pop("_ls", "")
                with st.spinner("Searching…"):
                    st.session_state["_sr"] = search_users(api_token, uq.strip()) or []
            sr = st.session_state.get("_sr", [])
            if sr and uq and uq.strip():
                opts = {}
                for u in sr:
                    un   = u.get("username") or u.get("id") or ""
                    disp = u.get("name") or u.get("full_name") or un
                    lbl  = f"{disp} (@{un})" if disp != un else un
                    if un and lbl not in opts: opts[lbl] = u.get("id") or un
                if opts:
                    sl  = st.radio("", list(opts.keys()), key="u_radio", horizontal=True, label_visibility="collapsed")
                    sid = opts.get(sl, "")
                    if sid and sid != st.session_state.get("_ls", ""):
                        st.session_state["_ls"] = sid
                        with st.spinner(): f = fetch_user_by_id(api_token, sid)
                        if f:
                            if not f.get("id"): f["id"] = sid
                            st.session_state["sel_user"] = f

        # Selected user display
        if st.session_state.get("sel_user"):
            u   = st.session_state["sel_user"]
            uid = u.get("id", "")
            unm = u.get("name") or u.get("full_name") or u.get("username") or uid
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);
              border-radius:12px;padding:14px 16px;margin:12px 0;display:flex;align-items:center;gap:14px;">
              <div style="width:42px;height:42px;background:linear-gradient(135deg,#059669,#10b981);
                border-radius:50%;display:flex;align-items:center;justify-content:center;
                font-size:18px;flex-shrink:0;">👤</div>
              <div>
                <div style="font-family:'Syne',sans-serif;font-weight:800;font-size:15px;
                  color:#34d399;line-height:1;">{unm}</div>
                <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                  color:#2d6e4e;margin-top:4px;">{uid}</div>
              </div>
              <div style="margin-left:auto;background:rgba(16,185,129,0.15);border-radius:6px;
                padding:4px 10px;font-size:11px;color:#34d399;font-weight:700;">SELECTED</div>
            </div>
            """, unsafe_allow_html=True)

            ex_teams = [t["name"] for t in load_teams().get("teams", [])]
            if ex_teams:
                ta1, ta2 = st.columns([2, 1])
                with ta1:
                    sel_t = st.selectbox("Assign to", ex_teams, key=f"at_{uid}", label_visibility="collapsed")
                with ta2:
                    if st.button("➕  Add", key=f"add_{uid}", use_container_width=True):
                        _td = load_teams()
                        for _t in _td["teams"]:
                            if _t["name"] == sel_t:
                                if uid not in _t["members"]:
                                    _t["members"].append(uid)
                                    save_teams(_td)
                                    st.success(f"Added to **{sel_t}**!")
                                    st.rerun()
                                else:
                                    st.info("Already a member.")
                                break
            else:
                st.info("Create a team first.")

        st.markdown("</div>", unsafe_allow_html=True)

    # Right: Team cards
    with right:
        st.markdown("""
        <div style="font-family:'Syne',sans-serif;font-size:13px;font-weight:700;
          color:#4d6fa0;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:16px;">
          ◈ Your Teams
        </div>""", unsafe_allow_html=True)

        td_all = load_teams()
        if not td_all.get("teams"):
            st.markdown("""
            <div style="background:linear-gradient(135deg,#0d1629,#111d35);
              border:1px dashed rgba(255,255,255,0.1);border-radius:16px;
              padding:48px;text-align:center;">
              <div style="font-size:40px;margin-bottom:12px;">🏗️</div>
              <div style="font-family:'Syne',sans-serif;font-size:16px;font-weight:700;
                color:#4d6fa0;">No teams yet</div>
              <div style="font-size:13px;color:#2d3f5e;margin-top:6px;">
                Create your first team using the panel on the left
              </div>
            </div>""", unsafe_allow_html=True)
        else:
            for i, team in enumerate(td_all["teams"]):
                members = team.get("members", [])
                mc      = len(members)

                with st.expander(
                    f"{'🟢' if mc > 0 else '⚫'}  {team['name']}  ·  {mc} member{'s' if mc != 1 else ''}",
                    expanded=(i == 0 and mc > 0),
                ):
                    hc1, hc2 = st.columns([3, 1])
                    with hc2:
                        if st.button("🗑️  Delete", key=f"del_{i}",
                            help="Delete this team permanently", use_container_width=True):
                            delete_team(team["name"])
                            st.rerun()

                    if members:
                        st.markdown(f"""
                        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                          color:#556080;letter-spacing:1px;text-transform:uppercase;
                          margin-bottom:10px;">{mc} MEMBER{'S' if mc != 1 else ''}</div>
                        """, unsafe_allow_html=True)

                        to_remove = []
                        for mid in members:
                            ud  = fetch_user_by_id(api_token, mid) if api_token else {}
                            mn  = ud.get("name") or ud.get("full_name") or ud.get("username") or f"@{mid}"
                            mc1, mc2 = st.columns([5, 1])
                            with mc1:
                                st.markdown(f"""
                                <div style="display:flex;align-items:center;gap:12px;
                                  background:rgba(255,255,255,0.03);
                                  border:1px solid rgba(255,255,255,0.06);
                                  border-radius:10px;padding:10px 14px;margin-bottom:6px;">
                                  <div style="width:34px;height:34px;background:linear-gradient(135deg,#1e3a8a,#3b82f6);
                                    border-radius:50%;display:flex;align-items:center;justify-content:center;
                                    font-size:14px;flex-shrink:0;">👤</div>
                                  <div>
                                    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:13px;
                                      color:#e8edf8;">{mn}</div>
                                    <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                                      color:#556080;margin-top:2px;">{mid}</div>
                                  </div>
                                </div>""", unsafe_allow_html=True)
                            with mc2:
                                st.write("")
                                if st.button("✕", key=f"rm_{i}_{mid}", help=f"Remove {mn}"):
                                    to_remove.append(mid)

                        if to_remove:
                            _td2 = load_teams()
                            for _t in _td2["teams"]:
                                if _t["name"] == team["name"]:
                                    _t["members"] = [m for m in _t["members"] if m not in to_remove]
                                    break
                            save_teams(_td2)
                            st.rerun()
                    else:
                        st.markdown("""
                        <div style="text-align:center;padding:20px;color:#2d3f5e;font-size:13px;">
                          No members yet. Search and add from the left panel.
                        </div>""", unsafe_allow_html=True)