# 🔥 REPLACE ONLY THESE 3 FUNCTIONS IN YOUR CODE

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
            "profit":profit  # ✅ ALWAYS RECALCULATE
        })
    return bets


def update_bet(row, bet):
    odds_val = safe_parse_odds(bet["odds"])
    profit = calc_profit(bet["risk"], odds_val, bet["result"])

    sheet.update(f"A{row}:H{row}", [[
        str(bet["date"]), "", "", bet["bet_line"],
        bet["odds"], bet["risk"], bet["result"], profit
    ]])


def save_bet(b):
    odds_val = safe_parse_odds(b["odds"])
    profit = calc_profit(b["risk"], odds_val, b["result"])

    sheet.append_row([
        str(b["date"]), "", "", b["bet_line"],
        b["odds"], b["risk"], b["result"], profit
    ])
