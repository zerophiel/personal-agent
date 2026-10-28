"""Recurring card charges per statement month (subscriptions, apps, games, instalment-like lines) next to the recorded
subscriptions, to confirm with the owner what is recurring, ended, or one-off.
Run: ssh ubuntu@43.157.242.194 'sudo docker exec -i personal-agent-vault-tools-1 python -' < ops/calibration/recurring_charges.py
Read-only."""
import re
import sqlite3

fm = lambda n: f"{n:,}".replace(",", ".")  # noqa: E731
c = sqlite3.connect("file:/data/ledger.db?mode=ro", uri=True)
c.row_factory = sqlite3.Row
groups = {"google": r"GOOGLE", "coway": r"COWAY", "anthropic": r"ANTHROPIC|CLAUDE", "apple": r"APPLE", "rockstar": r"ROCKSTAR",
          "netflix": r"NETFLIX", "spotify": r"SPOTIFY", "squarespace": r"SQSP|SQUARESPACE", "microsoft": r"MICROSOFT", "telkomsel": r"TELKOMSEL",
          "xl": r"XL AXIATA", "openai": r"OPENAI", "gopro": r"GOPRO", "playstation": r"PLAYSTATION", "steam": r"STEAM", "tokopedia-mid": r"MID\*TOKOPEDIA"}
rows = c.execute("SELECT substr(l.cycle,1,7) m, k.alias card, l.description d, l.amount a FROM card_lines l JOIN cards k ON k.id=l.card_id"
                 " WHERE l.kind IN ('belanja','langganan','refund') AND l.cycle >= '2026-05'").fetchall()
table = {}
for r in rows:
    for g, pat in groups.items():
        if re.search(pat, (r["d"] or "").upper()):
            key = (g, r["card"])
            table.setdefault(key, {}).setdefault(r["m"], [0, 0])
            table[key][r["m"]][0] += r["a"]
            table[key][r["m"]][1] += 1
months = sorted({r["m"] for r in rows})
print("statement month:".ljust(28), " ".join(m[2:] for m in months))
for (g, card), per in sorted(table.items()):
    print(f"{g:12s} {card:14s} " + " ".join((fm(per[m][0]) + (f"x{per[m][1]}" if per[m][1] > 1 else "")).rjust(9) if m in per else "        -" for m in months))
print("\nledger subscriptions:")
for r in c.execute("SELECT alias, amount, source, status FROM subscriptions WHERE status!='ended' ORDER BY amount DESC"):
    print(f"   {r['alias']:24s} {fm(r['amount']):>10s} {r['source'][:20]:20s} {r['status']}")
