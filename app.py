import streamlit as st
import pandas as pd
from datetime import date
from dotenv import load_dotenv
from fetch import fetch_user_by_id, fetch_user_audio_contributions, search_users
from compliance import get_team_slot_compliance, REQUIRED_SESSIONS
from mapping import load_teams, save_teams, update_team_membership, delete_team, get_all_teams
from auth import get_token

load_dotenv()

st.set_page_config(page_title="Standup Tracker | Viswam.Ai", page_icon="🚀", layout="wide")

st.markdown("""
<style>
    .metric-card {
        background: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border: 1px solid #eee; text-align: center;
    }
    .metric-value { font-size: 24px; font-weight: bold; color: #1e3a8a; }
    .metric-label { font-size: 14px; color: #666; }
</style>
""", unsafe_allow_html=True)

# ── Auto-login ────────────────────────────────────────────────────────────────
if "api_token" not in st.session_state:
    try:
        st.session_state["api_token"] = get_token()
    except RuntimeError as e:
        st.error(f"🔐 Auto-login failed: {e}")
        st.info("Set CORPUS_PHONE and CORPUS_PASSWORD in your .env file.")
        st.stop()

api_token: str = st.session_state["api_token"]

st.title("🚀 Team Standup Compliance Tracker")
st.caption("Viswam.Ai - Swecha Corpus Backend Powered")

with st.sidebar:
    st.markdown("### 🕐 Standup Time Slots")
    st.markdown("""
| Session | On-Time | Late |
|:--------|:--------|:-----|
| 🌅 Morning Standup | 09:00 – 10:59 | 11:00 – 11:59 |
| 🔄 Morning Recap | 12:00 – 12:59 | 13:00 – 13:59 |
| ☀️ Afternoon Standup | 14:00 – 15:59 | 16:00 – 16:59 |
| 🔄 Afternoon Recap | 17:00 – 17:59 | 18:00 – 23:59 |
""")
    st.markdown("---")
    st.markdown("""
**Status Legend**
- ✅ **Submitted** — On time
- ⚠️ **Late** — Within late window
- ❌ **Missing** — No submission
""")
    st.markdown("---")
    st.caption("All times are in IST (UTC+5:30)")

tab_dashboard, tab_mgmt = st.tabs(["📊 Compliance Dashboard", "👥 Team Management"])

# ─────────────────────────────────────────────────────────────────────────────
# TEAM MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
with tab_mgmt:
    st.header("Team & Member Setup")
    st.subheader("👤 Add Member")

    # ── Single combined search + autocomplete bar ─────────────────────────────
    try:
        from streamlit_searchbox import st_searchbox

        def _search_fn(query: str):
            """Auto-called as user types. Returns display labels for dropdown."""
            if not query or len(query.strip()) < 1 or not api_token:
                return []
            raw = search_users(api_token, query.strip())
            labels = []
            raw_map = {}
            for u in raw:
                uname = u.get("username") or u.get("id") or ""
                display = u.get("name") or u.get("full_name") or uname
                label = f"{display} (@{uname})" if display and display != uname else uname
                if label and label not in raw_map:
                    labels.append(label)
                    raw_map[label] = u
            st.session_state["_raw_search_map"] = raw_map
            return labels

        selected_label = st_searchbox(
            _search_fn,
            key="user_searchbox",
            placeholder="🔍 Type name or username — results appear automatically…",
            label="Search & Select User",
            clear_on_submit=False,
            debounce=350,
        )

        if selected_label:
            import re
            raw_map = st.session_state.get("_raw_search_map", {})
            matched = raw_map.get(selected_label, {})
            m = re.search(r"@(\w+)", selected_label)
            username_guess = matched.get("username") or (m.group(1) if m else selected_label.strip())
            user_id_guess  = matched.get("id") or username_guess

            prev_sel = st.session_state.get("_last_selected_sb", "")
            if user_id_guess != prev_sel:
                st.session_state["_last_selected_sb"] = user_id_guess
                with st.spinner(f"Fetching profile for @{username_guess}…"):
                    fetched = fetch_user_by_id(api_token, user_id_guess)
                if fetched:
                    if not fetched.get("id"):
                        fetched["id"] = user_id_guess
                    st.session_state["selected_user"] = fetched
                else:
                    st.error("❌ Could not fetch user profile.")

    except ImportError:
        # ── Fallback: single text input, auto-searches on change ─────────────
        st.caption("💡 Install `streamlit-searchbox` for true typeahead: `pip install streamlit-searchbox`")

        user_query = st.text_input(
            "🔍 Search user",
            placeholder="Type name or username — results appear below automatically…",
            key="user_search_input",
        )

        if user_query and user_query.strip():
            prev_query = st.session_state.get("_last_query", "")
            if user_query.strip() != prev_query:
                st.session_state["_last_query"] = user_query.strip()
                st.session_state.pop("_last_selected", None)
                if api_token:
                    with st.spinner("Searching…"):
                        raw_results = search_users(api_token, user_query.strip())
                    st.session_state["search_results"] = raw_results or []

        results = st.session_state.get("search_results", [])
        if results and user_query and user_query.strip():
            user_options = {}
            for u in results:
                uname = u.get("username") or u.get("id") or ""
                display = u.get("name") or u.get("full_name") or uname
                label = f"{display} (@{uname})" if display and display != uname else uname
                if uname and label not in user_options:
                    user_options[label] = u.get("id") or uname

            if user_options:
                selected_label = st.radio(
                    "Select:",
                    options=list(user_options.keys()),
                    key="user_radio",
                    horizontal=True,
                    label_visibility="collapsed",
                )
                selected_id = user_options.get(selected_label, "")
                prev_sel = st.session_state.get("_last_selected", "")
                if selected_id and selected_id != prev_sel:
                    st.session_state["_last_selected"] = selected_id
                    with st.spinner("Fetching profile…"):
                        fetched = fetch_user_by_id(api_token, selected_id)
                    if fetched:
                        if not fetched.get("id"):
                            fetched["id"] = selected_id
                        st.session_state["selected_user"] = fetched
                    else:
                        st.error("❌ Could not fetch user profile.")

    # ── Selected user card + team assignment ──────────────────────────────────
    if st.session_state.get("selected_user"):
        user  = st.session_state["selected_user"]
        uid   = user.get("id", "")
        uname = user.get("name") or user.get("full_name") or user.get("username") or uid

        st.markdown(f"""
        <div style="border:1px solid #22c55e;background:#f0fdf4;border-radius:8px;
                    padding:12px 16px;margin-top:8px;">
            <div style="display:flex;align-items:center;gap:12px;">
                <span style="font-size:28px;">👤</span>
                <div>
                    <div style="font-weight:700;font-size:16px;color:#15803d;">{uname}</div>
                    <div style="font-size:12px;color:#6b7280;">ID: {uid}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        _existing_teams = [t["name"] for t in load_teams().get("teams", [])]
        if _existing_teams:
            _ac1, _ac2 = st.columns([3, 1])
            with _ac1:
                _selected_team = st.selectbox(
                    "Assign to team",
                    options=_existing_teams,
                    key=f"assign_team_{uid}",
                )
            with _ac2:
                st.write("")
                if st.button("➕ Add to Team", key=f"btn_assign_{uid}", use_container_width=True):
                    _td = load_teams()
                    for _t in _td["teams"]:
                        if _t["name"] == _selected_team:
                            if uid not in _t["members"]:
                                _t["members"].append(uid)
                                save_teams(_td)
                                st.success(f"✅ **{uname}** added to **{_selected_team}**!")
                            else:
                                st.info(f"ℹ️ **{uname}** is already in **{_selected_team}**.")
                            break
        else:
            st.info("ℹ️ No teams yet — create one below to assign this user.")

    # ── Team Builder ──────────────────────────────────────────────────────────
    st.divider()
    teams_data = load_teams()

    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        st.subheader("Create Team")
        nt_name = st.text_input("Team Name", key="new_team_name")
        if st.button("➕ Create"):
            if nt_name.strip() and nt_name.strip() not in [t["name"] for t in teams_data["teams"]]:
                teams_data["teams"].append({"name": nt_name.strip(), "members": []})
                save_teams(teams_data)
                st.rerun()
            elif not nt_name.strip():
                st.warning("Enter a team name.")
            else:
                st.warning("Team already exists.")

    with col_t2:
        st.subheader("Existing Teams")
        for i, team in enumerate(teams_data["teams"]):
            member_count = len(team.get("members", []))
            with st.expander(
                f"👥 {team['name']}  ·  {member_count} member{'s' if member_count != 1 else ''}",
                expanded=False,
            ):
                # Delete entire team
                del_col, _ = st.columns([1, 5])
                with del_col:
                    if st.button("🗑️ Delete Team", key=f"del_{i}"):
                        delete_team(team["name"])
                        st.rerun()

                st.divider()

                # Members with individual remove buttons
                if team.get("members"):
                    st.markdown("**Members**")
                    members_to_remove = []
                    for mid in team["members"]:
                        user_data = fetch_user_by_id(api_token, mid) if api_token else {}
                        mname = (
                            user_data.get("name")
                            or user_data.get("full_name")
                            or user_data.get("username")
                            or f"@{mid}"
                        )
                        card_col, btn_col = st.columns([5, 1])
                        with card_col:
                            st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
     border:1px solid #e2e8f0;border-radius:8px;margin-bottom:6px;background:#f8fafc;">
    <span style="font-size:20px;">👤</span>
    <div>
        <div style="font-weight:600;font-size:14px;color:#1e3a8a;">{mname}</div>
        <div style="font-size:11px;color:#6b7280;font-family:monospace;">{mid}</div>
    </div>
</div>""", unsafe_allow_html=True)
                        with btn_col:
                            st.write("")
                            if st.button("❌", key=f"rm_{i}_{mid}", help=f"Remove {mname}"):
                                members_to_remove.append(mid)

                    # Apply removals after rendering all cards
                    if members_to_remove:
                        _td = load_teams()
                        for _t in _td["teams"]:
                            if _t["name"] == team["name"]:
                                _t["members"] = [m for m in _t["members"] if m not in members_to_remove]
                                break
                        save_teams(_td)
                        st.rerun()
                else:
                    st.info("No members yet. Search above and use '➕ Add to Team'.")


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
with tab_dashboard:
    st.header("Team Compliance Report")
    c1, c2, c3 = st.columns([1, 1, 1])
    with c1:
        selected_date = st.date_input("Date", date.today())
    with c2:
        all_created_teams = get_all_teams()
        filter_team = st.multiselect(
            "Filter Teams", options=["All"] + all_created_teams, default=["All"]
        )
    with c3:
        st.write("<br>", unsafe_allow_html=True)
        run = st.button("🚀 Check Compliance", use_container_width=True, type="primary")

    if run:
        teams_data = load_teams()
        all_usernames = list({
            username
            for team in teams_data.get("teams", [])
            for username in team.get("members", [])
        })

        if not all_usernames:
            st.warning("⚠️ No team members found. Add members in the 'Team Management' tab first.")
        else:
            with st.spinner(f"🎙️ Fetching audio contributions for {len(all_usernames)} member(s)..."):
                records_by_user = {
                    uname: fetch_user_audio_contributions(api_token, uname)
                    for uname in all_usernames
                }

            results = []
            for team in teams_data.get("teams", []):
                slots = get_team_slot_compliance(
                    team.get("members", []), records_by_user, selected_date
                )
                completed = sum(1 for v in slots.values() if v == "submitted")
                results.append({
                    "team_name": team["name"],
                    **slots,
                    "completion": (completed / len(REQUIRED_SESSIONS)) * 100,
                })

            if not results:
                st.warning("⚠️ No teams configured.")
            else:
                df_raw = pd.DataFrame(results)
                if "All" not in filter_team:
                    df_raw = df_raw[df_raw["team_name"].isin(filter_team)]

                if df_raw.empty:
                    st.info("No matching teams found.")
                else:
                    session_cols = [
                        "morning_standup", "morning_recap",
                        "afternoon_standup", "afternoon_recap",
                    ]
                    m1, m2, m3 = st.columns(3)
                    total_sub  = (df_raw[session_cols] == "submitted").sum().sum()
                    total_late = (df_raw[session_cols] == "late").sum().sum()
                    avg_pct    = df_raw["completion"].mean()
                    m1.markdown(f'<div class="metric-card"><div class="metric-label">Active Teams</div><div class="metric-value">{len(df_raw)}</div></div>', unsafe_allow_html=True)
                    m2.markdown(f'<div class="metric-card"><div class="metric-label">✅ Submitted / ⚠️ Late</div><div class="metric-value">{total_sub} / {total_late}</div></div>', unsafe_allow_html=True)
                    m3.markdown(f'<div class="metric-card"><div class="metric-label">Avg Completion</div><div class="metric-value">{avg_pct:.1f}%</div></div>', unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)

                    def badge(val: str) -> str:
                        if val == "submitted":
                            return '<span style="background:#d1fae5;color:#065f46;border-radius:6px;padding:3px 10px;font-weight:600;">✅ Submitted</span>'
                        elif val == "late":
                            return '<span style="background:#fef3c7;color:#92400e;border-radius:6px;padding:3px 10px;font-weight:600;">⚠️ Late</span>'
                        else:
                            return '<span style="background:#fee2e2;color:#991b1b;border-radius:6px;padding:3px 10px;font-weight:600;">❌ Missing</span>'

                    def progress_bar(pct: float) -> str:
                        color = "#16a34a" if pct >= 100 else "#ca8a04" if pct >= 50 else "#dc2626"
                        return (
                            f'<div style="background:#e5e7eb;border-radius:6px;overflow:hidden;width:100%;">'
                            f'<div style="width:{pct:.0f}%;background:{color};padding:4px 0;'
                            f'text-align:center;color:white;font-weight:bold;font-size:13px;">'
                            f'{pct:.0f}%</div></div>'
                        )

                    headers = [
                        "Team Name", "Morning Standup", "Morning Recap",
                        "Afternoon Standup", "Afternoon Recap", "Completion %",
                    ]
                    header_html = "".join(
                        f'<th style="padding:10px 14px;background:#1e3a8a;color:white;'
                        f'text-align:center;font-weight:600;">{h}</th>'
                        for h in headers
                    )
                    body_rows = ""
                    for idx, (_, row) in enumerate(df_raw.iterrows()):
                        bg = "#f9fafb" if idx % 2 else "white"
                        body_rows += (
                            f'<tr style="background:{bg};border-bottom:1px solid #e2e8f0;">'
                            f'<td style="padding:10px 14px;font-weight:600;white-space:nowrap;">{row["team_name"]}</td>'
                        )
                        for col in session_cols:
                            body_rows += f'<td style="padding:10px 14px;text-align:center;">{badge(row[col])}</td>'
                        body_rows += f'<td style="padding:10px 14px;min-width:150px;">{progress_bar(row["completion"])}</td></tr>'

                    st.markdown(f"""
                    <div style="overflow-x:auto;border-radius:10px;
                                box-shadow:0 4px 12px rgba(0,0,0,0.08);
                                border:1px solid #e2e8f0;margin-top:8px;">
                    <table style="width:100%;border-collapse:collapse;font-family:sans-serif;font-size:14px;">
                        <thead><tr>{header_html}</tr></thead>
                        <tbody>{body_rows}</tbody>
                    </table></div>
                    """, unsafe_allow_html=True)

                    st.markdown("<br>", unsafe_allow_html=True)
                    with st.expander("🛠️ Raw Record Data"):
                        st.json(results)