import streamlit as st
from datetime import date, timedelta
import calendar
import json
import os

DATA_FILE = "bets.json"

st.title("Bet Tracker")

UNIT_SIZE = st.number_input("Dollar value per unit", value=100)

# ---------- SAVE / LOAD ----------
def load_bets():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            for b in data:
                b["date"] = date.fromisoformat(b["date"])
            return data
    return []

def save_bets():
    data = []
    for b in st.session_state.bets:
        b_copy = b.copy()
        b_copy["date"] = b_copy["date"].isoformat()
        data.append(b_copy)
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ---------- HELPERS ----------
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

# ---------- STATE ----------
if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

tab_tracker, tab_add, tab_calendar = st.tabs(["Tracker", "Add Bet", "Calendar"])

# ================= TRACKER TAB =================
with tab_tracker:
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

    st.subheader("Bet Status Summary")

    open_count = win_count = loss_count = push_count = 0
    open_exposure = 0
    total_profit = 0
    total_risked = 0
    settled = []

    for b in st.session_state.bets:
        if b["result"] == "pending":
            open_count += 1
            open_exposure += b["units"] * UNIT_SIZE
        else:
            total_profit += b["profit"]
            total_risked += b["units"] * UNIT_SIZE
            settled.append(b)

        if b["result"] == "win":
            win_count += 1
        if b["result"] == "loss":
            loss_count += 1
        if b["result"] == "push":
            push_count += 1

    # ---- STREAKS ----
    current_streak = "-"
    longest_win = 0
    longest_loss = 0
    streak = 0
    streak_type = None

    for b in sorted(settled, key=lambda x: x["date"]):
        if b["result"] == "win":
            streak = streak + 1 if streak_type == "win" else 1
            streak_type = "win"
            longest_win = max(longest_win, streak)
        elif b["result"] == "loss":
            streak = streak + 1 if streak_type == "loss" else 1
            streak_type = "loss"
            longest_loss = max(longest_loss, streak)
        else:
            streak = 0
            streak_type = None

    if streak_type:
        current_streak = ("W" if streak_type == "win" else "L") + str(streak)

    win_rate = (win_count / (win_count + loss_count)) * 100 if (win_count + loss_count) else 0
    roi = (total_profit / total_risked) * 100 if total_risked else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Open Bets", open_count)
    c2.metric("Wins", win_count)
    c3.metric("Losses", loss_count)
    c4.metric("Pushes", push_count)
    c5.metric("Open Exposure ($)", f"${round(open_exposure,2)}")

    c6, c7, c8, c9, c10 = st.columns(5)
    c6.metric("Win Rate", f"{round(win_rate,1)}%")
    c7.metric("ROI", f"{round(roi,1)}%")
    c8.metric("Current Streak", current_streak)
    c9.metric("Best Win Streak", longest_win)
    c10.metric("Worst Loss Streak", longest_loss)

    st.subheader("Bets")
    view_choice = st.radio("View", ["All","Open","Closed"], horizontal=True)

    for i, b in enumerate(st.session_state.bets):
        show = True
        if view_choice == "Open" and b["result"] != "pending":
            show = False
        if view_choice == "Closed" and b["result"] == "pending":
            show = False

        if show and b["sport"] in sport_filter and b["bet_type"] in type_filter and b["result"] in result_filter:
            bg = (
                "#e6fffa" if b["result"] == "win"
                else "#ffe4e6" if b["result"] == "loss"
                else "#fff9db" if b["result"] == "push"
                else "#edf2f7"
            )

            st.markdown(
                f"""
                <div style="background:{bg};padding:10px;border-radius:8px;margin-bottom:6px;">
                <strong>{b['date']}</strong> | {b['sport']} | {b['bet_type']} |
                {b['bet_line']} | {b['odds']} | <strong>{b['result'].upper()}</strong> |
                ${round(b['profit'],2)}
                </div>
                """,
                unsafe_allow_html=True
            )

            new_result = st.selectbox(
                "Update Result",
                ["pending","win","loss","push"],
                index=["pending","win","loss","push"].index(b["result"]),
                key=f"res{i}"
            )

            if new_result != b["result"]:
                odds_val = parse_odds(b["odds"])
                b["result"] = new_result
                b["profit"] = calc_profit(b["units"], odds_val, new_result) * UNIT_SIZE
                save_bets()
                st.rerun()

            if st.button("Delete Bet", key=f"del{i}"):
                del st.session_state.bets[i]
                save_bets()
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
                st.session_state.bets.append({
                    "date": bet_date,
                    "sport": sport,
                    "bet_type": bet_type,
                    "bet_line": bet_line,
                    "odds": odds_text,
                    "units": units,
                    "result": result,
                    "profit": profit
                })
                save_bets()
                st.success("Bet added")

# ================= CALENDAR TAB =================
with tab_calendar:
    st.subheader("Monthly Profit Calendar")

    today = date.today()
    year = st.selectbox("Year", [today.year-1, today.year, today.year+1], index=1)
    month = st.selectbox("Month", list(range(1,13)), index=today.month-1)

    totals = {}
    monthly_total = 0

    for b in st.session_state.bets:
        if b["result"] in ["win","loss","push"]:
            if b["date"].year == year and b["date"].month == month:
                totals[b["date"]] = totals.get(b["date"], 0) + b["profit"]
                monthly_total += b["profit"]

    color = "green" if monthly_total > 0 else "red" if monthly_total < 0 else "black"
    st.markdown(
        f"<h3 style='color:{color}'>Monthly Total: ${round(monthly_total,2)}</h3>",
        unsafe_allow_html=True
    )

    headers = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    cols = st.columns(7)
    for i in range(7):
        cols[i].markdown(f"**{headers[i]}**")

    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for idx, day in enumerate(week):
            if day == 0:
                cols[idx].markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
            else:
                d = date(year, month, day)
                val = totals.get(d, 0)
                bg = "#c6f6d5" if val > 0 else "#feb2b2" if val < 0 else "#edf2f7"

                box = f"""
                <div style="
                    background:{bg};
                    border:1px solid #cbd5e0;
                    height:80px;
                    border-radius:8px;
                    text-align:center;
                    padding-top:10px;
                    font-weight:600;
                ">
                    {day}<br>${round(val,2)}
                </div>
                """

                if cols[idx].button(" ", key=str(d)):
                    st.session_state.selected_day = d
                cols[idx].markdown(box, unsafe_allow_html=True)

    if st.session_state.selected_day:
        st.markdown("---")
        st.subheader(f"Bets on {st.session_state.selected_day}")
        found = False
        for b in st.session_state.bets:
            if b["date"] == st.session_state.selected_day:
                found = True
                st.write(
                    f"{b['sport']} | {b['bet_type']} | {b['bet_line']} | "
                    f"{b['odds']} | {b['result']} | ${round(b['profit'],2)}"
                )
        if not found:
            st.info("No bets on this day.")
