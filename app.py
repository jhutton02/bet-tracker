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

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# ================= TABS =================

t1, t2, t3, t4 = st.tabs(["📅 Calendar", "➕ Add Bet", "📋 Tracker", "🔥 Live Tracker"])

# ================= CALENDAR =================

with t1:
    today = date.today()

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    with col2:
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Month", month_names, index=today.month - 1)

    month = month_names.index(selected_month_name) + 1

    totals = {}
    counts = {}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year == year and b["date"].month == month:
            d = b["date"]
            totals[d] = totals.get(d, 0) + b["profit"]
            counts[d] = counts.get(d, 0) + 1

    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].markdown("")
                continue

            d = date(year, month, day)
            val = totals.get(d, 0)
            cnt = counts.get(d, 0)

            if val > 0:
                bg = "#16a34a"; tc = "white"
            elif val < 0:
                bg = "#dc2626"; tc = "white"
            else:
                bg = "#f1f5f9"; tc = "black"

            with cols[i]:
                if st.button(" ", key=f"btn_{d}"):
                    st.session_state.selected_date = d

                st.markdown(f"""
                <div style="background:{bg};color:{tc};padding:12px;border-radius:14px;height:100px;text-align:center;">
                    <b>{day}</b><br>${round(val,2)}<br>{cnt} bets
                </div>
                """, unsafe_allow_html=True)

    selected_date = st.session_state.selected_date

    st.divider()
    st.subheader(f"Bets for {selected_date}")

    day_bets = [b for b in st.session_state.bets if b["date"] == selected_date]

    for b in day_bets:
        col1, col2, col3 = st.columns([8,1,1])

        with col1:
            st.markdown(f"""
            <div style='background:#f1f5f9;padding:12px;border-radius:12px;margin-bottom:8px'>
            <b>{b['sport']} | {b['bet_type']}</b><br>
            {b['bet_line']} {result_badge(b['result'])}<br>
            Odds: {format_odds_display(b['odds'])}<br>
            Risk: ${get_risk(b)}<br>
            <b>${round(b['profit'],2)}</b>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if st.button("✏️", key=f"edit_{b['row']}"):
                st.session_state.edit_row = b["row"]

        with col3:
            if st.button("❌", key=f"del_{b['row']}"):
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
    st.write("Tracker working")

# ================= LIVE =================
with t4:
    st.write("Live tracker working")
