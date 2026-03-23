import streamlit as st
from datetime import date, timedelta
import calendar
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Bet Tracker", layout="centered")
st.title("📊 Bet Tracker Pro")

UNIT_SIZE = st.number_input("Dollar value per unit", value=100)

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

def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for i, r in enumerate(rows, start=2):
        bets.append({
            "row": i,
            "date": date.fromisoformat(str(r["date"])),
            "sport": r["sport"],
            "bet_type": r["bet_type"],
            "bet_line": r["bet_line"],
            "odds": safe_parse_odds(r["odds"]),
            "units": float(r["units"]),
            "result": r["result"],
            "profit": float(r["profit"])
        })
    return bets

def save_bet(bet):
    sheet.append_row([
        str(bet["date"]), bet["sport"], bet["bet_type"], bet["bet_line"],
        bet["odds"], bet["units"], bet["result"], bet["profit"]
    ])

def update_bet(row, bet):
    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), bet["sport"], bet["bet_type"], bet["bet_line"],
        bet["odds"], bet["units"], bet["result"], bet["profit"]
    ]])

def delete_bet(row):
    sheet.delete_rows(row)

def calc_profit(units, odds, result):
    if result == "pending":
        return 0
    if odds >= 1.01 and odds < 10:
        return units * (odds - 1) if result == "win" else -units
    if odds > 0:
        return units * (odds / 100) if result == "win" else -units
    if odds < 0:
        return units * (100 / abs(odds)) if result == "win" else -units
    return 0

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

# ================= TABS =================
t1, t2, t3 = st.tabs(["📋 Tracker", "➕ Add Bet", "📅 Calendar"])

# ================= TRACKER =================
with t1:

    bets = st.session_state.bets

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    def get_total(start):
        return sum(b["profit"] for b in bets if b["date"] >= start)

    weekly = get_total(week_start)
    monthly = get_total(month_start)
    yearly = get_total(year_start)

    def color(val):
        return "#16a34a" if val > 0 else "#dc2626" if val < 0 else "#374151"

    c1, c2, c3 = st.columns(3)

    c1.markdown(f"<h3 style='color:{color(weekly)}'>Week: ${round(weekly,2)}</h3>", unsafe_allow_html=True)
    c2.markdown(f"<h3 style='color:{color(monthly)}'>Month: ${round(monthly,2)}</h3>", unsafe_allow_html=True)
    c3.markdown(f"<h3 style='color:{color(yearly)}'>Year: ${round(yearly,2)}</h3>", unsafe_allow_html=True)

# ================= CALENDAR =================
with t3:

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

    headers = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    cols = st.columns(7)
    for i in range(7):
        cols[i].markdown("**" + headers[i] + "**")

    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)

        for idx, day in enumerate(week):

            if day == 0:
                cols[idx].markdown("")
            else:
                d = date(year, month, day)
                val = totals.get(d, 0)
                cnt = counts.get(d, 0)

                bg = "#d1fae5" if val > 0 else "#fee2e2" if val < 0 else "#f1f5f9"

                if cols[idx].button(f"{day}\n${round(val,2)}\n{cnt} bets", key=f"day_{d}"):
                    st.session_state.selected_day = d

                cols[idx].markdown(f"""
                <div style="
                    background:{bg};
                    padding:10px;
                    border-radius:10px;
                    margin-top:-80px;
                    height:100px;
                "></div>
                """, unsafe_allow_html=True)

    # ===== CLEAN DROPDOWN BELOW =====
    if st.session_state.selected_day:
        st.divider()
        st.subheader(f"Bets on {st.session_state.selected_day}")

        day_bets = [b for b in st.session_state.bets if b["date"] == st.session_state.selected_day]

        for b in day_bets:
            color_box = "#d1fae5" if b["profit"] > 0 else "#fee2e2"

            st.markdown(f"""
            <div style='background:{color_box};padding:12px;border-radius:10px;margin-bottom:8px'>
            {b['sport']} | {b['bet_line']} | {b['result']}<br>
            <b>${round(b['profit'],2)}</b>
            </div>
            """, unsafe_allow_html=True)
