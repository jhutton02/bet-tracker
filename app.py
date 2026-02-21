import streamlit as st
from datetime import date, timedelta
import calendar
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Bet Tracker", layout="wide")
st.title("Bet Tracker")

UNIT_SIZE = st.number_input("Dollar value per unit", value=100)

# ================= GOOGLE SHEETS SETUP =================

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = st.secrets["gcp_service_account"]
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
gc = gspread.authorize(creds)

# Use your Sheet ID (already set in your app)
SHEET_ID = st.secrets.get("SHEET_ID", None)

if SHEET_ID:
    sheet = gc.open_by_key(SHEET_ID).sheet1
else:
    SHEET_NAME = "Bet Tracker Data"
    sheet = gc.open(SHEET_NAME).sheet1

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

# ================= LOAD DATA =================

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

tab_tracker, tab_add, tab_calendar = st.tabs(["Tracker", "Add Bet", "Calendar"])

# ================= TRACKER TAB =================
with tab_tracker:

    st.subheader("Bet Status Summary")

    open_count = win_count = loss_count = push_count = 0
    open_exposure = 0

    for b in st.session_state.bets:
        if b["result"] == "pending":
            open_count += 1
            open_exposure += b["units"] * UNIT_SIZE
        if b["result"] == "win":
            win_count += 1
        if b["result"] == "loss":
            loss_count += 1
        if b["result"] == "push":
            push_count += 1

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Open Bets", open_count)
    c2.metric("Wins", win_count)
    c3.metric("Losses", loss_count)
    c4.metric("Pushes", push_count)
    c5.metric("Open Exposure ($)", "$" + str(round(open_exposure, 2)))

    st.sidebar.header("Filters")
    sport_filter = st.sidebar.multiselect(
        "Sport", ["NBA","NHL","NFL","MLB","Other"],
        default=["NBA","NHL","NFL","MLB","Other"]
    )
    type_filter = st.sidebar.multiselect(
        "Bet Type", ["Straight","Parlay"],
        default=["Straight","Parlay"]
    )
    result_filter = st.sidebar.multiselect(
        "Result", ["pending","win","loss","push"],
        default=["pending","win","loss","push"]
    )

    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    daily_profit = weekly_profit = monthly_profit = 0

    for b in st.session_state.bets:
        if b["result"] in ["win","loss","push"]:
            if b["date"] == today:
                daily_profit += b["profit"]
            if b["date"] >= week_ago:
                weekly_profit += b["profit"]
            if b["date"] >= month_ago:
                monthly_profit += b["profit"]

    c6, c7, c8 = st.columns(3)
    c6.metric("Today ($)", "$" + str(round(daily_profit, 2)))
    c7.metric("Last 7 Days ($)", "$" + str(round(weekly_profit, 2)))
    c8.metric("Last 30 Days ($)", "$" + str(round(monthly_profit, 2)))

    st.subheader("Bets")
    view_choice = st.radio("View", ["All","Open","Closed"], horizontal=True)

    rows = sheet.get_all_records()

    for i, b in enumerate(st.session_state.bets):
        show = True
        if view_choice == "Open" and b["result"] != "pending":
            show = False
        if view_choice == "Closed" and b["result"] == "pending":
            show = False

        if show and b["sport"] in sport_filter and b["bet_type"] in type_filter and b["result"] in result_filter:

            color = "#c6f6d5" if b["profit"] > 0 else "#fed7d7" if b["profit"] < 0 else "#edf2f7"

            # ✅ TEXT COLOR FORCED TO BLACK
            st.markdown(
                f"<div style='background-color:{color};padding:8px;border-radius:6px;color:#000000;'>"
                f"{b['date']} | {b['sport']} | {b['bet_type']} | {b['bet_line']} | {b['odds']} | {b['result']} | ${round(b['profit'],2)}"
                f"</div>",
                unsafe_allow_html=True
            )

            new_result = st.selectbox(
                "Update Result",
                ["pending","win","loss","push"],
                index=["pending","win","loss","push"].index(b["result"]),
                key="res" + str(i)
            )

            if new_result != b["result"]:
                odds_val = parse_odds(b["odds"])
                b["result"] = new_result
                b["profit"] = calc_profit(b["units"], odds_val, new_result) * UNIT_SIZE
                update_bet(i + 2, b)
                st.rerun()

            if st.button("Delete Bet", key="del" + str(i)):
                delete_bet(i + 2)
                st.session_state.bets = load_bets()
                st.rerun()

# ================= ADD BET TAB =================
with tab_add:

    st.subheader("Add Bet")

    with st.form("add"):
        bet_date = st.date_input("Date", date.today())
        sport = st.selectbox("Sport", ["NBA","NHL","NFL","MLB","Other"])
        bet_type = st.selectbox("Bet Type", ["Straight","Parlay"])
        bet_line = st.text_input("Bet Line (e.g. Mavericks ML)")
        odds_text = st.text_input("Odds")
        units = st.number_input("Units", min_value=0.5, step=0.5)
        result = st.selectbox("Result", ["pending","win","loss","push"])
        submitted = st.form_submit_button("Add Bet")

        if submitted:
            odds = parse_odds(odds_text)
            if odds is None:
                st.error("Invalid odds")
            else:
                profit = calc_profit(units, odds, result) * UNIT_SIZE
                bet = {
                    "date": bet_date,
                    "sport": sport,
                    "bet_type": bet_type,
                    "bet_line": bet_line,
                    "odds": odds_text,
                    "units": units,
                    "result": result,
                    "profit": profit
                }
                save_bet(bet)
                st.session_state.bets = load_bets()
                st.success("Bet added")

# ================= CALENDAR TAB =================
with tab_calendar:

    st.subheader("Monthly Profit Calendar")

    today = date.today()
    year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    month = st.selectbox("Month", list(range(1,13)), index=today.month - 1)

    totals = {}
    monthly_total = 0

    for b in st.session_state.bets:
        if b["result"] in ["win","loss","push"]:
            if b["date"].year == year and b["date"].month == month:
                totals[b["date"]] = totals.get(b["date"], 0) + b["profit"]
                monthly_total += b["profit"]

    color = "green" if monthly_total > 0 else "red" if monthly_total < 0 else "black"
    st.markdown(
        "<h3 style='color:{}'>Monthly Total: ${}</h3>".format(color, round(monthly_total,2)),
        unsafe_allow_html=True
    )

    headers = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    cols = st.columns(7)
    for i in range(7):
        cols[i].markdown("**" + headers[i] + "**")

    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].markdown(
                    "<div style='border:1px solid #e2e8f0;height:80px;border-radius:8px'></div>",
                    unsafe_allow_html=True
                )
            else:
                d = date(year, month, day)
                val = totals.get(d, 0)

                if val > 0:
                    bg = "#c6f6d5"
                elif val < 0:
                    bg = "#fed7d7"
                else:
                    bg = "#edf2f7"

                html = f"""
                <div style="
                    background-color:{bg};
                    color:#000000;
                    border-radius:8px;
                    padding:6px;
                    height:80px;
                    text-align:center;
                    font-weight:600;
                    display:flex;
                    flex-direction:column;
                    justify-content:center;
                    border:1px solid #cbd5e0;
                ">
                    <div>{day}</div>
                    <div>${round(val,2)}</div>
                </div>
                """

                cols[idx].markdown(html, unsafe_allow_html=True)



