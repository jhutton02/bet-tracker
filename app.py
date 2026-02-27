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

    # Mobile-friendly stacked metrics
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    c1.metric("Open Bets", open_count)
    c2.metric("Wins", win_count)
    c3.metric("Losses", loss_count)
    c4.metric("Pushes", push_count)

    st.metric("Open Exposure ($)", "$" + str(round(open_exposure, 2)))

    st.subheader("Filters")

    sport_filter = st.multiselect(
        "Sport", ["NBA","NHL","NFL","MLB","Other"],
        default=["NBA","NHL","NFL","MLB","Other"]
    )
    type_filter = st.multiselect(
        "Bet Type", ["Straight","Parlay"],
        default=["Straight","Parlay"]
    )
    result_filter = st.multiselect(
        "Result", ["pending","win","loss","push"],
        default=["pending","win","loss","push"]
    )

    st.subheader("Bets")
    view_choice = st.radio("View", ["All","Open","Closed"], horizontal=True)

    for i, b in enumerate(st.session_state.bets):
        show = True
        if view_choice == "Open" and b["result"] != "pending":
            show = False
        if view_choice == "Closed" and b["result"] == "pending":
            show = False

        if show and b["sport"] in sport_filter and b["bet_type"] in type_filter and b["result"] in result_filter:

            color = "#c6f6d5" if b["profit"] > 0 else "#fed7d7" if b["profit"] < 0 else "#edf2f7"

            st.markdown(
                f"<div style='background-color:{color};padding:14px;border-radius:10px;color:#000000;margin-bottom:10px;'>"
                f"{b['date']} | {b['sport']} | {b['bet_type']}<br>"
                f"{b['bet_line']} | {b['odds']} | {b['result']}<br>"
                f"<b>${round(b['profit'],2)}</b>"
                f"</div>",
                unsafe_allow_html=True
            )

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
