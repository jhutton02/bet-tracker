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
        return float(val.replace("x",""))
    except:
        return 0.0

def calc_odds(risk, to_win):
    return (to_win / risk) + 1 if risk != 0 else 0

def calc_profit(risk, odds, result):
    result = str(result).lower().strip()
    if result == "loss":
        return -risk
    if result == "pending" or result == "push":
        return 0
    return risk * (odds - 1)

def parse_date_safe(val):
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        return None

def get_risk(b):
    return float(b.get("risk", 0))

# ================= DATA =================
def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for i, r in enumerate(rows, start=2):
        risk = float(r.get("risk", 0))
        odds = safe_parse_odds(r["odds"])
        result = str(r["result"]).lower()

        bets.append({
            "row": i,
            "date": parse_date_safe(r["date"]),
            "bet_line": r["bet_line"],
            "odds": r["odds"],
            "risk": risk,
            "result": result,
            "profit": calc_profit(risk, odds, result)
        })
    return bets

def update_bet(row, bet):
    odds_val = safe_parse_odds(bet["odds"])
    profit = calc_profit(bet["risk"], odds_val, bet["result"])

    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), "", "", bet["bet_line"],
        bet["odds"], bet["risk"], bet["result"], profit
    ]])

    st.session_state.bets = load_bets()

# ================= STATE =================
if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

# ================= CALENDAR =================
st.subheader("Calendar")

today = date.today()

year = st.selectbox("Year", [today.year])
month_names = list(calendar.month_name)[1:]
selected_month = st.selectbox("Month", month_names, index=today.month-1)
month = month_names.index(selected_month) + 1

# CALCULATE DAILY TOTALS
totals = {}
counts = {}

for b in st.session_state.bets:
    if b["date"] and b["date"].year == year and b["date"].month == month:
        d = b["date"]
        totals[d] = totals.get(d, 0) + b["profit"]
        counts[d] = counts.get(d, 0) + 1

# CALENDAR GRID
for week in calendar.monthcalendar(year, month):
    cols = st.columns(7)

    for i, day in enumerate(week):
        if day == 0:
            continue

        d = date(year, month, day)
        val = totals.get(d, 0)
        cnt = counts.get(d, 0)

        # COLORS
        if val > 0:
            bg = "#16a34a"
            text = "white"
        elif val < 0:
            bg = "#dc2626"
            text = "white"
        else:
            bg = "#f1f5f9"
            text = "#111"

        # CLICKABLE CARD
        if cols[i].button("", key=f"click_{day}"):
            st.session_state.selected_date = d

        cols[i].markdown(f"""
        <div style="
            background:{bg};
            color:{text};
            padding:12px;
            border-radius:14px;
            height:100px;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
            font-size:14px;
        ">
            <div style="font-weight:600;">{day}</div>
            <div style="font-size:18px;font-weight:700;">${round(val,2)}</div>
            <div style="font-size:12px;opacity:0.8;">{cnt} bets</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ================= DAY DETAILS =================
st.subheader(f"Bets for {st.session_state.selected_date}")

for b in st.session_state.bets:
    if b["date"] == st.session_state.selected_date:
        st.write(f"{b['bet_line']} | {b['odds']} | ${b['profit']}")
