import streamlit as st
from datetime import date, timedelta, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials
import matplotlib.pyplot as plt
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

# ================= LIVE =================

def get_live_stat(player, stat):
    base = random.randint(10, 40)
    if stat == "Points":
        return base
    elif stat == "Rebounds":
        return base // 2
    elif stat == "Assists":
        return base // 3
    return base + base//2

def progress_bar(current, line):
    pct = min(current/line,1)
    filled = int(pct*20)
    return f"[{'█'*filled}{'░'*(20-filled)}] {int(pct*100)}%"

# ================= DATA =================

def load_bets():
    rows = sheet.get_all_records()
    bets=[]
    for i,r in enumerate(rows,start=2):
        risk=float(r.get("risk",0))
        odds=safe_parse_odds(r["odds"])
        result=r["result"]

        bets.append({
            "row":i,
            "date":parse_date(r["date"]),
            "bet_line":r["bet_line"],
            "odds":r["odds"],
            "risk":risk,
            "result":result,
            "profit":calc_profit(risk,odds,result)
        })
    return bets

def save_bet(b):
    sheet.append_row([
        str(b["date"]), "", "", b["bet_line"],
        b["odds"], b["risk"], b["result"], b["profit"]
    ])

def delete_bet(r):
    sheet.delete_rows(r)

# ================= STATE =================

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "live_slips" not in st.session_state:
    st.session_state.live_slips = []

if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

# ================= TABS =================

t1, t2, t3, t4 = st.tabs(["📅 Calendar","➕ Add Bet","📋 Tracker","🔥 Live Tracker"])

# ================= CALENDAR =================

with t1:
    today=date.today()

    year=st.selectbox("Year",[today.year])
    month=st.selectbox("Month",list(calendar.month_name)[1:],index=today.month-1)
    m=list(calendar.month_name).index(month)

    totals={}
    counts={}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year==year and b["date"].month==m:
            d=b["date"]
            totals[d]=totals.get(d,0)+b["profit"]
            counts[d]=counts.get(d,0)+1

    for week in calendar.monthcalendar(year,m):
        cols=st.columns(7)
        for i,day in enumerate(week):
            if day==0: 
                cols[i].markdown("")
                continue

            d=date(year,m,day)
            val=totals.get(d,0)
            cnt=counts.get(d,0)

            # 🎨 COLORS
            if val>0:
                border="#16a34a"
                bg="#ecfdf5"
                profit_color="#16a34a"
            elif val<0:
                border="#dc2626"
                bg="#fef2f2"
                profit_color="#dc2626"
            else:
                border="#d1d5db"
                bg="#f9fafb"
                profit_color="#374151"

            # 🧱 CLEAN CARD DESIGN
            if cols[i].button("", key=f"d{day}", use_container_width=True):
                st.session_state.selected_day=d

            cols[i].markdown(f"""
            <div style="
                margin-top:-75px;
                border:2px solid {border};
                background:{bg};
                border-radius:14px;
                padding:10px;
                height:110px;
                display:flex;
                flex-direction:column;
                justify-content:space-between;
            ">
                <div style="font-weight:600;font-size:14px;">
                    {day}
                </div>

                <div style="font-size:18px;font-weight:700;color:{profit_color};">
                    ${round(val,2)}
                </div>

                <div style="font-size:12px;color:#6b7280;">
                    {cnt} bets
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ================= SELECTED DAY =================

    if st.session_state.selected_day:
        st.markdown(f"## Bets for {st.session_state.selected_day}")

        for b in st.session_state.bets:
            if b["date"]==st.session_state.selected_day:
                c1,c2,c3=st.columns([8,1,1])

                color="green" if b["profit"]>0 else "red" if b["profit"]<0 else "gray"

                c1.markdown(f"""
                **{b['bet_line']}**  
                Odds: {b['odds']}  
                <span style='color:{color}'>${round(b['profit'],2)}</span>
                """, unsafe_allow_html=True)

                if c2.button("✏️", key=f"e{b['row']}"):
                    pass

                if c3.button("❌", key=f"x{b['row']}"):
                    delete_bet(b["row"])
                    st.session_state.bets=load_bets()
                    st.rerun()


# ================= ADD =================

with t2:
    with st.form("add"):
        d=st.date_input("Date")
        wager=st.text_input("Wager")
        risk=st.number_input("Risk",value=100.0)
        to_win=st.number_input("To Win",value=100.0)

        odds=calc_odds(risk,to_win)
        st.text_input("Odds",f"{round(odds,2)}x",disabled=True)

        result=st.selectbox("Result",["pending","win","loss"])

        if st.form_submit_button("Add Bet"):
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

    d=sum(b["profit"] for b in bets if b["date"]==today)
    w=sum(b["profit"] for b in bets if b["date"]>=today-timedelta(days=7))
    m=sum(b["profit"] for b in bets if b["date"]>=today.replace(day=1))
    y=sum(b["profit"] for b in bets if b["date"]>=today.replace(month=1,day=1))

    def c(v): return "green" if v>0 else "red" if v<0 else "gray"

    c1,c2,c3,c4=st.columns(4)
    for col,val,name in zip([c1,c2,c3,c4],[d,w,m,y],["Day","Week","Month","Year"]):
        col.markdown(f"<h3 style='color:{c(val)}'>{name}<br>${round(val,2)}</h3>",unsafe_allow_html=True)

    if bets:
        sorted_bets=sorted([b for b in bets if b["date"]],key=lambda x:x["date"])
        dates=[]
        running=[]
        total=0

        for b in sorted_bets:
            total+=b["profit"]
            dates.append(b["date"])
            running.append(total)

        fig,ax=plt.subplots()
        ax.plot(dates,running)
        ax.axhline(0,linestyle="--")
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
