import streamlit as st
import pandas as pd
from datetime import date
from fetch import fetch_standups
from compliance import calculate_compliance

# Page config
st.set_page_config(page_title="Standup Compliance Tracker", layout="wide")

st.title("🚀 Team Standup Compliance Tracker")
st.markdown("""
This dashboard tracks daily standup submissions across different teams. 
Each team is expected to submit 4 sessions: **Morning Standup, Morning Recap, Afternoon Standup, and Afternoon Recap**.
""")

# Sidebar for inputs
with st.sidebar:
    st.header("Settings")
    selected_date = st.date_input("Select Date", date.today())
    use_demo = st.checkbox("🧪 Use Demo Data", value=True, help="Enable this to see how the dashboard works with mock data.")
    run_check = st.button("🔄 Check Compliance", use_container_width=True)

if run_check:
    with st.spinner(f"Fetching data for {selected_date}..."):
        if use_demo:
            # Mock data for demonstration
            submissions = [
                {"member_id": "u101", "name": "Alice", "timestamp": f"{selected_date}T09:30:00", "label": "stand-up"},
                {"member_id": "u102", "name": "Bob", "timestamp": f"{selected_date}T11:15:00", "label": "stand-up"},
                {"member_id": "u201", "name": "Charlie", "timestamp": f"{selected_date}T12:30:00", "label": "stand-up"},
                {"member_id": "u201", "name": "Charlie", "timestamp": f"{selected_date}T14:30:00", "label": "stand-up"},
                {"member_id": "u202", "name": "David", "timestamp": f"{selected_date}T17:15:00", "label": "stand-up"},
            ]
            st.info("💡 Running in Demo Mode with mock data.")
        else:
            # Fetch real data
            submissions = fetch_standups(selected_date.isoformat())
        
        if not submissions:
            if not use_demo:
                st.warning(f"No submissions found for {selected_date}. Please check if the BASE_URL in `fetch.py` is correct.")
            else:
                st.warning(f"No submissions found for {selected_date}.")
        else:
            # Process compliance
            results = calculate_compliance(submissions)
            
            if results:
                # Convert to DataFrame for better display
                df = pd.DataFrame(results)
                
                # Reorder columns for better readability
                cols = ["team_name", "morning_standup", "morning_recap", "afternoon_standup", "afternoon_recap", "completion"]
                df = df[cols]
                
                # Display metrics summary
                avg_completion = df["completion"].mean()
                st.metric("Overall Organization Compliance", f"{avg_completion:.1f}%")

                # Function to color cells based on status
                def color_status(val):
                    color = "#ffffff"
                    if val == "submitted":
                        color = "#d4edda" # light green
                    elif val == "late":
                        color = "#fff3cd" # light yellow
                    elif val == "missing":
                        color = "#f8d7da" # light red
                    return f'background-color: {color}'

                # Style the completion column
                def color_completion(val):
                    color = "red" if val < 50 else "blue" if val < 100 else "green"
                    return f'color: {color}; font-weight: bold'

                styled_df = df.style.applymap(color_status, subset=["morning_standup", "morning_recap", "afternoon_standup", "afternoon_recap"])\
                                   .applymap(color_completion, subset=["completion"])\
                                   .format({"completion": "{:.1f}%"})

                st.subheader(f"Compliance Report for {selected_date}")
                st.table(styled_df)
                
                # Show raw JSON for developer use
                with st.expander("Show Raw JSON Output"):
                    st.json(results)
            else:
                st.error("Could not calculate compliance. Check if team mapping is configured.")
else:
    st.info("Select a date from the sidebar and click 'Check Compliance' to begin.")

# Footer
st.markdown("---")
st.caption("Viswam.Ai Standup Compliance Tracker | Modular & Production-Ready")
