import os
import streamlit as st
import pandas as pd
from datetime import date
from dotenv import load_dotenv
from fetch import fetch_records, fetch_users, fetch_categories, fetch_user_by_id
from compliance import calculate_compliance
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
    _default_token = os.getenv("API_TOKEN", "")
    api_token = st.text_input("Bearer Token", value=_default_token, type="password")
    st.divider()
    st.info("Assign members locally in the 'Team Management' tab.")

tab_dashboard, tab_mgmt = st.tabs(["📊 Compliance Dashboard", "👥 Team Management"])

# --- TEAM MANAGEMENT ---
with tab_mgmt:
    st.header("Team & Member Setup")
    
    # API Settings in Expander
    with st.expander("⚙️ API Configuration", expanded=False):
        _default_standup_id = os.getenv("STANDUP_CATEGORY_ID", "")
        _default_internship_id = os.getenv("INTERNSHIP_CATEGORY_ID", "")
        _default_fetch_limit = int(os.getenv("FETCH_LIMIT", "500"))
        st.text_input("Standup Category ID", value=_default_standup_id, key="standup_cat_id")
        st.text_input("Internship Category ID", value=_default_internship_id, key="internship_cat_id")
        st.number_input("Fetch Limit", min_value=10, max_value=2000, value=_default_fetch_limit, key="fetch_limit")
        if st.button("🔍 Find Category IDs"):
            if api_token:
                cats = fetch_categories(api_token)
                st.dataframe(cats)

    # 1. Fetch User by ID
    st.subheader("👤 User Management")
    u_id_search = st.text_input("Search User by UUID", placeholder="e.g. 8d53a79b-ae48-48db-bd28-1aa8557357a3")
    if st.button("🔍 Fetch"):
        if api_token and u_id_search:
            with st.spinner("Looking up user..."):
                user = fetch_user_by_id(api_token, u_id_search.strip())
            if user:
                if 'fetched_users' not in st.session_state:
                    st.session_state['fetched_users'] = []
                already_added = any(u.get('id') == user.get('id') for u in st.session_state['fetched_users'])
                if not already_added:
                    st.session_state['fetched_users'].append(user)
                st.session_state['last_fetched_user'] = user
            else:
                st.session_state.pop('last_fetched_user', None)
                st.error("❌ User not found. Check the UUID and your token.")
        else:
            st.warning("Enter a UUID and make sure your Bearer Token is set in the sidebar.")

    # Show fetched user below search
    if 'last_fetched_user' in st.session_state:
        u = st.session_state['last_fetched_user']
        uid = u.get('id', '')
        already = any(usr.get('id') == uid for usr in st.session_state.get('fetched_users', []))
        st.markdown(f"""
        <div style="border:1px solid #22c55e;background:#f0fdf4;border-radius:8px;padding:12px 16px;margin-top:6px;display:flex;align-items:center;gap:12px;">
            <span style="font-size:28px;">👤</span>
            <div>
                <div style="font-weight:700;font-size:16px;color:#15803d;">{u.get('name', 'Unknown')}</div>
                <div style="font-size:12px;color:#6b7280;">ID: {uid}</div>
                <div style="font-size:12px;color:#16a34a;margin-top:2px;">{'✅ Added to user list' if already else ''}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Show all fetched users
    if st.session_state.get('fetched_users'):
        with st.expander(f"👥 Fetched Users ({len(st.session_state['fetched_users'])})"):
            for u in st.session_state['fetched_users']:
                st.markdown(f"• **{u.get('name', 'Unknown')}** — `{u.get('id', '')}`")

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
            with st.container():
                st.markdown(f'''<div style="border:1px solid #ddd; padding:10px; border-radius:8px; margin-bottom:5px; background:#f9f9f9">''', unsafe_allow_html=True)
                bc1, bc2 = st.columns([4, 1])
                bc1.write(f"**{team['name']}**")
                if bc2.button("🗑️", key=f"del_{i}"):
                    delete_team(team['name'])
                    st.rerun()
                
                if 'fetched_users' in st.session_state:
                    user_opts = {u['id']: f"{u.get('name', 'User')} ({u['id'][:6]})" for u in st.session_state['fetched_users']}
                    cur_mem = [m for m in team['members'] if m in user_opts]
                    sel_mem = st.multiselect("Members", options=list(user_opts.keys()), default=cur_mem, format_func=lambda x: user_opts[x], key=f"ms_{i}")
                    if st.button("💾 Save", key=f"save_{i}"):
                        update_team_membership(team['name'], sel_mem)
                        st.success("Saved.")
                st.markdown("</div>", unsafe_allow_html=True)

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
            s_id = st.session_state.get('standup_cat_id', "")
            i_id = st.session_state.get('internship_cat_id', "")
            limit = st.session_state.get('fetch_limit', 500)
            
            with st.spinner("⏳ Fetching records (cached for 5 min)..."):
                records = []
                date_str = selected_date.isoformat()
                if s_id: records.extend(fetch_records(api_token, target_date=date_str, category_id=s_id, limit=limit))
                if i_id: records.extend(fetch_records(api_token, target_date=date_str, category_id=i_id, limit=limit))
                if not records and not (s_id or i_id): records = fetch_records(api_token, target_date=date_str, limit=limit)
                
                if not records:
                    st.warning("⚠️ No records found. Check your token and Category IDs in the Team Management tab.")
                else:
                    results = calculate_compliance(records, selected_date.isoformat(), all_created_teams)
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
