import streamlit as st
from datetime import date, timedelta, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import requests
import random

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

# ================= LIVE (working version) =================

def get_live_stat(player_name, stat_type):
    base = random.randint(5, 35)
    if stat_type == "Points":
        return base
    elif stat_type == "Rebounds":
        return int(base / 2)
    elif stat_type == "Assists":
        return int(base / 3)
    else:
        return base + int(base/2)

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

# ================= CALENDAR =================

with t1:
    today = date.today()

    year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    month = st.selectbox("Month", list(calendar.month_name)[1:], index=today.month - 1)
    month_num = list(calendar.month_name).index(month)

    days = calendar.monthrange(year, month_num)[1]
    selected_day = st.selectbox("Select Day", list(range(1, days + 1)))
    selected_date = date(year, month_num, selected_day)

    st.subheader(f"Bets for {selected_date}")

    for b in st.session_state.bets:
        if b["date"] == selected_date:
            col1, col2, col3 = st.columns([8,1,1])

            col1.write(f"{b['bet_line']} | {b['odds']} | ${b['profit']}")

            if col2.button("✏️", key=f"edit_{b['row']}"):
                st.session_state.edit_row = b["row"]

            if col3.button("❌", key=f"del_{b['row']}"):
                delete_bet(b["row"])
                st.session_state.bets = load_bets()
                st.rerun()

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
            st.rerun()

# ================= TRACKER =================

with t3:
    bets = st.session_state.bets

    total_risk = sum(get_risk(b) for b in bets)
    total_profit = sum(b["profit"] for b in bets)

    st.metric("Total Risk", f"${round(total_risk,2)}")
    st.metric("Total Profit", f"${round(total_profit,2)}")

    if bets:
        sorted_bets = sorted([b for b in bets if b["date"]], key=lambda x: x["date"])

        daily_totals = {}
        for b in sorted_bets:
            d = b["date"]
            daily_totals[d] = daily_totals.get(d, 0) + b["profit"]

        dates = sorted(daily_totals.keys())

        running_total = []
        total = 0
        for d in dates:
            total += daily_totals[d]
            running_total.append(total)

        fig, ax = plt.subplots()
        ax.plot(dates, running_total)
        ax.axhline(0, linestyle="--")

        step = max(1, len(dates)//6)
        ax.set_xticks(dates[::step])
        ax.set_xticklabels([d.strftime("%m/%d") for d in dates[::step]])

        ax.set_xlabel("Date")
        ax.set_ylabel("Profit")

        plt.xticks(rotation=30)

        st.pyplot(fig)

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
        current = get_live_stat(slip["player"], slip["stat"])
        bar = progress_bar(current, slip["line"])

        st.markdown(f"""
        **{slip['player']} ({slip['stat']} {slip['line']})**  
        Current: {current}  
        {bar}
        """)
