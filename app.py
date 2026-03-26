import streamlit as st
from datetime import date, timedelta, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
import requests
import random

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

def calc_odds(risk, to_win):
    return (to_win / risk) + 1 if risk != 0 else 0

def calc_profit(risk, odds, result):
    if result == "win":
        return risk * (odds - 1)
    elif result == "loss":
        return -risk
    return 0

def parse_date_safe(val):
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except:
        return None

def get_risk(b):
    return float(b.get("risk", b.get("units", 0)))

# ================= LIVE =================

def get_live_stat(player, stat):
    base = random.randint(10, 40)
    if stat == "Points":
        return base
    elif stat == "Rebounds":
        return base // 2
    elif stat == "Assists":
        return base // 3
    else:
        return base + base//2

def progress_bar(current, line):
    pct = min(current/line,1)
    filled = int(pct*20)
    return f"[{'█'*filled}{'░'*(20-filled)}] {int(pct*100)}%"

# ================= LOAD =================

def load_bets():
    rows = sheet.get_all_records()
    bets = []
    for i,r in enumerate(rows,start=2):
        risk = float(r.get("risk", r.get("units", 0)))
        odds = safe_parse_odds(r["odds"])
        result = r["result"]
        profit = calc_profit(risk, odds, result)

        bets.append({
            "row":i,
            "date":parse_date_safe(r["date"]),
            "bet_line":r["bet_line"],
            "odds":r["odds"],
            "risk":risk,
            "result":result,
            "profit":profit
        })
    return bets

def save_bet(b):
    sheet.append_row([str(b["date"]), "", "", b["bet_line"], b["odds"], b["risk"], b["result"], b["profit"]])

def delete_bet(r):
    sheet.delete_rows(r)

# ================= STATE =================

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "live_slips" not in st.session_state:
    st.session_state.live_slips = []

# ================= TABS =================

t1,t2,t3,t4 = st.tabs(["📅 Calendar","➕ Add Bet","📋 Tracker","🔥 Live Tracker"])

# ================= CALENDAR =================

with t1:
    today = date.today()
    year = st.selectbox("Year",[today.year],index=0)
    month = st.selectbox("Month",list(calendar.month_name)[1:],index=today.month-1)
    month_num = list(calendar.month_name).index(month)

    totals={}
    counts={}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year==year and b["date"].month==month_num:
            d=b["date"]
            totals[d]=totals.get(d,0)+b["profit"]
            counts[d]=counts.get(d,0)+1

    for week in calendar.monthcalendar(year,month_num):
        cols=st.columns(7)
        for i,day in enumerate(week):
            if day==0:
                continue
            d=date(year,month_num,day)
            val=totals.get(d,0)
            cnt=counts.get(d,0)

            if val>0:
                bg="#16a34a"; tc="white"
            elif val<0:
                bg="#dc2626"; tc="white"
            else:
                bg="#f1f5f9"; tc="black"

            cols[i].markdown(f"""
            <div style="background:{bg};color:{tc};padding:10px;border-radius:10px">
            {day}<br>${round(val,2)}<br>{cnt} bets
            </div>
            """,unsafe_allow_html=True)

# ================= ADD =================

with t2:
    with st.form("add"):
        d=st.date_input("Date")
        wager=st.text_input("Wager")
        risk=st.number_input("Risk",value=100.0)
        to_win=st.number_input("To Win",value=100.0)
        odds=calc_odds(risk,to_win)
        result=st.selectbox("Result",["pending","win","loss"])

        if st.form_submit_button("Add"):
            save_bet({
                "date":d,
                "bet_line":wager,
                "odds":f"{round(odds,2)}x",
                "risk":risk,
                "result":result,
                "profit":calc_profit(risk,odds,result)
            })
            st.session_state.bets=load_bets()
            st.rerun()

# ================= TRACKER =================

with t3:
    bets=st.session_state.bets
    today=date.today()

    daily=sum(b["profit"] for b in bets if b["date"]==today)
    weekly=sum(b["profit"] for b in bets if b["date"]>=today-timedelta(days=7))
    monthly=sum(b["profit"] for b in bets if b["date"]>=today.replace(day=1))
    yearly=sum(b["profit"] for b in bets if b["date"]>=today.replace(month=1,day=1))

    def color(v): return "green" if v>0 else "red" if v<0 else "gray"

    c1,c2,c3,c4=st.columns(4)
    for c,val,label in zip([c1,c2,c3,c4],[daily,weekly,monthly,yearly],["Day","Week","Month","Year"]):
        c.markdown(f"<h3 style='color:{color(val)}'>{label}<br>${round(val,2)}</h3>",unsafe_allow_html=True)

    # GRAPH
    if bets:
        sorted_bets=sorted([b for b in bets if b["date"]],key=lambda x:x["date"])
        daily_totals={}
        for b in sorted_bets:
            d=b["date"]
            daily_totals[d]=daily_totals.get(d,0)+b["profit"]

        dates=sorted(daily_totals.keys())
        running=[]
        total=0
        for d in dates:
            total+=daily_totals[d]
            running.append(total)

        fig,ax=plt.subplots()
        ax.plot(dates,running)
        ax.axhline(0,linestyle="--")
        ax.set_xticks(dates[::max(1,len(dates)//6)])
        ax.set_xticklabels([d.strftime("%m/%d") for d in dates[::max(1,len(dates)//6)]])
        plt.xticks(rotation=30)
        st.pyplot(fig)

# ================= LIVE =================

with t4:
    with st.form("live"):
        p=st.text_input("Player")
        s=st.selectbox("Stat",["PRA","Points","Rebounds","Assists"])
        l=st.number_input("Line",value=30.0)
        if st.form_submit_button("Add"):
            st.session_state.live_slips.append({"p":p,"s":s,"l":l})

    for x in st.session_state.live_slips:
        cur=get_live_stat(x["p"],x["s"])
        st.write(f"{x['p']} {x['s']} {x['l']}")
        st.write(cur)
        st.write(progress_bar(cur,x["l"]))
