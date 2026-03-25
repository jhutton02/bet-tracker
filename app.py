import streamlit as st
from datetime import date, timedelta, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import requests

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
    if risk == 0:
        return 0
    return (to_win / risk) + 1

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

# ================= LIVE STATS =================

def get_player_points(player_name):
    try:
        # 🔥 Simple free API example (can upgrade later)
        url = f"https://www.balldontlie.io/api/v1/players?search={player_name}"
        res = requests.get(url).json()
        if not res["data"]:
            return 0

        player_id = res["data"][0]["id"]

        stats_url = f"https://www.balldontlie.io/api/v1/stats?player_ids[]={player_id}&per_page=1"
        stats = requests.get(stats_url).json()

        if not stats["data"]:
            return 0

        game = stats["data"][0]
        return game["pts"] + game["reb"] + game["ast"]  # PRA default
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

# ================= STATE =================
if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "live_slips" not in st.session_state:
    st.session_state.live_slips = []

# ================= TABS =================
t1, t2, t3, t4 = st.tabs(["📅 Calendar", "➕ Add Bet", "📋 Tracker", "🔥 Live Tracker"])

# ================= ADD BET =================
with t2:
    with st.form("add"):
        bet_date = st.date_input("Date", date.today())
        sport = st.selectbox("Sport", ["NBA","NFL","MLB","NHL","Other"])
        bet_type = st.selectbox("Bet Type", ["Straight","Parlay"])
        wager = st.text_input("Wager")

        risk = st.number_input("Risk ($)", value=100.0)
        to_win = st.number_input("To Win ($)", value=100.0)
        odds_val = calc_odds(risk, to_win)

        st.text_input("Odds", f"{round(odds_val,2)}x", disabled=True)

        result = st.selectbox("Result", ["pending","win","loss","push"])

        if st.form_submit_button("Add Bet"):
            profit = calc_profit(risk, odds_val, result)

            save_bet({
                "date": bet_date,
                "sport": sport,
                "bet_type": bet_type,
                "bet_line": wager,
                "odds": f"{round(odds_val,2)}x",
                "risk": risk,
                "result": result,
                "profit": profit
            })

            st.session_state.bets = load_bets()
            st.success("Bet added")
            st.rerun()

# ================= TRACKER =================
with t3:
    bets = st.session_state.bets

    total_risk = sum(get_risk(b) for b in bets)
    total_profit = sum(b["profit"] for b in bets)

    st.metric("Total Risk", f"${round(total_risk,2)}")
    st.metric("Total Profit", f"${round(total_profit,2)}")

    if bets:
        sorted_bets = sorted(bets, key=lambda x: x["date"])
        dates = []
        running_total = []
        total = 0

        for b in sorted_bets:
            total += b["profit"]
            dates.append(b["date"])
            running_total.append(total)

        fig, ax = plt.subplots()
        ax.plot(dates, running_total)
        ax.axhline(0, linestyle="--")
        st.pyplot(fig)

# ================= LIVE TRACKER =================
with t4:
    st.subheader("Live Bet Tracker")

    with st.form("live_form"):
        player = st.text_input("Player Name (e.g. Nikola Jokic)")
        line = st.number_input("Line (e.g. 34.5)", value=30.0)

        if st.form_submit_button("Add Live Bet"):
            st.session_state.live_slips.append({
                "player": player,
                "line": line
            })

    st.divider()

    for slip in st.session_state.live_slips:
        current = get_player_points(slip["player"])
        bar = progress_bar(current, slip["line"])

        st.markdown(f"""
        **{slip['player']} (Line: {slip['line']})**  
        Current: {current}  
        {bar}
        """)
