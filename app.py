with t1:
    today = date.today()

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    with col2:
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Month", month_names, index=today.month - 1)

    month = month_names.index(selected_month_name) + 1

    # ================= DATA =================
    totals = {}
    counts = {}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year == year and b["date"].month == month:
            d = b["date"]
            totals[d] = totals.get(d, 0) + b["profit"]
            counts[d] = counts.get(d, 0) + 1

    # ================= CALENDAR HEADER =================
    st.markdown("""
    <div style="
        background:#f8fafc;
        padding:20px;
        border-radius:12px;
        box-shadow:0 8px 20px rgba(0,0,0,0.08);
    ">
    """, unsafe_allow_html=True)

    # Weekday labels
    days = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"]
    cols = st.columns(7)
    for i, d in enumerate(days):
        cols[i].markdown(f"""
        <div style="
            text-align:center;
            font-size:12px;
            color:#6b7280;
            padding-bottom:8px;
            font-weight:600;
        ">
            {d}
        </div>
        """, unsafe_allow_html=True)

    # ================= GRID =================
    for week in calendar.monthcalendar(year, month):
        cols = st.columns(7)
        for i, day in enumerate(week):

            if day == 0:
                cols[i].markdown(f"""
                <div style="
                    height:90px;
                    border:1px solid #e5e7eb;
                    background:#ffffff;
                "></div>
                """, unsafe_allow_html=True)
                continue

            d = date(year, month, day)
            val = totals.get(d, 0)
            cnt = counts.get(d, 0)

            # Color logic (subtle like your reference)
            if val > 0:
                bg = "#dcfce7"   # light green
            elif val < 0:
                bg = "#fee2e2"   # light red
            else:
                bg = "#ffffff"

            cols[i].markdown(f"""
            <div style="
                height:90px;
                border:1px solid #e5e7eb;
                padding:8px;
                background:{bg};
                display:flex;
                flex-direction:column;
                justify-content:space-between;
            ">
                <div style="font-size:13px;font-weight:600;">{day}</div>
                <div style="font-size:12px;color:#6b7280;">
                    ${round(val,2)}<br>
                    {cnt} bets
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ================= DAY DETAILS =================
    st.divider()

    selected_date = st.date_input("Select Day", date(year, month, 1))

    st.subheader(f"Bets for {selected_date}")

    day_bets = [b for b in st.session_state.bets if b["date"] == selected_date]

    for b in day_bets:
        st.markdown(f"""
        <div style='background:#f1f5f9;padding:12px;border-radius:10px;margin-bottom:8px'>
        <b>{b['sport']} | {b['bet_type']}</b><br>
        {b['bet_line']} {result_badge(b['result'])}<br>
        Odds: {format_odds_display(b['odds'])}<br>
        Risk: ${get_risk(b)}<br>
        <b>${round(b['profit'],2)}</b>
        </div>
        """, unsafe_allow_html=True)
