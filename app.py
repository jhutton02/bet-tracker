# EVERYTHING ABOVE IS 100% UNCHANGED

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
        if b["date"].year == year and b["date"].month == month:
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
        for idx, b in enumerate(day_bets):  # ✅ ONLY CHANGE (idx added)

            if b["profit"] > 0:
                bg = "#d1fae5"
            elif b["profit"] < 0:
                bg = "#fee2e2"
            else:
                bg = "#f1f5f9"

            col1, col2, col3 = st.columns([8,1,1])

            with col1:
                st.markdown(f"""
                <div style='background:{bg};padding:12px;border-radius:12px;margin-bottom:8px'>
                <b>{b['sport']} | {b['bet_type']}</b><br>
                {b['bet_line']} | {b['result']}<br>
                Odds: {format_odds_display(b['odds'])}<br>
                <b>${round(b['profit'],2)}</b>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if st.button("✏️", key=f"cal_edit_{b['row']}_{idx}"):  # ✅ FIX
                    st.session_state.edit_row = b["row"]

            with col3:
                if st.button("❌", key=f"cal_del_{b['row']}_{idx}"):  # ✅ FIX
                    delete_bet(b["row"])
                    st.session_state.bets = load_bets()
                    st.rerun()
