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
    bets=[]
    for i,r in enumerate(rows,start=2):
        risk=float(r.get("risk",0))
        odds=safe_parse_odds(r["odds"])
        result=r["result"]

        profit = calc_profit(risk, odds, result)

        bets.append({
            "row":i,
            "date":parse_date(r["date"]),
            "bet_line":r["bet_line"],
            "odds":r["odds"],
            "risk":risk,
            "result":result,
            "profit":profit
        })
    return bets

def save_bet(b):
    odds_val = safe_parse_odds(b["odds"])
    profit = calc_profit(b["risk"], odds_val, b["result"])

    sheet.append_row([
        str(b["date"]), "", "", b["bet_line"],
        b["odds"], b["risk"], b["result"], profit
    ])

def delete_bet(r):
    sheet.delete_rows(r)

def update_bet(row, bet):
    odds_val = safe_parse_odds(bet["odds"])
    profit = calc_profit(bet["risk"], odds_val, bet["result"])

    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), "", "", bet["bet_line"],
        bet["odds"], bet["risk"], bet["result"], profit
    ]])

# ================= STATE =================

if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "selected_day" not in st.session_state:
    st.session_state.selected_day = None

if "edit_row" not in st.session_state:
    st.session_state.edit_row = None

# ================= TABS =================

t1, t2, t3 = st.tabs(["📅 Calendar","➕ Add Bet","📋 Tracker"])

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
                cols[i].write("")
                continue

            d=date(year,m,day)
            val=totals.get(d,0)
            cnt=counts.get(d,0)

            if val>0:
                border="#16a34a"; bg="#ecfdf5"; color="#16a34a"
            elif val<0:
                border="#dc2626"; bg="#fef2f2"; color="#dc2626"
            else:
                border="#d1d5db"; bg="#f9fafb"; color="#374151"

            cols[i].markdown(f"""
            <div style="
                border:2px solid {border};
                background:{bg};
                border-radius:12px;
                padding:8px;
                height:95px;
            ">
                <div style="font-size:13px;font-weight:600;">{day}</div>
                <div style="font-size:16px;font-weight:700;color:{color};">${round(val,2)}</div>
                <div style="font-size:11px;color:#6b7280;">{cnt} bets</div>
            </div>
            """, unsafe_allow_html=True)

            if cols[i].button("Select", key=f"d{day}"):
                st.session_state.selected_day=d

    if st.session_state.selected_day:
        st.markdown(f"## Bets for {st.session_state.selected_day}")

        for b in st.session_state.bets:
            if b["date"]==st.session_state.selected_day:

                c1,c2,c3=st.columns([7,1,1])

                c1.markdown(f"""
                **{b['bet_line']}**  
                Odds: {b['odds']}  
                Profit: ${round(b['profit'],2)}
                """)

                if c2.button("✏️", key=f"edit{b['row']}"):
                    st.session_state.edit_row=b["row"]

                if c3.button("❌", key=f"del{b['row']}"):
                    delete_bet(b["row"])
                    st.session_state.bets=load_bets()
                    st.rerun()

                if st.session_state.edit_row == b["row"]:
                    with st.form(f"form{b['row']}"):

                        new_wager = st.text_input("Wager", b["bet_line"])
                        risk = st.number_input("Risk ($)", value=b["risk"])
                        to_win = st.number_input("To Win ($)", value=b["risk"])

                        odds_val = calc_odds(risk, to_win)
                        st.text_input("Odds", f"{round(odds_val,2)}x", disabled=True)

                        new_result = st.selectbox("Result", ["pending","win","loss"])

                        if st.form_submit_button("Save"):
                            update_bet(b["row"],{
                                "date":b["date"],
                                "bet_line":new_wager,
                                "odds":f"{round(odds_val,2)}x",
                                "risk":risk,
                                "result":new_result
                            })

                            st.session_state.edit_row=None
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
    today=date.today()

    d=sum(b["profit"] for b in bets if b["date"]==today)
    w=sum(b["profit"] for b in bets if b["date"]>=today-timedelta(days=7))
    m=sum(b["profit"] for b in bets if b["date"]>=today.replace(day=1))
    y=sum(b["profit"] for b in bets if b["date"]>=today.replace(month=1,day=1))

    def color(val):
        return "green" if val > 0 else "red" if val < 0 else "gray"

    st.markdown(f"**Daily:** <span style='color:{color(d)}'>${round(d,2)}</span>", unsafe_allow_html=True)
    st.markdown(f"**Weekly:** <span style='color:{color(w)}'>${round(w,2)}</span>", unsafe_allow_html=True)
    st.markdown(f"**Monthly:** <span style='color:{color(m)}'>${round(m,2)}</span>", unsafe_allow_html=True)
    st.markdown(f"**Yearly:** <span style='color:{color(y)}'>${round(y,2)}</span>", unsafe_allow_html=True)
