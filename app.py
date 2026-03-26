# ✅ ONLY CHANGE: Calendar is now clickable (everything else untouched)

# ================= STATE ADD THIS =================
if "selected_date" not in st.session_state:
    st.session_state.selected_date = None


# ================= REPLACE ONLY CALENDAR SECTION =================

with t1:
    today = date.today()

    col1, col2 = st.columns(2)
    with col1:
        year = st.selectbox("Year", [today.year - 1, today.year, today.year + 1], index=1)
    with col2:
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Month", month_names, index=today.month - 1)

    month = month_names.index(selected_month_name) + 1

    totals = {}
    counts = {}

    for b in st.session_state.bets:
        if b["date"] and b["date"].year == year and b["date"].month == month:
            d = b["date"]
            totals[d] = totals.get(d, 0) + b["profit"]
            counts[d] = counts.get(d, 0) + 1

    # 🔥 CLICKABLE CALENDAR
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

            # 👉 BUTTON INSIDE STYLE
            if cols[i].button(f"{day}\n${round(val,2)}\n{cnt} bets", key=f"day_{year}_{month}_{day}"):
                st.session_state.selected_date = d

            # visual box (same look)
            cols[i].markdown(f"""
            <div style="margin-top:-70px;background:{bg};color:{tc};padding:12px;border-radius:14px;height:100px;text-align:center;">
                <b>{day}</b><br>${round(val,2)}<br>{cnt} bets
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 🔥 SHOW SELECTED DAY (instead of dropdown)
    selected_date = st.session_state.selected_date or today

    st.subheader(f"Bets for {selected_date}")

    day_bets = [b for b in st.session_state.bets if b["date"] == selected_date]

    for b in day_bets:
        col1, col2, col3 = st.columns([8,1,1])

        with col1:
            st.markdown(f"""
            <div style='background:#f1f5f9;padding:12px;border-radius:12px;margin-bottom:8px'>
            <b>{b['sport']} | {b['bet_type']}</b><br>
            {b['bet_line']} {result_badge(b['result'])}<br>
            Odds: {format_odds_display(b['odds'])}<br>
            Risk: ${get_risk(b)}<br>
            <b>${round(b['profit'],2)}</b>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            if st.button("✏️", key=f"edit_{b['row']}"):
                st.session_state.edit_row = b["row"]

        with col3:
            if st.button("❌", key=f"del_{b['row']}"):
                delete_bet(b["row"])
                st.session_state.bets = load_bets()
                st.rerun()

        if st.session_state.edit_row == b["row"]:
            with st.form(f"edit_form_{b['row']}"):

                new_wager = st.text_input("Wager", b["bet_line"])

                risk = st.number_input("Risk ($)", value=get_risk(b))
                to_win = st.number_input("To Win ($)", value=calc_to_win(risk, safe_parse_odds(b["odds"])))
                odds_val = calc_odds(risk, to_win)

                st.text_input("Odds", f"{round(odds_val,2)}x", disabled=True)

                new_result = st.selectbox("Result", ["pending","win","loss","push"])

                if st.form_submit_button("Save"):
                    profit = calc_profit(risk, odds_val, new_result)

                    update_bet(b["row"], {
                        "date": b["date"],
                        "sport": b["sport"],
                        "bet_type": b["bet_type"],
                        "bet_line": new_wager,
                        "odds": f"{round(odds_val,2)}x",
                        "risk": risk,
                        "result": new_result,
                        "profit": profit
                    })

                    st.session_state.bets = load_bets()
                    st.session_state.edit_row = None
                    st.rerun()
