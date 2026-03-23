import streamlit as st
from datetime import date
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

# ================= TABS =================
t1, t2 = st.tabs(["📋 Tracker", "➕ Add Bet"])

# ================= TRACKER =================
with t1:

    view = st.radio("View", ["All", "Open", "Closed"], horizontal=True)

    bets = st.session_state.bets

    if view == "Open":
        bets = [b for b in bets if b["result"] == "pending"]
    elif view == "Closed":
        bets = [b for b in bets if b["result"] != "pending"]

    bets = sorted(bets, key=lambda x: x["date"], reverse=True)

    total_profit = sum(b["profit"] for b in bets)
    total_units = sum(
        b["units"] if b["result"] == "win"
        else -b["units"] if b["result"] == "loss"
        else 0 for b in bets
    )

    wins = sum(1 for b in bets if b["result"] == "win")
    losses = sum(1 for b in bets if b["result"] == "loss")
    closed = wins + losses
    winrate = (wins / closed * 100) if closed else 0

    total_risk = sum(abs(b["units"]) * UNIT_SIZE for b in bets)
    roi = (total_profit / total_risk * 100) if total_risk else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Profit", f"${round(total_profit,2)}")
    c2.metric("Units", round(total_units,2))
    c3.metric("ROI", f"{round(roi,1)}%")

    st.metric("Win Rate", f"{round(winrate,1)}%")

    st.divider()

    for b in bets:
        color = "#d1fae5" if b["profit"] > 0 else "#fee2e2" if b["profit"] < 0 else "#f1f5f9"

        with st.container():
            cols = st.columns([6,1,1])

            with cols[0]:
                st.markdown(f"""
                <div style='background:{color};padding:12px;border-radius:10px'>
                <b>{b['date']}</b> | {b['sport']} | {b['bet_type']}<br>
                {b['bet_line']} | {b['odds']} | {b['result']}<br>
                <b>${round(b['profit'],2)}</b>
                </div>
                """, unsafe_allow_html=True)

            with cols[1]:
                if st.button("✏️", key=f"edit_{b['row']}"):
                    st.session_state.editing = b

            with cols[2]:
                if st.button("❌", key=f"del_{b['row']}"):
                    delete_bet(b["row"])
                    st.session_state.bets = load_bets()
                    st.rerun()

    # EDIT FORM
    if "editing" in st.session_state:
        st.subheader("Edit Bet")
        b = st.session_state.editing

        with st.form("edit_form"):
            new_units = st.number_input("Units", value=b["units"])
            new_result = st.selectbox(
                "Result",
                ["pending","win","loss","push"],
                index=["pending","win","loss","push"].index(b["result"])
            )

            submit = st.form_submit_button("Save Changes")

            if submit:
                new_profit = calc_profit(new_units, b["odds"], new_result) * UNIT_SIZE

                b["units"] = new_units
                b["result"] = new_result
                b["profit"] = new_profit

                update_bet(b["row"], b)
                st.session_state.bets = load_bets()
                del st.session_state.editing
                st.rerun()

# ================= ADD BET =================
with t2:

    with st.form("add"):
        bet_date = st.date_input("Date", date.today())
        sport = st.selectbox("Sport", ["NBA","NFL","MLB","NHL","Other"])
        bet_type = st.selectbox("Bet Type", ["Straight","Parlay"])
        bet_line = st.text_input("Bet Line")
        odds = st.number_input("Odds", value=1.9)
        units = st.number_input("Units", value=1.0)
        result = st.selectbox("Result", ["pending","win","loss","push"])

        if st.form_submit_button("Add Bet"):
            profit = calc_profit(units, odds, result) * UNIT_SIZE

            bet = {
                "date": bet_date,
                "sport": sport,
                "bet_type": bet_type,
                "bet_line": bet_line,
                "odds": odds,
                "units": units,
                "result": result,
                "profit": profit
            }

            save_bet(bet)
            st.session_state.bets = load_bets()
            st.success("Bet added")
