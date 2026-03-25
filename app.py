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
        return float(val)
    except:
        return 0.0

def format_odds_display(val):
    try:
        raw = str(val).lower().strip()
        if "x" in raw:
            return raw
        return f"{float(raw)}x"
    except:
        return val

def calc_profit(risk, odds, result):
    result = str(result).lower().strip()
    if result == "pending":
        return 0
    if result == "loss":
        return -risk
    if odds >= 1:
        return risk * (odds - 1)
    return 0

def parse_date_safe(val):
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        return datetime.strptime(str(val), "%m/%d/%Y").date()

def result_badge(result):
    colors = {
        "win": ("#16a34a","white"),
        "loss": ("#dc2626","white"),
        "pending": ("#facc15","black")
    }
    bg, color = colors.get(result, ("#64748b","white"))
    return f"<span style='background:{bg};color:{color};padding:3px 8px;border-radius:999px;font-size:11px;font-weight:600;'>{result.upper()}</span>"

# ================= DATA =================
def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for i, r in enumerate(rows, start=2):
        odds = safe_parse_odds(r["odds"])
        risk = float(r["units"])
        result = str(r["result"]).lower()
        profit = calc_profit(risk, odds, result)

        bets.append({
            "row": i,
            "date": parse_date_safe(r["date"]),
            "sport": r["sport"],
            "bet_type": r["bet_type"],
            "bet_line": r["bet_line"],
            "odds": r["odds"],
            "units": risk,
            "result": result,
            "profit": profit
        })
    return bets

def update_bet(row, bet):
    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), bet["sport"], bet["bet_type"], bet["bet_line"],
        bet["odds"], bet["units"], bet["result"], bet["profit"]
    ]])

def delete_bet(row):
    sheet.delete_rows(row)

# ================= STATE =================
if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "edit_row" not in st.session_state:
    st.session_state.edit_row = None

# ================= TABS =================
t1, t2, t3 = st.tabs(["📅 Calendar", "➕ Add Bet", "📋 Tracker"])

# ================= CALENDAR =================
with t1:

    today = date.today()

    year = st.selectbox("Year", [today.year-1, today.year, today.year+1], index=1)
    month = st.selectbox("Month", list(calendar.month_name)[1:], index=today.month-1)
    month_num = list(calendar.month_name).index(month)

    selected_day = st.selectbox("Select Day", list(range(1,32)))
    selected_date = date(year, month_num, selected_day)

    # ✅ CALENDAR GRID RESTORED
    for week in calendar.monthcalendar(year, month_num):
        cols = st.columns(7)
        for i, d in enumerate(week):
            if d == 0:
                continue
            cols[i].markdown(f"**{d}**")

    st.divider()
    st.subheader(f"Bets for {selected_date}")

    day_bets = [b for b in st.session_state.bets if b["date"] == selected_date]

    for b in day_bets:
        col1, col2, col3 = st.columns([8,1,1])

        with col1:
            st.markdown(f"""
            <div style='background:#f1f5f9;padding:12px;border-radius:12px;margin-bottom:8px'>
            <b>{b['sport']} | {b['bet_type']}</b><br>
            {b['bet_line']} {result_badge(b['result'])}<br>
            Odds: {format_odds_display(b['odds'])}<br>
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

        # ✅ EDIT FIXED
        if st.session_state.edit_row == b["row"]:
            with st.form(f"edit_form_{b['row']}"):
                new_result = st.selectbox("Result", ["pending","win","loss"])
                if st.form_submit_button("Save"):
                    b["result"] = new_result
                    update_bet(b["row"], b)
                    st.session_state.bets = load_bets()
                    st.session_state.edit_row = None
                    st.rerun()

# ================= TRACKER =================
with t3:

    bets = st.session_state.bets

    dates = [b["date"] for b in bets]
    profits = []
    total = 0

    for b in sorted(bets, key=lambda x: x["date"]):
        total += b["profit"]
        profits.append(total)

    # ✅ GRAPH FIXED (clean labels)
    fig, ax = plt.subplots()
    ax.plot(dates, profits)

    ax.set_xticks(dates[::max(1,len(dates)//5)])
    ax.set_xticklabels([d.strftime("%m/%d") for d in dates[::max(1,len(dates)//5)]])

    st.pyplot(fig)
