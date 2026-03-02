# ================= CALENDAR TAB =================
with tab_calendar:

    import streamlit.components.v1 as components

    today = date.today()

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    with col2:
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Month", month_names, index=today.month - 1)

    month = month_names.index(selected_month_name) + 1

    totals = {}
    monthly_total = 0

    for b in st.session_state.bets:
        if b["date"].year == year and b["date"].month == month:
            totals[b["date"]] = totals.get(b["date"], 0) + b["profit"]
            if b["result"] in ["win","loss","push"]:
                monthly_total += b["profit"]

    total_color = "green" if monthly_total > 0 else "red" if monthly_total < 0 else "black"

    st.markdown(
        f"<h2 style='text-align:center;margin-bottom:20px;'>{selected_month_name} {year} "
        f"<span style='color:{total_color};'>(${round(monthly_total,2)})</span></h2>",
        unsafe_allow_html=True
    )

    calendar_html = f"""
    <div style="
        border:6px solid black;
        border-radius:20px;
        padding:25px;
        font-family:sans-serif;
    ">
        <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:15px;font-weight:700;margin-bottom:10px;">
            {"".join([f"<div style='text-align:center;'>{h}</div>" for h in ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']])}
        </div>

        <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:15px;">
    """

    for week in calendar.monthcalendar(year, month):
        for day in week:
            if day == 0:
                calendar_html += "<div></div>"
            else:
                d = date(year, month, day)
                val = totals.get(d, 0)

                if val > 0:
                    bg = "#c6f6d5"
                elif val < 0:
                    bg = "#fed7d7"
                else:
                    bg = "#edf2f7"

                border = "4px solid blue" if st.session_state.selected_date == d else "1px solid #cbd5e0"

                calendar_html += f"""
                <div onclick="window.parent.postMessage({{selected:'{d}'}}, '*')" 
                     style="
                        background:{bg};
                        border:{border};
                        border-radius:12px;
                        height:140px;
                        padding:10px;
                        display:flex;
                        flex-direction:column;
                        justify-content:space-between;
                        cursor:pointer;
                        font-weight:600;
                     ">
                    <div style="font-size:18px;">{day}</div>
                    <div>${round(val,2)}</div>
                </div>
                """

    calendar_html += "</div></div>"

    components.html(calendar_html, height=800)

    # ================= DAILY DETAILS =================
    if st.session_state.selected_date:
        selected = st.session_state.selected_date
        st.markdown("---")
        st.subheader(f"Bets for {selected}")

        day_bets = [b for b in st.session_state.bets if b["date"] == selected]

        if len(day_bets) == 0:
            st.info("No bets this day.")
        else:
            daily_profit = sum(b["profit"] for b in day_bets)
            daily_units = sum(b["units"] for b in day_bets)
            wins = len([b for b in day_bets if b["result"] == "win"])
            losses = len([b for b in day_bets if b["result"] == "loss"])

            st.metric("Daily Profit", f"${round(daily_profit,2)}")
            st.metric("Units Risked", daily_units)
            st.metric("Record", f"{wins}-{losses}")
