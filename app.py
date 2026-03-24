import streamlit as st
from datetime import date, timedelta
import calendar
import gspread
from google.oauth2.service_account import Credentials

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
        return float(str(val).lower().replace("x", "").strip())
    except:
        return 0.0

def calc_profit(risk, odds, result):
    result = str(result).lower().strip()

    if result == "pending":
        return 0

    if result == "loss":
        return -risk

    if result == "push":
        return 0

    if odds >= 1:  # decimal odds
        return risk * (odds - 1)

    if odds > 0:  # american +
        return risk * (odds / 100)

    if odds < 0:  # american -
        return risk * (100 / abs(odds))

    return 0

def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for i, r in enumerate(rows, start=2):

        odds = safe_parse_odds(r["odds"])
        risk = float(r["units"])
        result = str(r["result"]).lower().strip()

        profit = calc_profit(risk, odds, result)

        bets.append({
            "row": i,
            "date": date.fromisoformat(str(r["date"])),
            "sport": r["sport"],
            "bet_type": r["bet_type"],
            "bet_line": r["bet_line"],
            "odds": odds,
            "units": risk,
            "result": result,
            "profit": profit
        })
    return bets

def save_bet(bet):
    sheet.append_row([
        str(bet["date"]), bet["sport"], bet["bet_type"], bet["bet_line"],
        bet["odds"], bet["units"], bet["result"], bet["profit"]
    ])

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

# ================= TABS =================
t1, t2, t3 = st.tabs(["📅 Calendar", "➕ Add Bet", "📋 Tracker"])

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
        if b["date"].year == year and b["date"].month == month:
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
                bg = "#16a34a"
                text_color = "white"
            elif val < 0:
                bg = "#dc2626"
                text_color = "white"
            else:
                bg = "#f1f5f9"
                text_color = "black"

            cols[i].markdown(f"""
            <div style="
                background:{bg};
                color:{text_color};
                padding:12px;
                border-radius:14px;
                height:100px;
                border:1px solid rgba(0,0,0,0.08);
            ">
                <b>{day}</b><br>
                ${round(val,2)}<br>
                {cnt} bets
            </div>
            """, unsafe_allow_html=True)

# ================= ADD BET =================
with t2:
    with st.form("add"):
        bet_date = st.date_input("Date", date.today())
        sport = st.selectbox("Sport", ["NBA","NFL","MLB","NHL","Other"])
        bet_type = st.selectbox("Bet Type", ["Straight","Parlay"])
        wager = st.text_input("Wager")
        odds = st.number_input("Odds", value=1.90)
        risk = st.number_input("Risk ($)", value=100.0)
        result = st.selectbox("Result", ["pending","win","loss","push"])

        if st.form_submit_button("Add Bet"):
            profit = calc_profit(risk, odds, result)

            bet = {
                "date": bet_date,
                "sport": sport,
                "bet_type": bet_type,
                "bet_line": wager,
                "odds": odds,
                "units": risk,
                "result": result,
                "profit": profit
            }

            save_bet(bet)
            st.session_state.bets = load_bets()
            st.success("Bet added")

# ================= TRACKER =================
with t3:

    bets = st.session_state.bets

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    daily = sum(b["profit"] for b in bets if b["date"] == today)
    weekly = sum(b["profit"] for b in bets if b["date"] >= week_start)
    monthly = sum(b["profit"] for b in bets if b["date"] >= month_start)

    def color(val):
        return "#16a34a" if val > 0 else "#dc2626" if val < 0 else "#374151"

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<h3 style='color:{color(daily)}'>Day: ${round(daily,2)}</h3>", unsafe_allow_html=True)
    c2.markdown(f"<h3 style='color:{color(weekly)}'>Week: ${round(weekly,2)}</h3>", unsafe_allow_html=True)
    c3.markdown(f"<h3 style='color:{color(monthly)}'>Month: ${round(monthly,2)}</h3>", unsafe_allow_html=True)

    st.divider()

    for b in sorted(bets, key=lambda x: x["date"], reverse=True):

        if b["profit"] > 0:
            bg = "#d1fae5"
        elif b["profit"] < 0:
            bg = "#fee2e2"
        else:
            bg = "#f1f5f9"

        st.markdown(f"""
        <div style='background:{bg};padding:12px;border-radius:12px;margin-bottom:10px'>
        <b>{b['date']}</b> | {b['sport']} | {b['bet_type']}<br>
        <b>Wager:</b> {b['bet_line']} | {b['result']}<br>
        <b>${round(b['profit'],2)}</b>
        </div>
        """, unsafe_allow_html=True)
