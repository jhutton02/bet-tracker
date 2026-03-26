import streamlit as st
from datetime import date, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import requests

st.set_page_config(page_title="Bet Tracker", layout="centered")
st.title("📊 Bet Tracker Pro")

# ================= GOOGLE =================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
gc = gspread.authorize(creds)
sheet = gc.open_by_key("1ckrXeP6LZpLSVdbRV1-02kj0WuKj603Q8_kDoqCVh9Q").sheet1

# ================= HELPERS =================
def safe_parse_odds(val):
    try:
        return float(str(val).replace("x",""))
    except:
        return 0

def calc_odds(risk, to_win):
    return (to_win / risk) + 1 if risk != 0 else 0

def calc_profit(risk, odds, result):
    if result == "win":
        return risk * (odds - 1)
    elif result == "loss":
        return -risk
    return 0

def parse_date(val):
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        return None

# ================= DATA =================
def load_bets():
    rows = sheet.get_all_records()
    bets = []

    for i, r in enumerate(rows, start=2):
        risk = float(r.get("risk", 0))
        odds_val = safe_parse_odds(r.get("odds", 0))
        result = str(r.get("result", "pending")).lower()

        profit = calc_profit(risk, odds_val, result)

        bets.append({
            "row": i,
            "date": parse_date(r.get("date")),
            "bet_line": r.get("bet_line", ""),
            "odds": f"{odds_val}x",
            "risk": risk,
            "result": result,
            "profit": profit
        })

    return bets

def save_bet(b):
    odds_val = safe_parse_odds(b["odds"])
    profit = calc_profit(b["risk"], odds_val, b["result"])

    sheet.append_row([
        str(b["date"]), "", "", b["bet_line"],
        b["odds"], b["risk"], b["result"], profit
    ])

def update_bet(row, bet):
    odds_val = safe_parse_odds(bet["odds"])
    profit = calc_profit(bet["risk"], odds_val, bet["result"])

    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), "", "", bet["bet_line"],
        f"{round(odds_val,2)}x",
        bet["risk"],
        bet["result"],
        profit
    ]])

    st.session_state.bets = load_bets()

def delete_bet(row):
    sheet.delete_rows(row)

# ================= LIVE =================
def get_player_points(name):
    try:
        url=f"https://www.balldontlie.io/api/v1/players?search={name}"
        res=requests.get(url).json()
        if not res["data"]:
            return 0
        pid=res["data"][0]["id"]

        stats=requests.get(f"https://www.balldontlie.io/api/v1/stats?player_ids[]={pid}&per_page=1").json()
        if not stats["data"]:
            return 0

        g=stats["data"][0]
        return g["pts"]+g["reb"]+g["ast"]
    except:
        return 0

# ================= STATE =================
if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "edit_row" not in st.session_state:
    st.session_state.edit_row = None

if "live_slips" not in st.session_state:
    st.session_state.live_slips = []

# ================= TABS =================
t1, t2, t3, t4 = st.tabs(["📅 Calendar","➕ Add Bet","📋 Tracker","🔥 Live Tracker"])

# ================= CALENDAR =================
with t1:
    today = date.today()

    col1, col2 = st.columns(2)
    year = col1.selectbox("Year",[today.year])
    month_names = list(calendar.month_name)[1:]
    month_name = col2.selectbox("Month", month_names, index=today.month-1)
    month = month_names.index(month_name)+1

    totals={}
    counts={}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year==year and b["date"].month==month:
            d=b["date"]
            totals[d]=totals.get(d,0)+b["profit"]
            counts[d]=counts.get(d,0)+1

    for week in calendar.monthcalendar(year,month):
        cols=st.columns(7)
        for i,day in enumerate(week):
            if day==0: continue

            d=date(year,month,day)
            val=totals.get(d,0)
            cnt=counts.get(d,0)

            if val>0:
                bg="#16a34a"; tc="white"
            elif val<0:
                bg="#dc2626"; tc="white"
            else:
                bg="#f1f5f9"; tc="black"

            if cols[i].button("", key=f"click{day}"):
                st.session_state.selected_date=d

            cols[i].markdown(f"""
            <div style="background:{bg};color:{tc};padding:12px;border-radius:12px;height:100px;">
            <b>{day}</b><br>
            <div style="font-size:18px;font-weight:700;">${round(val,2)}</div>
            <div style="font-size:12px;">{cnt} bets</div>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    st.subheader(f"Bets for {st.session_state.selected_date}")

    for b in st.session_state.bets:
        if b["date"] == st.session_state.selected_date:

            c1,c2,c3=st.columns([6,1,1])

            c1.write(f"{b['bet_line']} | {b['odds']} | ${round(b['profit'],2)}")

            if c2.button("✏️", key=f"edit{b['row']}"):
                st.session_state.edit_row=b["row"]

            if c3.button("❌", key=f"del{b['row']}"):
                delete_bet(b["row"])
                st.session_state.bets=load_bets()
                st.rerun()

            if st.session_state.edit_row==b["row"]:
                with st.form(f"form{b['row']}"):
                    wager=st.text_input("Wager",b["bet_line"])
                    risk=st.number_input("Risk",value=b["risk"])
                    odds_val=safe_parse_odds(b["odds"])
                    to_win=st.number_input("To Win",value=risk*(odds_val-1))
                    new_odds=calc_odds(risk,to_win)

                    st.write(f"Odds: {round(new_odds,2)}x")

                    result=st.selectbox("Result",["pending","win","loss"])

                    if st.form_submit_button("Save"):
                        update_bet(b["row"],{
                            "date":b["date"],
                            "bet_line":wager,
                            "odds":f"{round(new_odds,2)}x",
                            "risk":risk,
                            "result":result
                        })
                        st.session_state.edit_row=None
                        st.session_state.bets = load_bets()
                        st.rerun()

# ================= ADD =================
with t2:
    with st.form("add"):
        d=st.date_input("Date")
        wager=st.text_input("Wager")
        risk=st.number_input("Risk",value=100.0)
        to_win=st.number_input("To Win",value=100.0)

        odds=calc_odds(risk,to_win)
        st.write(f"Odds: {round(odds,2)}x")

        result=st.selectbox("Result",["pending","win","loss"])

        if st.form_submit_button("Add"):
            save_bet({
                "date":d,
                "bet_line":wager,
                "odds":f"{round(odds,2)}x",
                "risk":risk,
                "result":result
            })
            st.session_state.bets=load_bets()
            st.rerun()

# ================= TRACKER =================
with t3:
    bets=st.session_state.bets

    total_profit=sum(b["profit"] for b in bets)
    st.metric("Total Profit",f"${round(total_profit,2)}")

    if bets:
        dates=[b["date"] for b in bets if b["date"]]
        profits=[b["profit"] for b in bets if b["date"]]

        running=[]
        total=0
        for p in profits:
            total+=p
            running.append(total)

        fig, ax = plt.subplots()
        ax.plot(dates, running)
        ax.axhline(0, linestyle="--")
        st.pyplot(fig)

# ================= LIVE =================
with t4:
    with st.form("live"):
        player=st.text_input("Player")
        bet_type=st.selectbox("Type",["Points","Rebounds","Assists","PRA"])
        line=st.number_input("Line",value=25.0)

        if st.form_submit_button("Add"):
            st.session_state.live_slips.append({
                "player":player,
                "type":bet_type,
                "line":line
            })

    for l in st.session_state.live_slips:
        cur=get_player_points(l["player"])
        pct=min(cur/l["line"],1) if l["line"] else 0

        st.write(f"{l['player']} ({l['type']}) {cur}/{l['line']} ({int(pct*100)}%)")
