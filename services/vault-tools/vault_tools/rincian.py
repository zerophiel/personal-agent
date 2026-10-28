"""/rincian: what to transfer where, WITH full numbers (sent privately and deleted after 24 h by the plugin).

Aggregated per destination, as if everything were paid on the same day: a card with a minimum payment and a second
payment that closes the bill becomes ONE transfer with the total; due dates are ignored. App-menu payments and
auto-debits are listed apart because they are not transfers. Telegram "Markdown" (legacy): *bold*, _italic_, `number`."""
from __future__ import annotations

from .money import format_idr

_WORDS = {"ipl": "IPL", "va": "VA", "spaylater": "SPayLater", "mtf": "MTF"}
_BANKS = {"bca": "BCA", "hsbc": "HSBC", "cimb": "CIMB", "dbs": "DBS", "mega": "Mega", "mandiri": "Mandiri", "jenius": "Jenius", "jago": "Jago"}


def _nice(alias: str) -> str:
    return " ".join(_WORDS.get(w, w.capitalize()) for w in alias.replace("-", " ").split())


def _bank(name: str | None) -> str:
    return _BANKS.get((name or "").lower(), (name or "").title())


def build(conn, vault, snap: dict) -> str:
    cards = {r["alias"]: r for r in conn.execute("SELECT alias, bank, last4, pay_method, pay_to_alias FROM cards")}
    transfers: dict[str, dict] = {}          # destination key -> {title, kind, amount, parts}
    app_menu: dict[str, int] = {}
    autodebit: list[dict] = []
    savings = 0
    for t in snap["transfers"]:
        if t.get("method") == "autodebit":
            autodebit.append(t)
            continue
        if t["reason"] == "tabungan":
            savings += t["amount"]
            continue
        if t.get("method") == "app_menu":
            app_menu[t["to_alias"]] = app_menu.get(t["to_alias"], 0) + t["amount"]
            continue
        key = t.get("pay_to") or t["to_alias"]
        d = transfers.setdefault(key, {"to": t["to_alias"], "amount": 0, "parts": 0})
        d["amount"] += t["amount"]
        d["parts"] += 1

    def describe(key: str, to_alias: str) -> tuple[str, str]:
        meta = conn.execute("SELECT kind, bank FROM payee_secrets WHERE alias=?", (key,)).fetchone()
        card = cards.get(to_alias)
        if card:
            to = {"account": "rekening", "va": "virtual account"}.get(meta["kind"] if meta else "", "")
            return f"{_bank(card['bank'])} …{card['last4']}", ("tagihan kartu, bayar ke " + to) if to else "kartu kredit"
        bank = _bank(meta["bank"]) if meta and meta["bank"] != "?" else ""
        kind = {"account": "rekening", "va": "virtual account", "card": "kartu"}.get(meta["kind"] if meta else "", "")
        return _nice(to_alias) + (f" ({bank})" if bank else ""), kind

    rows, missing, total = [], [], 0
    for key, d in sorted(transfers.items(), key=lambda kv: (kv[1]["to"] not in cards, -kv[1]["amount"])):
        title, kind = describe(key, d["to"])
        total += d["amount"]
        try:
            number = vault.reveal(key)
        except KeyError:
            missing.append(f"• {title}: *{format_idr(d['amount'])}*")
            continue
        note = f"_{d['parts']} pembayaran digabung_\n" if d["parts"] > 1 else ""
        rows.append(f"*{len(rows) + 1}. {title}*" + (f" - {kind}" if kind else "") + f"\n{note}Jumlah: *{format_idr(d['amount'])}*\nNomor: `{number}`")

    out = ["*💸 Transfer yang perlu dilakukan*\n_Digabung per tujuan, seolah semuanya dibayar di hari yang sama (jatuh tempo diabaikan)._"]
    out += rows or ["Tidak ada transfer."]
    if missing:
        out.append("*⚠️ Tujuan belum didaftarkan (nomor belum ada)*\n" + "\n".join(missing))
    out.append(f"*🧾 Total transfer: {format_idr(total)}*" + (f"\n_Belum terdanai (tidak termasuk): {format_idr(sum(u['amount'] for u in snap['unfunded']))}_" if snap.get("unfunded") else ""))
    if app_menu:
        lines = []
        for alias, amt in app_menu.items():
            c = cards.get(alias)
            name = f"{_bank(c['bank'])} …{c['last4']}" if c else _nice(alias)
            number = ""
            for key in ((c["pay_to_alias"], f"num-{c['last4']}") if c else ()):
                try:
                    number = f"\n  Nomor kartu: `{vault.reveal(key)}`" if key else ""
                except KeyError:
                    number = ""
                if number:
                    break
            lines.append(f"• {name}: *{format_idr(amt)}*{number}")
        out.append("*📱 Lewat menu aplikasi bank (bukan transfer)*\n" + "\n".join(lines))
    if autodebit:
        lines = []
        for t in autodebit:
            acct = conn.execute("SELECT bank FROM accounts WHERE alias=?", (t.get("pay_to"),)).fetchone()
            src = f"rekening {_bank(acct['bank'])}" if acct else "rekening yang diset"
            lines.append(f"• {_nice(t['to_alias'])}: *{format_idr(t['amount'])}* dari {src}")
        out.append("*🔄 Autodebet (tidak perlu transfer, pastikan saldo cukup)*\n" + "\n".join(lines))
    if savings:
        out.append(f"*🐖 Sisihkan ke tabungan sendiri*\n{format_idr(savings)} (tidak ada nomor tujuan)")
    return "\n\n".join(out)
