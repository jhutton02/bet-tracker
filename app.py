import streamlit as st
from datetime import date, timedelta, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt

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
        if val.startswith("+") or val.startswith("-"):
            return float(val)
        return float(val)
    except:
        return 0.0

def calc_odds(risk, to_win):
    if risk == 0:
        return 0
    return (to_win / risk) + 1

def calc_to_win(risk, odds):
    return risk * (odds - 1) if odds >= 1 else 0

def format_odds_display(val):
    try:
        raw = str(val).lower().strip()
        if "x" in raw:
            return raw
        if raw.startswith("+") or raw.startswith("-"):
            return raw
        num = float(raw)
        if num >= 1:
            return f"{num}x"
        return raw
    except:
        return val

def calc_profit(risk, odds, result):
    result = str(result).lower().strip()
    if result == "pending":
        return 0
    if result == "loss":
        return -risk
    if result == "push":
        return 0
    if odds >= 1:
        return risk * (odds - 1)
    if odds > 0:
        return risk * (odds / 100)
    if odds < 0:
        return risk * (100 / abs(odds))
    return 0

def parse_date_safe(val):
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        try:
            return datetime.strptime(str(val), "%m/%d/%Y").date()
        except:
            return None

# ================= 🔑 FIX IS HERE =================
def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for i, r in enumerate(rows, start=2):
        odds = safe_parse_odds(r["odds"])

        # 🔥 STANDARDIZE HERE
        risk = float(r.get("risk", r.get("units", 0)))

        result = str(r["result"]).lower().strip()
        profit = calc_profit(risk, odds, result)

        bets.append({
            "row": i,
            "date": parse_date_safe(r["date"]),
            "sport": r["sport"],
            "bet_type": r["bet_type"],
            "bet_line": r["bet_line"],
            "odds": r["odds"],
            "risk": risk,   # ALWAYS risk now
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

if "edit_row" not in st.session_state:
    st.session_state.edit_row = None

# ================= TABS =================
t1, t2, t3 = st.tabs(["📅 Calendar", "➕ Add Bet", "📋 Tracker"])

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
            st.success("Bet added")
            st.rerun()

# ================= CALENDAR =================
with t1:
    st.subheader("Bets")

    for b in st.session_state.bets:
        st.markdown(f"""
        **{b['sport']} | {b['bet_type']}**  
        {b['bet_line']}  
        Odds: {b['odds']}  
        Risk: ${b['risk']}  
        Profit: ${round(b['profit'],2)}
        """)

# ================= TRACKER =================
with t3:
    bets = st.session_state.bets

    total_risk = sum(b["risk"] for b in bets)
    total_profit = sum(b["profit"] for b in bets)

    st.metric("Total Risk", f"${round(total_risk,2)}")
    st.metric("Total Profit", f"${round(total_profit,2)}")
