# 🔥 FIX — YOU REPLACED TOO MUCH

# Put this line BACK ABOVE your calendar section:

t1, t2, t3, t4 = st.tabs(["📅 Calendar","➕ Add Bet","📋 Tracker","🔥 Live Tracker"])


# 🔥 THEN USE THIS FULL CALENDAR SECTION (inside t1)

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

    if "selected_day" not in st.session_state:
        st.session_state.selected_day = None

    for week in calendar.monthcalendar(year,month_num):
        cols=st.columns(7)
        for i,day in enumerate(week):
            if day==0:
                continue

            d=date(year,month_num,day)
            val=totals.get(d,0)
            cnt=counts.get(d,0)

            label=f"{day}\n${round(val,2)}\n{cnt} bets"

            if cols[i].button(label, key=f"day_{day}"):
                st.session_state.selected_day = d

    if st.session_state.selected_day:
        selected = st.session_state.selected_day
        st.markdown(f"## Bets for {selected}")

        for b in st.session_state.bets:
            if b["date"] == selected:

                c1,c2,c3 = st.columns([8,1,1])

                color = "green" if b["profit"] > 0 else "red" if b["profit"] < 0 else "gray"

                c1.markdown(f"""
                **{b['bet_line']}**  
                Odds: {b['odds']}  
                <span style='color:{color}'>${round(b['profit'],2)}</span>
                """, unsafe_allow_html=True)

                if c2.button("✏️", key=f"edit_{b['row']}"):
                    st.session_state.edit_row = b["row"]

                if c3.button("❌", key=f"del_{b['row']}"):
                    delete_bet(b["row"])
                    st.session_state.bets = load_bets()
                    st.rerun()
