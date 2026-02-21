import streamlit as st
import pandas as pd
from datetime import date
from fetch import fetch_records, fetch_users, fetch_categories, fetch_user_by_id
from compliance import calculate_compliance
from mapping import load_teams, save_teams, update_team_membership, delete_team, get_all_teams

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
    api_token = st.text_input("Bearer Token", type="password")
    st.divider()
    st.info("Assign members locally in the 'Team Management' tab.")

tab_dashboard, tab_mgmt = st.tabs(["📊 Compliance Dashboard", "👥 Team Management"])

# --- TEAM MANAGEMENT ---
with tab_mgmt:
    st.header("Team & Member Setup")
    
    # API Settings in Expander
    with st.expander("⚙️ API Configuration", expanded=False):
        st.text_input("Standup Category ID", key="standup_cat_id")
        st.text_input("Internship Category ID", key="internship_cat_id")
        st.number_input("Fetch Limit", min_value=10, max_value=2000, value=500, key="fetch_limit")
        if st.button("🔍 Find Category IDs"):
            if api_token:
                cats = fetch_categories(api_token)
                st.dataframe(cats)

    # 1. Fetch User by ID
    st.subheader("👤 User Management")
    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        u_id_search = st.text_input("Search/Add User by UUID", placeholder="8d53a79b-...")
    with col_u2:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🎯 Fetch & Add", use_container_width=True):
            if api_token and u_id_search:
                user = fetch_user_by_id(api_token, u_id_search)
                if user:
                    if 'fetched_users' not in st.session_state: st.session_state['fetched_users'] = []
                    if not any(u.get('id') == user.get('id') for u in st.session_state['fetched_users']):
                        st.session_state['fetched_users'].append(user)
                    st.success(f"Added: {user.get('name', 'Unknown')}")
                else: st.error("User not found.")

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
            
            with st.spinner("Fetching..."):
                records = []
                if s_id: records.extend(fetch_records(api_token, s_id, limit=limit))
                if i_id: records.extend(fetch_records(api_token, i_id, limit=limit))
                if not records and not (s_id or i_id): records = fetch_records(api_token, limit=limit)
                
                if not records: st.error("No records found.")
                else:
                    results = calculate_compliance(records, selected_date.isoformat(), all_created_teams)
                    df = pd.DataFrame(results)
                    
                    # Selection Filter
                    if "All" not in filter_team:
                        df = df[df["team_name"].isin(filter_team)]
                    
                    if df.empty:
                        st.info("No matching teams.")
                    else:
                        m1, m2, m3 = st.columns(3)
                        total_sub = (df[["morning_standup", "morning_recap", "afternoon_standup", "afternoon_recap"]] == "submitted").sum().sum()
                        m1.markdown(f'<div class="metric-card"><div class="metric-label">Teams</div><div class="metric-value">{len(df)}</div></div>', unsafe_allow_html=True)
                        m2.markdown(f'<div class="metric-card"><div class="metric-label">Total Submissions</div><div class="metric-value">{total_sub}</div></div>', unsafe_allow_html=True)
                        m3.markdown(f'<div class="metric-card"><div class="metric-label">Avg Completion</div><div class="metric-value">{df["completion"].mean():.1f}%</div></div>', unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        def color_status(val):
                            if val == "submitted": return 'background-color: #d1fae5'
                            if val == "late": return 'background-color: #fef3c7'
                            if val == "missing": return 'background-color: #fee2e2'
                            return ''

                        st.dataframe(
                            df.style.map(color_status, subset=["morning_standup", "morning_recap", "afternoon_standup", "afternoon_recap"]),
                            column_config={
                                "completion": st.column_config.ProgressColumn("Progress", format="%d%%", min_value=0, max_value=100)
                            },
                            use_container_width=True, hide_index=True
                        )
                        with st.expander("Show Details"): st.json(results)
