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

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    with col2:
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Month", month_names, index=today.month - 1)

    month = month_names.index(selected_month_name) + 1

    days_in_month = calendar.monthrange(year, month)[1]
    day_options = [f"{month}/{d}" for d in range(1, days_in_month + 1)]
    selected_label = st.selectbox("Select Day", day_options)
    selected_day = int(selected_label.split("/")[1])
    selected_date = date(year, month, selected_day)

    totals = {}
    counts = {}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year == year and b["date"].month == month:
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
                <b>{day}</b><br>${round(val,2)}<br>{cnt} bets
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.subheader(f"Bets for {selected_date}")

    day_bets = [b for b in st.session_state.bets if b["date"] == selected_date]

    if not day_bets:
        st.info("No bets for this day")
    else:
        for b in day_bets:
            col1, col2, col3 = st.columns([8,1,1])

            with col1:
                st.markdown(f"""
                <div style='background:#f1f5f9;padding:12px;border-radius:12px;margin-bottom:8px'>
                <b>{b['sport']} | {b['bet_type']}</b><br>
                {b['bet_line']} | {b['result']}<br>
                Odds: {format_odds_display(b['odds'])}<br>
                <b>${round(b['profit'],2)}</b>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button("✏️", key=f"cal_edit_{b['row']}"):
                    st.session_state.edit_row = b["row"]

            with col3:
                if st.button("❌", key=f"cal_del_{b['row']}"):
                    delete_bet(b["row"])
                    st.session_state.bets = load_bets()
                    st.rerun()

            if st.session_state.edit_row == b["row"]:
                with st.form(f"edit_form_{b['row']}"):
                    new_wager = st.text_input("Wager", b["bet_line"])
                    new_odds = st.text_input("Odds", b["odds"])
                    new_units = st.number_input("Units", value=b["units"])
                    new_result = st.selectbox(
                        "Result",
                        ["pending","win","loss","push"],
                        index=["pending","win","loss","push"].index(b["result"])
                    )

                    if st.form_submit_button("Save"):
                        parsed_odds = safe_parse_odds(new_odds)
                        profit = calc_profit(new_units, parsed_odds, new_result)

                        updated_bet = {
                            "date": b["date"],
                            "sport": b["sport"],
                            "bet_type": b["bet_type"],
                            "bet_line": new_wager,
                            "odds": new_odds,
                            "units": new_units,
                            "result": new_result,
                            "profit": profit
                        }

                        update_bet(b["row"], updated_bet)
                        st.session_state.bets = load_bets()
                        st.session_state.edit_row = None
                        st.rerun()

# ================= ADD BET =================
with t2:
    with st.form("add"):
        bet_date = st.date_input("Date", date.today())
        sport = st.selectbox("Sport", ["NBA","NFL","MLB","NHL","Other"])
        bet_type = st.selectbox("Bet Type", ["Straight","Parlay"])
        wager = st.text_input("Wager")
        odds = st.text_input("Odds")
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
                "odds": odds,
                "units": risk,
                "result": result,
                "profit": profit
            }

            save_bet(bet)
            st.session_state.bets = load_bets()
            st.success("Bet added")
            st.rerun()

# ================= TRACKER =================
with t3:

    bets = st.session_state.bets

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    daily = sum(b["profit"] for b in bets if b["date"] == today)
    weekly = sum(b["profit"] for b in bets if b["date"] >= week_start)
    monthly = sum(b["profit"] for b in bets if b["date"] >= month_start)
    yearly = sum(b["profit"] for b in bets if b["date"] >= year_start)

    def color(val):
        return "#16a34a" if val > 0 else "#dc2626" if val < 0 else "#374151"

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val in zip(
        [c1, c2, c3, c4],
        ["Day", "Week", "Month", "Year"],
        [daily, weekly, monthly, yearly]
    ):
        col.markdown(f"""
        <div style='background:#ffffff;padding:14px;border-radius:12px;border:1px solid rgba(0,0,0,0.08);text-align:center;'>
            <div style='font-size:14px;color:#6b7280'>{label}</div>
            <div style='font-size:20px;font-weight:bold;color:{color(val)}'>
                ${round(val,2)}
            </div>
        </div>
        """, unsafe_allow_html=True)

    total_bets = len(bets)
    wins = sum(1 for b in bets if b["profit"] > 0)
    total_risk = sum(b["units"] for b in bets)
    total_profit = sum(b["profit"] for b in bets)

    win_pct = (wins / total_bets * 100) if total_bets else 0
    roi = (total_profit / total_risk * 100) if total_risk else 0

    m1, m2, m3 = st.columns(3)

    m1.metric("Win %", f"{round(win_pct,1)}%")
    m2.metric("ROI %", f"{round(roi,1)}%")
    m3.metric("Total Bets", total_bets)

    if bets:
        sorted_bets = sorted(bets, key=lambda x: x["date"])
        dates = []
        running_total = []
        total = 0

        for b in sorted_bets:
            total += b["profit"]
            dates.append(b["date"])
            running_total.append(total)

        fig, ax = plt.subplots()

        ax.plot(dates, running_total, linewidth=2.5)
        ax.fill_between(dates, running_total, where=[v >= 0 for v in running_total], alpha=0.15)
        ax.fill_between(dates, running_total, where=[v < 0 for v in running_total], alpha=0.15)

        ax.axhline(0, linestyle="--", linewidth=1)
        ax.set_title("Profit Over Time", fontsize=13, pad=10)
        ax.set_ylabel("Total Profit ($)")
        ax.set_xlabel("Date")

        tick_dates = dates[::max(1, len(dates)//6)]
        tick_labels = [f"{d.month}/{d.day}" for d in tick_dates]

        ax.set_xticks(tick_dates)
        ax.set_xticklabels(tick_labels)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.grid(alpha=0.2)

        plt.tight_layout()
        st.pyplot(fig)

    st.divider()
