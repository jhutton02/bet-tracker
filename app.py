import streamlit as st
from datetime import date, datetime
import calendar
import gspread
from google.oauth2.service_account import Credentials

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

def delete_bet(row):
    sheet.delete_rows(row)

def update_bet(row, bet):
    odds_val = safe_parse_odds(bet["odds"])
    profit = calc_profit(bet["risk"], odds_val, bet["result"])

    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), "", "", bet["bet_line"],
        bet["odds"], bet["risk"], bet["result"], profit
    ]])

    st.session_state.bets = load_bets()

# ================= STATE =================
if "bets" not in st.session_state:
    st.session_state.bets = load_bets()

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "edit_row" not in st.session_state:
    st.session_state.edit_row = None

# ================= CALENDAR =================
st.subheader("Calendar")

today = date.today()
year = st.selectbox("Year",[today.year])
month_names = list(calendar.month_name)[1:]
month_name = st.selectbox("Month", month_names, index=today.month-1)
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
        <div style="
        background:{bg};
        color:{tc};
        padding:12px;
        border-radius:12px;
        height:100px;
        display:flex;
        flex-direction:column;
        justify-content:space-between;
        ">
        <b>{day}</b>
        <div style="font-size:18px;font-weight:700;">${round(val,2)}</div>
        <div style="font-size:12px;">{cnt} bets</div>
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ================= BETS =================
st.subheader(f"Bets for {st.session_state.selected_date}")

for b in st.session_state.bets:
    if b["date"] == st.session_state.selected_date:

        c1,c2,c3=st.columns([6,1,1])

        c1.write(f"{b['bet_line']} | {b['odds']} | ${b['profit']}")

        if c2.button("✏️", key=f"edit{b['row']}"):
            st.session_state.edit_row=b["row"]

        if c3.button("❌", key=f"del{b['row']}"):
            delete_bet(b["row"])
            st.session_state.bets=load_bets()
            st.rerun()

        # EDIT FORM BACK
        if st.session_state.edit_row==b["row"]:
            with st.form(f"form{b['row']}"):

                wager=st.text_input("Wager",b["bet_line"])
                risk=st.number_input("Risk",value=b["risk"])

                odds_val=safe_parse_odds(b["odds"])
                to_win=st.number_input("To Win",value=risk*(odds_val-1))

                new_odds=(to_win/risk)+1 if risk!=0 else 0
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
                    st.rerun()
