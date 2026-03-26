# ================= LIVE TRACKER =================

import requests
from bs4 import BeautifulSoup

def get_espn_stats(player_name, stat_type):
    try:
        search_name = player_name.lower().replace(" ", "-")

        url = f"https://www.espn.com/nba/player/_/name/{search_name}"
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

        if res.status_code != 200:
            return 0

        soup = BeautifulSoup(res.text, "html.parser")

        stats = soup.find_all("td")

        values = []
        for s in stats:
            try:
                values.append(float(s.text))
            except:
                continue

        if len(values) < 3:
            return 0

        pts = values[0]
        reb = values[1]
        ast = values[2]

        if stat_type == "Points":
            return pts
        elif stat_type == "Rebounds":
            return reb
        elif stat_type == "Assists":
            return ast
        else:
            return pts + reb + ast

    except:
        return 0

# ================= UI =================

with t4:
    st.subheader("Live Bet Tracker")

    with st.form("live_form"):
        player = st.text_input("Player Name")
        stat_type = st.selectbox("Stat Type", ["PRA","Points","Rebounds","Assists"])
        line = st.number_input("Line", value=30.0)

        if st.form_submit_button("Add"):
            st.session_state.live_slips.append({
                "player": player,
                "line": line,
                "stat": stat_type
            })

    for slip in st.session_state.live_slips:
        current = get_espn_stats(slip["player"], slip["stat"])

        pct = min(current / slip["line"], 1.0) if slip["line"] > 0 else 0
        filled = int(pct * 20)
        bar = "█" * filled + "░" * (20 - filled)

        st.markdown(f"""
        **{slip['player']} ({slip['stat']} {slip['line']})**  
        Current: {current}  
        [{bar}] {int(pct*100)}%
        """)
