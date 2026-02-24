# ⚡ Corpus Standup Tracker

A Streamlit-based compliance tracker for monitoring daily standup contributions on the [Corpus (Swecha)](https://corpus.swecha.org) platform.

## 🔗 Live App

**[https://corpus-standup-tracker.streamlit.app](https://corpus-standup-tracker.streamlit.app/)**

---

## What It Does

- **Login** — Authenticate with your Corpus phone number and password (+91 prefix is pre-filled).
- **Compliance Dashboard** — Check whether team members submitted their standups on time, late, or missed them entirely for any given date.
- **Analytics** — View contribution trends, submission heatmaps, and team-level statistics over configurable date ranges with interactive Plotly charts.
- **Team Management** — Create teams, search users from Corpus, and assign them to teams. Member info is persisted locally in `teams.json`.

### Session Windows (IST)

| Session | On-Time | Late/Grace |
|---|---|---|
| 🌅 Morning Standup | 09:00 – 09:30 | 09:30 – 10:30 |
| 🔄 Morning Recap | 12:00 – 12:30 | 12:30 – 13:30 |
| ☀️ Afternoon Standup | 13:30 – 14:00 | 14:00 – 15:00 |
| 🌆 Afternoon Recap | 16:30 – 17:00 | 17:00 – 00:00 |

---

## Project Structure

```
corpus-standup-tracker/
├── app.py              # Main Streamlit app (login, dashboard, analytics, team mgmt)
├── auth.py             # Standalone auth helper (auto-login from .env)
├── compliance.py       # Compliance logic — session windows, on-time/late classification
├── fetch.py            # API calls — user search, profile fetch, audio contributions
├── mapping.py          # Team CRUD — load/save/delete teams from teams.json
├── teams.json          # Persisted team & member data
├── test_compliance.py  # Unit tests for compliance logic
├── requirements.txt    # Python dependencies
├── .env.example        # Template for environment variables
└── .gitignore
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://code.swecha.org/Mukthanand21/corpus-standup-tracker.git
cd corpus-standup-tracker
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the app

```bash
streamlit run app.py
```

The app will open at `http://localhost:8501`.

---

## Running Tests

```bash
python3 -m pytest test_compliance.py -v
```

---

## Tech Stack

- **[Streamlit](https://streamlit.io/)** — UI framework
- **[Plotly](https://plotly.com/python/)** — Interactive charts
- **[Pandas](https://pandas.pydata.org/)** — Data processing
- **[Requests](https://docs.python-requests.org/)** — HTTP client for Corpus API
- **[streamlit-searchbox](https://github.com/m-wrzr/streamlit-searchbox)** — Typeahead user search (optional)

---

## License

This project was built during **Viswam.Ai 2102 Hackathon**.

## Team

| Name | GitLab |
|---|---|
| Mukthanand Reddy M | [@Mukthanand21](https://gitlab.com/Mukthanand21) |
| Shanmukha Varma Lanke | [@Shanmukh16](https://gitlab.com/Shanmukh16) |
| Rushika Sritha Maddula | [@Rushika_1105](https://gitlab.com/Rushika_1105) |
