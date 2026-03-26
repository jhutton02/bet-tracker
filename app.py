# ONLY CHANGE IS INSIDE CALENDAR LOOP

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

        with cols[i]:
            # clickable area (full width)
            if st.button("", key=f"day_{d}", use_container_width=True):
                st.session_state.selected_date = d

            # styled box (UNCHANGED LOOK)
            st.markdown(f"""
            <div style="
                background:{bg};
                color:{tc};
                padding:12px;
                border-radius:14px;
                height:100px;
                margin-top:-70px;
            ">
                <b>{day}</b><br>${round(val,2)}<br>{cnt} bets
            </div>
            """, unsafe_allow_html=True)
