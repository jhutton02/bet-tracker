import streamlit as st
from datetime import date, timedelta, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="Bet Tracker", layout="centered")
st.title("📊 Bet Tracker Pro")

# ================= GOOGLE SHEETS =================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1ckrXeP6LZpLSVdbRV1-02kj0WuKj603Q8_kDoqCVh9Q").sheet1

# ================= HELPERS =================

def safe_parse_odds(val):
    try:
        val = str(val).lower().replace(" ", "").strip()
        if "x" in val:
            return float(val.replace("x", ""))
        return float(val)
    except:
        return 0.0

def calc_odds(risk, to_win):
    return (to_win / risk) + 1 if risk != 0 else 0

def calc_to_win(risk, odds):
    return risk * (odds - 1) if odds >= 1 else 0

def calc_profit(risk, odds, result):
    result = str(result).lower().strip()
    if result == "pending":
        return 0
    if result == "loss":
        return -risk
    if result == "push":
        return 0
    return risk * (odds - 1)

def parse_date_safe(val):
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        return None

def get_risk(b):
    return float(b.get("risk", b.get("units", 0)))

def format_odds_display(val):
    try:
        return f"{float(str(val).replace('x','')):.2f}x"
    except:
        return val

def result_badge(result):
    result = result.lower()
    colors = {
        "win": ("#16a34a","white"),
        "loss": ("#dc2626","white"),
        "pending": ("#facc15","black"),
        "push": ("#64748b","white")
    }
    bg, color = colors.get(result, ("#64748b","white"))
    return f"<span style='background:{bg};color:{color};padding:3px 8px;border-radius:999px;font-size:11px;font-weight:600;'>{result.upper()}</span>"

# ================= ESPN LIVE =================

def get_espn_stats(player_name, stat_type):
    try:
        search_name = player_name.lower().replace(" ", "-")
        url = f"https://www.espn.com/nba/player/_/name/{search_name}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

        if res.status_code != 200:
            return 0

        soup = BeautifulSoup(res.text, "html.parser")
        stats = soup.find_all("td")

        values = []
        for s in stats:
            try:
                values.append(float(s.text))
            except:
                continue

        if len(values) < 3:
            return 0

        pts = values[0]
        reb = values[1]
        ast = values[2]

        if stat_type == "Points":
            return pts
        elif stat_type == "Rebounds":
            return reb
        elif stat_type == "Assists":
            return ast
        else:
            return pts + reb + ast

    except:
        return 0

def progress_bar(current, line):
    pct = min(current / line, 1.0) if line > 0 else 0
    filled = int(pct * 20)
    bar = "█" * filled + "░" * (20 - filled)
    return f"[{bar}] {int(pct*100)}%"

# ================= DATA =================

def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for i, r in enumerate(rows, start=2):
        risk = float(r.get("risk", r.get("units", 0)))
        odds = safe_parse_odds(r["odds"])
        result = str(r["result"]).lower().strip()
        profit = calc_profit(risk, odds, result)

        bets.append({
            "row": i,
            "date": parse_date_safe(r["date"]),
            "sport": r["sport"],
            "bet_type": r["bet_type"],
            "bet_line": r["bet_line"],
            "odds": r["odds"],
            "risk": risk,
            "result": result,
            "profit": profit
        })
    return bets

def save_bet(bet):
    sheet.append_row([
        str(bet["date"]), bet["sport"], bet["bet_type"], bet["bet_line"],
        bet["odds"], bet["risk"], bet["result"], bet["profit"]
    ])

def delete_bet(row):
    sheet.delete_rows(row)

def update_bet(row, bet):
    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), bet["sport"], bet["bet_type"], bet["bet_line"],
        bet["odds"], bet["risk"], bet["result"], bet["profit"]
    ]])

# ================= STATE =================

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "live_slips" not in st.session_state:
    st.session_state.live_slips = []

if "edit_row" not in st.session_state:
    st.session_state.edit_row = None

# ================= TABS =================

t1, t2, t3, t4 = st.tabs(["📅 Calendar", "➕ Add Bet", "📋 Tracker", "🔥 Live Tracker"])

# ================= LIVE TRACKER =================

with t4:
    st.subheader("Live Bet Tracker")

    with st.form("live_form"):
        player = st.text_input("Player Name")
        stat_type = st.selectbox("Stat Type", ["PRA","Points","Rebounds","Assists"])
        line = st.number_input("Line", value=30.0)

        if st.form_submit_button("Add"):
            st.session_state.live_slips.append({
                "player": player,
                "line": line,
                "stat": stat_type
            })

    for slip in st.session_state.live_slips:
        current = get_espn_stats(slip["player"], slip["stat"])
        bar = progress_bar(current, slip["line"])

        st.markdown(f"""
        **{slip['player']} ({slip['stat']} {slip['line']})**  
        Current: {current}  
        {bar}
        """)
