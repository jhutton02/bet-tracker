import streamlit as st
from datetime import date, timedelta
import calendar
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Bet Tracker", layout="centered")
st.title("Bet Tracker")

UNIT_SIZE = st.number_input("Dollar value per unit", value=100)

# ================= GOOGLE SHEETS SETUP =================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
gc = gspread.authorize(creds)

SHEET_ID = "1ckrXeP6LZpLSVdbRV1-02kj0WuKj603Q8_kDoqCVh9Q"
sheet = gc.open_by_key(SHEET_ID).sheet1

# ================= HELPERS =================

def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for r in rows:
        b = {}
        b["date"] = date.fromisoformat(str(r["date"]))
        b["sport"] = r["sport"]
        b["bet_type"] = r["bet_type"]
        b["bet_line"] = r["bet_line"]
        b["odds"] = r["odds"]
        b["units"] = float(r["units"])
        b["result"] = r["result"]
        b["profit"] = float(r["profit"])
        bets.append(b)
    return bets

def save_bet(bet):
    sheet.append_row([
        str(bet["date"]),
        bet["sport"],
        bet["bet_type"],
        bet["bet_line"],
        bet["odds"],
        bet["units"],
        bet["result"],
        bet["profit"]
    ])

def update_bet(row_index, bet):
    sheet.update(f"A{row_index}:H{row_index}", [[
        str(bet["date"]),
        bet["sport"],
        bet["bet_type"],
        bet["bet_line"],
        bet["odds"],
        bet["units"],
        bet["result"],
        bet["profit"]
    ]])

def delete_bet(row_index):
    sheet.delete_rows(row_index)

def parse_odds(text):
    try:
        return float(text.lower().replace("x", "").strip())
    except:
        return None

def calc_profit(units, odds, result):
    if result == "pending":
        return 0
    if odds >= 1.01 and odds < 10 and result == "win":
        return units * (odds - 1)
    if odds >= 1.01 and odds < 10 and result == "loss":
        return -units
    if result == "win" and odds > 0:
        return units * (odds / 100)
    if result == "win" and odds < 0:
        return units * (100 / abs(odds))
    if result == "loss":
        return -units
    return 0

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

tab_tracker, tab_add, tab_calendar = st.tabs(["Tracker", "Add Bet", "Calendar"])

# ================= CALENDAR TAB =================
with tab_calendar:

    today = date.today()

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    with col2:
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Month", month_names, index=today.month - 1)

    month = month_names.index(selected_month_name) + 1

    monthly_total = 0
    totals = {}

    for b in st.session_state.bets:
        if b["date"].year == year and b["date"].month == month:
            totals[b["date"]] = totals.get(b["date"], 0) + b["profit"]
            if b["result"] in ["win","loss","push"]:
                monthly_total += b["profit"]

    total_color = "green" if monthly_total > 0 else "red" if monthly_total < 0 else "black"

    st.markdown(
        f"<h2 style='text-align:center;margin-bottom:20px;'>{selected_month_name} {year} "
        f"<span style='color:{total_color};'>(${round(monthly_total,2)})</span></h2>",
        unsafe_allow_html=True
    )

    # TRUE CALENDAR CONTAINER
    calendar_html = """
    <div style='
        border:6px solid black;
        border-radius:20px;
        padding:25px;
        background:white;
        box-shadow:0 6px 14px rgba(0,0,0,0.15);
    '>
    """

    # Headers
    calendar_html += "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:10px;margin-bottom:10px;font-weight:700;'>"
    for h in ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]:
        calendar_html += f"<div style='text-align:center;'>{h}</div>"
    calendar_html += "</div>"

    # Days
    calendar_html += "<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:10px;'>"

    for week in calendar.monthcalendar(year, month):
        for day in week:
            if day == 0:
                calendar_html += "<div style='height:110px;border:1px solid #e2e8f0;border-radius:10px;'></div>"
            else:
                d = date(year, month, day)
                val = totals.get(d, 0)
                bg = "#c6f6d5" if val > 0 else "#fed7d7" if val < 0 else "#edf2f7"

                calendar_html += f"""
                <div style='
                    background:{bg};
                    border-radius:10px;
                    padding:8px;
                    height:110px;
                    border:1px solid #cbd5e0;
                    display:flex;
                    flex-direction:column;
                    justify-content:space-between;
                '>
                    <div style='font-weight:700;font-size:18px;'>{day}</div>
                    <div>${round(val,2)}</div>
                </div>
                """

    calendar_html += "</div></div>"

    st.markdown(calendar_html, unsafe_allow_html=True)
