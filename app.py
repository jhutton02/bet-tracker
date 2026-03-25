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
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPES
)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1ckrXeP6LZpLSVdbRV1-02kj0WuKj603Q8_kDoqCVh9Q").sheet1

# ================= HELPERS =================

def safe_parse_odds(val):
    try:
        return float(str(val).replace("x", "").strip())
    except:
        return 0.0

def calc_to_win(risk, odds):
    return risk * (odds - 1)

def calc_odds(risk, to_win):
    if risk == 0:
        return 0
    return (to_win / risk) + 1

def calc_profit(risk, odds, result):
    result = str(result).lower()
    if result == "win":
        return risk * (odds - 1)
    elif result == "loss":
        return -risk
    else:
        return 0

def parse_date_safe(val):
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        return None

def load_bets():
    rows = sheet.get_all_records()
    bets = []

    for i, r in enumerate(rows, start=2):
        risk = float(r.get("risk", r.get("units", 0)))  # ✅ handles old data

        bets.append({
            "row": i,
            "date": parse_date_safe(r["date"]),
            "sport": r["sport"],
            "bet_type": r["bet_type"],
            "bet_line": r["bet_line"],
            "odds": r["odds"],
            "risk": risk,
            "result": r["result"]
        })

    return bets

def save_bet(bet):
    sheet.append_row([
        str(bet["date"]),
        bet["sport"],
        bet["bet_type"],
        bet["bet_line"],
        bet["odds"],
        bet["risk"],
        bet["result"],
        bet["profit"]
    ])

# ================= STATE =================
if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

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
        odds = safe_parse_odds(b["odds"])
        profit = calc_profit(b["risk"], odds, b["result"])

        st.markdown(f"""
        **{b['sport']} | {b['bet_type']}**  
        {b['bet_line']}  
        Odds: {b['odds']}  
        Risk: ${b['risk']}  
        Profit: ${round(profit,2)}
        """)

# ================= TRACKER =================
with t3:
    bets = st.session_state.bets

    total_risk = sum(b["risk"] for b in bets)
    total_profit = sum(
        calc_profit(b["risk"], safe_parse_odds(b["odds"]), b["result"])
        for b in bets
    )

    st.metric("Total Risk", f"${round(total_risk,2)}")
    st.metric("Total Profit", f"${round(total_profit,2)}")

    if bets:
        dates = []
        running_total = []
        total = 0

        for b in bets:
            profit = calc_profit(b["risk"], safe_parse_odds(b["odds"]), b["result"])
            total += profit
            dates.append(b["date"])
            running_total.append(total)

        fig, ax = plt.subplots()
        ax.plot(dates, running_total)
        ax.axhline(0, linestyle="--")

        st.pyplot(fig)
