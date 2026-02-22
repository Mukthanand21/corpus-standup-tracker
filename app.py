import os
import streamlit as st
import pandas as pd
from datetime import date
from dotenv import load_dotenv
from fetch import fetch_user_by_id, fetch_user_audio_contributions, search_users
from compliance import get_team_slot_compliance, REQUIRED_SESSIONS
from mapping import load_teams, save_teams, update_team_membership, delete_team, get_all_teams

load_dotenv()  # Load .env at app startup

# Page config
st.set_page_config(page_title="Standup Tracker | Viswam.Ai", page_icon="🚀", layout="wide")

# CSS for styling
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

st.title("🚀 Team Standup Compliance Tracker")
st.caption("Viswam.Ai - Swecha Corpus Backend Powered")

# Sidebar
with st.sidebar:
    st.header("🔑 Auth")
    _default_token = os.getenv("CORPUS_ACCESS_TOKEN", "") or os.getenv("API_TOKEN", "")
    api_token = st.text_input("Bearer Token", value=_default_token, type="password")
    st.divider()
    st.info("Assign members locally in the 'Team Management' tab.")

tab_dashboard, tab_mgmt = st.tabs(["📊 Compliance Dashboard", "👥 Team Management"])

# --- TEAM MANAGEMENT ---
with tab_mgmt:
    st.header("Team & Member Setup")
    
    # 1. Search Users by username
    st.subheader("👤 User Management")
    u_id_search = st.text_input("Search User", placeholder="Enter username to search")
    search_clicked = st.button("🔍 Search")
    
    if search_clicked and api_token and u_id_search:
        with st.spinner("Searching users..."):
            # Uses default limit=10
            search_results = search_users(api_token, u_id_search.strip())
        if search_results:
            if 'search_results' not in st.session_state:
                st.session_state['search_results'] = []
            st.session_state['search_results'] = search_results
            st.session_state['selected_user'] = None
        else:
            st.session_state.pop('search_results', None)
            st.session_state.pop('selected_user', None)
            st.warning("No users found matching the query.")
    elif search_clicked and not u_id_search:
        st.warning("Please enter a search query.")

    # Show search results and allow user selection
    if 'search_results' in st.session_state and st.session_state['search_results']:
        st.markdown("**Search Results:**")
        results = st.session_state['search_results']
        
        # Create options for selection
        user_options = {}
        for u in results:
            # Handle different response formats
            username = u.get('username') or u.get('name') or u.get('id', '')
            user_id = u.get('id') or u.get('username') or username
            user_options[user_id] = f"{username}"
        
        selected_user_id = st.selectbox(
            "Select a user to add",
            options=list(user_options.keys()),
            format_func=lambda x: user_options.get(x, x),
            key="user_select"
        )
        
        if selected_user_id:
            # Fetch full user details
            with st.spinner("Fetching user details..."):
                user = fetch_user_by_id(api_token, selected_user_id)
            
            if user:
                if 'fetched_users' not in st.session_state:
                    st.session_state['fetched_users'] = []
                already_added = any(u.get('id') == user.get('id') for u in st.session_state['fetched_users'])
                if not already_added:
                    st.session_state['fetched_users'].append(user)
                st.session_state['selected_user'] = user
                
                # Display selected user
                uid = user.get('id', '')
                uname = user.get('name') or user.get('username') or 'Unknown'
                
                st.markdown(f"""
                <div style="border:1px solid #22c55e;background:#f0fdf4;border-radius:8px;padding:12px 16px;margin-top:6px;">
                    <div style="display:flex;align-items:center;gap:12px;">
                        <span style="font-size:28px;">👤</span>
                        <div>
                            <div style="font-weight:700;font-size:16px;color:#15803d;">{uname}</div>
                            <div style="font-size:12px;color:#6b7280;">ID: {uid}</div>
                            <div style="font-size:12px;color:#16a34a;margin-top:2px;">{'✅ Already in user list' if already_added else '✅ Selected'}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Inline team assignment
                _existing_teams = [t['name'] for t in load_teams().get('teams', [])]
                if _existing_teams:
                    _assign_col1, _assign_col2 = st.columns([3, 1])
                    with _assign_col1:
                        _selected_team = st.selectbox(
                            "Assign to team",
                            options=_existing_teams,
                            key=f"assign_team_{uid}"
                        )
                    with _assign_col2:
                        st.write("")
                        if st.button("➕ Add to Team", key=f"btn_assign_{uid}", use_container_width=True):
                            _td = load_teams()
                            for _t in _td['teams']:
                                if _t['name'] == _selected_team:
                                    if uid not in _t['members']:
                                        _t['members'].append(uid)
                                    break
                            else:
                                _td['teams'].append({'name': _selected_team, 'members': [uid]})
                            from mapping import save_teams
                            save_teams(_td)
                            st.success(f"✅ **{uname}** added to **{_selected_team}**!")
                else:
                    st.info("ℹ️ No teams yet — create one below to assign this user.")
        
        # Show all fetched users
        if st.session_state.get('fetched_users'):
            with st.expander(f"👥 Fetched Users ({len(st.session_state['fetched_users'])})", expanded=True):
                for u in st.session_state['fetched_users']:
                    uname = u.get('name') or u.get('username') or 'Unknown'
                    st.markdown(f"• **{uname}** — `{u.get('id', '')}`")

    # 2. Team Builder
    st.divider()
    teams_data = load_teams()
    
    col_t1, col_t2 = st.columns([1, 2])
    with col_t1:
        st.subheader("Create Team")
        nt_name = st.text_input("Name")
        if st.button("➕ Create"):
            if nt_name and nt_name not in [t['name'] for t in teams_data['teams']]:
                teams_data['teams'].append({"name": nt_name, "members": []})
                save_teams(teams_data)
                st.rerun()

    with col_t2:
        st.subheader("Existing Teams (Editable)")
        for i, team in enumerate(teams_data['teams']):
            member_count = len(team.get('members', []))
            # Build name lookup from fetched_users in session
            fetched_map = {
                u['id']: u.get('name', 'Unknown')
                for u in st.session_state.get('fetched_users', [])
            }

            with st.expander(f"👥 {team['name']}  ·  {member_count} member{'s' if member_count != 1 else ''}", expanded=False):
                # Delete button at top-right
                del_col, _ = st.columns([1, 5])
                with del_col:
                    if st.button("🗑️ Delete Team", key=f"del_{i}"):
                        delete_team(team['name'])
                        st.rerun()

                st.divider()

                # Member detail cards
                if team.get('members'):
                    st.markdown("**Members**")
                    for mid in team['members']:
                        # 1st: try session cache, 2nd: call API to resolve name
                        mname = fetched_map.get(mid)
                        if not mname and api_token:
                            user_data = fetch_user_by_id(api_token, mid)
                            mname = user_data.get('name') or user_data.get('username') or user_data.get('full_name')
                        display_name = mname if mname else f"User {mid[:8]}…"
                        st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:8px 12px;
     border:1px solid #e2e8f0;border-radius:8px;margin-bottom:6px;background:#f8fafc;">
    <span style="font-size:20px;">👤</span>
    <div>
        <div style="font-weight:600;font-size:14px;color:#1e3a8a;">{display_name}</div>
        <div style="font-size:11px;color:#6b7280;font-family:monospace;">{mid}</div>
    </div>
</div>""", unsafe_allow_html=True)
                else:
                    st.info("No members yet. Search for users above and use '➕ Add to Team'.")

                st.divider()

                # Edit membership (only when fetched users are available)
                if 'fetched_users' in st.session_state:
                    user_opts = {u['id']: f"{u.get('name', 'User')} ({u['id'][:6]})" for u in st.session_state['fetched_users']}
                    cur_mem = [m for m in team['members'] if m in user_opts]
                    sel_mem = st.multiselect("Edit members", options=list(user_opts.keys()), default=cur_mem, format_func=lambda x: user_opts[x], key=f"ms_{i}")
                    if st.button("💾 Save Changes", key=f"save_{i}"):
                        update_team_membership(team['name'], sel_mem)
                        st.success("✅ Saved.")


# --- DASHBOARD ---
with tab_dashboard:
    st.header("Team Compliance Report")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        selected_date = st.date_input("Date", date.today())
    with c2:
        all_created_teams = get_all_teams()
        filter_team = st.multiselect("Filter Teams", options=["All"] + all_created_teams, default=["All"])
    with c3:
        st.write("<br>", unsafe_allow_html=True)
        run = st.button("🚀 Check Compliance", use_container_width=True, type="primary")

    if run:
        if not api_token: st.warning("Please enter a Bearer Token.")
        else:
            # Collect all unique usernames across all teams
            teams_data = load_teams()
            all_usernames = list({
                username
                for team in teams_data.get("teams", [])
                for username in team.get("members", [])
            })

            if not all_usernames:
                st.warning("⚠️ No team members found. Add members in the 'Team Management' tab first.")
            else:
                with st.spinner(f"🎙️ Fetching audio contributions for {len(all_usernames)} member(s) (cached 5 min)..."):
                    records_by_user = {}
                    for uname in all_usernames:
                        records_by_user[uname] = fetch_user_audio_contributions(api_token, uname)

                # Build compliance results per team
                results = []
                for team in teams_data.get("teams", []):
                    team_name = team["name"]
                    team_usernames = team.get("members", [])
                    slots = get_team_slot_compliance(
                        team_usernames, records_by_user, selected_date,
                    )
                    completed = sum(1 for v in slots.values() if v == "submitted")
                    results.append({
                        "team_name": team_name,
                        **slots,
                        "completion": (completed / len(REQUIRED_SESSIONS)) * 100,
                    })

                if not results:
                    st.warning("⚠️ No teams configured. Add members in the 'Team Management' tab first.")
                else:
                    df_raw = pd.DataFrame(results)
                    
                    # Selection Filter (on raw data)
                    if "All" not in filter_team:
                        df_raw = df_raw[df_raw["team_name"].isin(filter_team)]
                    
                    if df_raw.empty:
                        st.info("No matching teams found.")
                    else:
                        session_cols = ["morning_standup", "morning_recap", "afternoon_standup", "afternoon_recap"]
                        
                        # Summary metrics
                        m1, m2, m3 = st.columns(3)
                        total_sub = (df_raw[session_cols] == "submitted").sum().sum()
                        total_late = (df_raw[session_cols] == "late").sum().sum()
                        avg_pct = df_raw["completion"].mean()
                        m1.markdown(f'<div class="metric-card"><div class="metric-label">Active Teams</div><div class="metric-value">{len(df_raw)}</div></div>', unsafe_allow_html=True)
                        m2.markdown(f'<div class="metric-card"><div class="metric-label">✅ Submitted / ⚠️ Late</div><div class="metric-value">{total_sub} / {total_late}</div></div>', unsafe_allow_html=True)
                        m3.markdown(f'<div class="metric-card"><div class="metric-label">Avg Completion</div><div class="metric-value">{avg_pct:.1f}%</div></div>', unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)

                        # --- BADGE TABLE ---
                        def badge(val: str) -> str:
                            if val == "submitted":
                                return '<span style="background:#d1fae5;color:#065f46;border-radius:6px;padding:3px 10px;font-weight:600;">✅ Submitted</span>'
                            elif val == "late":
                                return '<span style="background:#fef3c7;color:#92400e;border-radius:6px;padding:3px 10px;font-weight:600;">⚠️ Late</span>'
                            else:
                                return '<span style="background:#fee2e2;color:#991b1b;border-radius:6px;padding:3px 10px;font-weight:600;">❌ Missing</span>'

                        def progress_bar(pct: float) -> str:
                            color = "#16a34a" if pct >= 100 else "#ca8a04" if pct >= 50 else "#dc2626"
                            return f'''<div style="background:#e5e7eb;border-radius:6px;overflow:hidden;width:100%;">
                                <div style="width:{pct:.0f}%;background:{color};padding:4px 0;text-align:center;color:white;font-weight:bold;font-size:13px;">{pct:.0f}%</div>
                            </div>'''

                        # Build HTML table
                        headers = ["Team Name", "Morning Standup", "Morning Recap", "Afternoon Standup", "Afternoon Recap", "Completion %"]
                        rows_html = ""
                        for _, row in df_raw.iterrows():
                            rows_html += "<tr>"
                            rows_html += f'<td style="padding:10px 14px;font-weight:600;white-space:nowrap;">{row["team_name"]}</td>'
                            for col in session_cols:
                                rows_html += f'<td style="padding:10px 14px;text-align:center;">{badge(row[col])}</td>'
                            rows_html += f'<td style="padding:10px 14px;min-width:150px;">{progress_bar(row["completion"])}</td>'
                            rows_html += "</tr>"

                        header_html = "".join(
                            f'<th style="padding:10px 14px;background:#1e3a8a;color:white;text-align:center;font-weight:600;">{h}</th>'
                            for h in headers
                        )

                        html_table = f"""
                        <div style="overflow-x:auto;border-radius:10px;box-shadow:0 4px 12px rgba(0,0,0,0.08);border:1px solid #e2e8f0;margin-top:8px;">
                        <table style="width:100%;border-collapse:collapse;font-family:sans-serif;font-size:14px;">
                            <thead><tr>{header_html}</tr></thead>
                            <tbody>
                            {"".join(f'<tr style="background:{"#f9fafb" if i % 2 else "white"};border-bottom:1px solid #e2e8f0;">{rows_html.split("</tr>")[i].split("<tr>")[1]}</tr>' for i in range(len(df_raw)))}</tbody>
                        </table></div>
                        """
                        st.markdown(html_table, unsafe_allow_html=True)

                        st.markdown("<br>", unsafe_allow_html=True)
                        with st.expander("🛠️ Raw Record Data"):
                            st.json(results)
