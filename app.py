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
        val = str(val).lower().replace(" ", "").strip()

        # Handle "2x", "2.5x"
        if "x" in val:
            return float(val.replace("x", ""))

        # Handle +210
        if val.startswith("+"):
            return float(val)

        # Handle -130
        if val.startswith("-"):
            return float(val)

        # Handle decimal (1.9, 2.1, etc)
        return float(val)

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

    # Decimal / multiplier (2.0, 2.5, etc)
    if odds >= 1:
        return risk * (odds - 1)

    # American +
    if odds > 0:
        return risk * (odds / 100)

    # American -
    if odds < 0:
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

def delete_bet(row):
    sheet.delete_rows(row)

def update_bet(row, bet):
    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), bet["sport"], bet["bet_type"], bet["bet_line"],
        bet["odds"], bet["units"], bet["result"], bet["profit"]
    ]])

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "edit_row" not in st.session_state:
    st.session_state.edit_row = None

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

    days_in_month = calendar.monthrange(year, month)[1]
    selected_day = st.selectbox("Select Day", list(range(1, days_in_month + 1)))
    selected_date = date(year, month, selected_day)

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
                bg = "#16a34a"; tc = "white"
            elif val < 0:
                bg = "#dc2626"; tc = "white"
            else:
                bg = "#f1f5f9"; tc = "black"

            cols[i].markdown(f"""
            <div style="background:{bg};color:{tc};padding:12px;border-radius:14px;height:100px;">
                <b>{day}</b><br>
                ${round(val,2)}<br>
                {cnt} bets
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader(f"Bets for {selected_date}")

    day_bets = [b for b in st.session_state.bets if b["date"] == selected_date]

    if not day_bets:
        st.info("No bets for this day")
    else:
        for b in day_bets:
            st.markdown(f"""
            <div style='background:#f1f5f9;padding:10px;border-radius:10px;margin-bottom:6px'>
            {b['bet_line']} | {b['result']} | ${round(b['profit'],2)}
            </div>
            """, unsafe_allow_html=True)

# ================= ADD BET =================
with t2:
    with st.form("add"):
        bet_date = st.date_input("Date", date.today())
        sport = st.selectbox("Sport", ["NBA","NFL","MLB","NHL","Other"])
        bet_type = st.selectbox("Bet Type", ["Straight","Parlay"])
        wager = st.text_input("Wager")
        odds = st.text_input("Odds (e.g. -130, +210, 2x, 2.5)")
        risk = st.number_input("Risk ($)", value=100.0)
        result = st.selectbox("Result", ["pending","win","loss","push"])

        if st.form_submit_button("Add Bet"):
            parsed_odds = safe_parse_odds(odds)
            profit = calc_profit(risk, parsed_odds, result)

            bet = {
                "date": bet_date,
                "sport": sport,
                "bet_type": bet_type,
                "bet_line": wager,
                "odds": odds,  # store raw input
                "units": risk,
                "result": result,
                "profit": profit
            }

            save_bet(bet)
            st.session_state.bets = load_bets()
            st.success("Bet added")

# ================= TRACKER =================
with t3:

    for b in sorted(st.session_state.bets, key=lambda x: x["date"], reverse=True):

        if b["profit"] > 0:
            bg = "#d1fae5"
        elif b["profit"] < 0:
            bg = "#fee2e2"
        else:
            bg = "#f1f5f9"

        col1, col2, col3 = st.columns([6,1,1])

        with col1:
            st.markdown(f"""
            <div style='background:{bg};padding:12px;border-radius:12px;margin-bottom:10px'>
            <b>{b['date']}</b> | {b['sport']} | {b['bet_type']}<br>
            <b>Wager:</b> {b['bet_line']} | {b['result']}<br>
            Odds: {b['odds']}<br>
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

    # EDIT FORM
    if st.session_state.edit_row:
        st.divider()
        st.subheader("Edit Bet")

        bet = next(b for b in st.session_state.bets if b["row"] == st.session_state.edit_row)

        with st.form("edit"):
            new_wager = st.text_input("Wager", bet["bet_line"])
            new_odds = st.text_input("Odds", str(bet["odds"]))
            new_risk = st.number_input("Risk ($)", value=bet["units"])
            new_result = st.selectbox("Result", ["pending","win","loss","push"], index=["pending","win","loss","push"].index(bet["result"]))

            if st.form_submit_button("Save"):
                parsed_odds = safe_parse_odds(new_odds)
                profit = calc_profit(new_risk, parsed_odds, new_result)

                updated = {
                    "date": bet["date"],
                    "sport": bet["sport"],
                    "bet_type": bet["bet_type"],
                    "bet_line": new_wager,
                    "odds": new_odds,
                    "units": new_risk,
                    "result": new_result,
                    "profit": profit
                }

                update_bet(bet["row"], updated)
                st.session_state.edit_row = None
                st.session_state.bets = load_bets()
                st.success("Updated")
                st.rerun()
