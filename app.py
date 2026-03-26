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

# ================= LIVE API =================

def get_player_points(player_name):
    try:
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
        return game["pts"] + game["reb"] + game["ast"]
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

# ================= CALENDAR =================

with t1:
    today = date.today()

    year = today.year
    month = today.month

    totals = {}
    counts = {}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year == year and b["date"].month == month:
            d = b["date"]
            totals[d] = totals.get(d, 0) + b["profit"]
            counts[d] = counts.get(d, 0) + 1

    st.markdown("<div style='background:#f8fafc;padding:20px;border-radius:12px;'>", unsafe_allow_html=True)

    days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    cols = st.columns(7)
    for i, d in enumerate(days):
        cols[i].markdown(f"<div style='text-align:center;font-size:12px;font-weight:600'>{d}</div>", unsafe_allow_html=True)

    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].markdown("<div style='height:90px;border:1px solid #e5e7eb;'></div>", unsafe_allow_html=True)
                continue

            d = date(year, month, day)
            val = totals.get(d, 0)
            cnt = counts.get(d, 0)

            bg = "#dcfce7" if val > 0 else "#fee2e2" if val < 0 else "#ffffff"

            cols[i].markdown(f"""
            <div style="height:90px;border:1px solid #e5e7eb;padding:8px;background:{bg};
                        display:flex;flex-direction:column;justify-content:space-between;">
                <div><b>{day}</b></div>
                <div style="font-size:12px;color:#6b7280;">
                    ${round(val,2)}<br>{cnt} bets
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

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

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    daily = sum(b["profit"] for b in bets if b["date"] == today)
    weekly = sum(b["profit"] for b in bets if b["date"] and b["date"] >= week_start)
    monthly = sum(b["profit"] for b in bets if b["date"] and b["date"] >= month_start)

    st.metric("Day", daily)
    st.metric("Week", weekly)
    st.metric("Month", monthly)

    # Graph
    sorted_bets = sorted([b for b in bets if b["date"]], key=lambda x: x["date"])
    dates = [b["date"] for b in sorted_bets]
    profits = [b["profit"] for b in sorted_bets]

    running = []
    total = 0
    for p in profits:
        total += p
        running.append(total)

    fig, ax = plt.subplots()
    ax.plot(dates, running)
    ax.axhline(0, linestyle="--")
    st.pyplot(fig)

# ================= LIVE TRACKER =================

with t4:
    st.subheader("Live Bet Tracker")

    with st.form("live_form"):
        player = st.text_input("Player Name")
        bet_type = st.selectbox("Bet Type", ["Points","Rebounds","Assists","PRA"])
        line = st.number_input("Line", value=30.0)

        if st.form_submit_button("Add"):
            st.session_state.live_slips.append({
                "player": player,
                "line": line,
                "bet_type": bet_type
            })

    for slip in st.session_state.live_slips:
        current = get_player_points(slip["player"])
        bar = progress_bar(current, slip["line"])

        st.markdown(f"""
        **{slip['player']} ({slip['bet_type']} - Line: {slip['line']})**  
        Current: {current}  
        {bar}
        """)
