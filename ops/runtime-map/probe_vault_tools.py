"""vault-tools side of the runtime map: the live ledger schema (DDL from sqlite_master), what is recorded (entity catalog,
coverage, /usulan, plans, change_log) and the /data and /ingest layout. Runs inside the vault-tools container:
  ssh ubuntu@43.157.242.194 'sudo docker exec -i personal-agent-vault-tools-1 python -' < ops/runtime-map/probe_vault_tools.py
Read-only (ledger opened with mode=ro). No money column leaves the container: the entity catalog is a whitelist of
non-money columns, coverage is counts and dates, free text (/usulan) has amounts masked. Secrets: names only."""
import json
import os
import re
import sqlite3
import stat
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

DATA, INGEST, LEDGER = "/data", "/ingest", "/data/ledger.db"
WIB = timezone(timedelta(hours=7))
CATALOG = {   # non-money columns only: no balance, limit, amount, target, last4
    "accounts": ("alias", "bank", "kind"),
    "cards": ("alias", "bank", "statement_day", "due_day", "pay_method", "pay_to_alias", "interest_bp_month"),
    "debts": ("alias", "lender", "due_day", "pay_method", "pay_to_alias", "debit_account_alias"),
    "fixed_expenses": ("alias", "payee_alias", "due_day"),
    "sinking_funds": ("alias", "due_date", "pool_alias", "pool_pay_to", "creditor_pay_to", "pace", "due_payday", "low_until"),
    "subscriptions": ("alias", "name", "source", "status", "essential", "ends"),
    "payee_secrets": ("alias", "kind", "bank"),
}
TOKEN = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}|sk-ant-[A-Za-z0-9_-]+|\bntn_[A-Za-z0-9]+|\bsecret_[A-Za-z0-9]{20,}"
                   r"|ya29\.[A-Za-z0-9_.-]+|\b1//[A-Za-z0-9_-]{20,}|AKIA[A-Z0-9]{12,}|(?i:bearer)\s+[A-Za-z0-9._~+/=-]{12,}")
MONEY = re.compile(r"(?i:rp)\.?\s*\d(?:[\d.,]*\d)?(?:\s*(?i:jt|juta|rb|ribu|k)\b)?|\d{1,3}(?:[.,]\d{3})+")
AMOUNT = re.compile(MONEY.pattern + r"|\d{4,}")
BANKS = ("bca", "mandiri", "jago", "jenius", "cimb", "dbs", "hsbc", "mega", "bni", "bri", "permata", "ocbc", "uob", "citi",
         "maybank", "danamon", "panin", "btn", "sinarmas", "shopee", "spaylater", "mtf")
DOC_KINDS = (("e-statement", r"e-?statement"), ("monthly-statement", r"monthly.?statement"), ("mutasi", r"mutasi"),
             ("tagihan", r"tagihan|billing"), ("rekening-koran", r"rekening.?koran"))
MONTHS = r"(?<![a-z])(?:jan|feb|mar|apr|mei|may|jun|jul|agu|aug|sep|okt|oct|nov|des|dec)"


def scrub(s):
    s = TOKEN.sub("[token]", str(s))
    s = re.sub(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", "[email]", s)
    s = re.sub(r"\b\d{3,4}(?:[ -]\d{3,4}){2,}\b", "[nomor]", s)
    return re.sub(r"\d{9,}", "[angka]", s)


def free(s, width=220):
    s = scrub(re.sub(r"\s+", " ", s or ""))
    return AMOUNT.sub(lambda m: "Rp [n]" if m.group()[:2].lower() == "rp" else "[n]", s)[:width]


def money_free(s):
    """Catalog text (subscription names, sources): amounts masked, card last-4 kept."""
    return MONEY.sub(lambda m: "Rp [n]" if m.group()[:2].lower() == "rp" else "[n]", scrub(s))


def fname(s):
    return re.sub(r"\b[0-9a-f]{12,}\b", "H", re.sub(r"\d{5,}", "[n]", scrub(s)))


def fkind(name):
    """What a file is (source, bank, document kind, extension), never its name: statement filenames carry the
    owner's name and account fragments."""
    low = str(name).lower()
    ext = os.path.splitext(low)[1] or "(none)"
    if "@" in low:
        return f"email-named {ext}"
    bank = next((b for b in BANKS if re.search(rf"(?<![a-z]){b}(?![a-z])", low)), None)
    kind = next((k for k, rx in DOC_KINDS if re.search(rx, low)), None)
    parts = ["telegram-doc" if low.startswith("doc_") else None, bank, kind, "dated" if re.search(MONTHS, low) else None]
    return " ".join(p for p in parts if p) + f" {ext}" if any(parts) else f"other {ext}"


def day(ts):
    try:
        return datetime.fromtimestamp(float(ts), WIB).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return None


def tree(root, depth=2):
    """Directory sizes and counts; names masked, file contents never read."""
    rows = []
    if not os.path.isdir(root):
        return rows
    for dirpath, dirs, files in os.walk(root):
        rel = os.path.relpath(dirpath, root)
        if rel.count(os.sep) >= depth:
            dirs[:] = []
        st = [os.lstat(os.path.join(dirpath, f)) for f in files]
        rows.append({"dir": fname(rel), "files": len(files), "bytes": sum(s.st_size for s in st),
                     "exts": dict(Counter(os.path.splitext(f)[1].lower() or "(none)" for f in files).most_common(10)),
                     "kinds": dict(Counter(fkind(f) for f in files).most_common(15)),
                     "newest": day(max((s.st_mtime for s in st), default=None)), "oldest": day(min((s.st_mtime for s in st), default=None))})
    return rows


def data_files():
    out = []
    for f in sorted(os.listdir(DATA)):
        st = os.lstat(os.path.join(DATA, f))
        out.append({"name": fname(f), "bytes": st.st_size, "mtime": day(st.st_mtime), "mode": oct(st.st_mode & 0o777),
                    "type": "dir" if stat.S_ISDIR(st.st_mode) else "file"})
    return out


def secrets():
    root = "/run/secrets"
    return [{"name": f, "mode": oct(os.lstat(os.path.join(root, f)).st_mode & 0o777)} for f in sorted(os.listdir(root))] \
        if os.path.isdir(root) else []


def sockets():
    inode_pid, procs, listen = {}, [], []
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            cmd = [c.decode(errors="replace") for c in open(f"/proc/{pid}/cmdline", "rb").read().split(b"\0") if c][:6]
            status = open(f"/proc/{pid}/status").read()
            rss = re.search(r"VmRSS:\s+(\d+)", status)
            uid = re.search(r"Uid:\s+(\d+)", status)
            procs.append({"pid": int(pid), "uid": int(uid.group(1)) if uid else None, "rss_mb": int(rss.group(1)) // 1024 if rss else 0,
                          "cmd": scrub(" ".join(cmd))[:140]})
            for fd in os.listdir(f"/proc/{pid}/fd"):
                link = os.readlink(f"/proc/{pid}/fd/{fd}")
                if link.startswith("socket:["):
                    inode_pid[link[8:-1]] = int(pid)
        except OSError:
            continue
    for proto in ("tcp", "tcp6"):
        try:
            rows = open(f"/proc/net/{proto}").read().splitlines()[1:]
        except OSError:
            continue
        for row in rows:
            p = row.split()
            if p[3] != "0A":
                continue
            addr, port = p[1].split(":")
            ip = ".".join(str(int(addr[i:i + 2], 16)) for i in (6, 4, 2, 0)) if len(addr) == 8 else ("::" if set(addr) == {"0"} else "ipv6")
            listen.append({"proto": proto, "ip": ip, "port": int(port, 16), "pid": inode_pid.get(p[9])})
    return {"listen": listen, "processes": procs}


def ledger():
    con = sqlite3.connect(f"file:{LEDGER}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    q = lambda sql, *a: con.execute(sql, a).fetchall()  # noqa: E731
    tables = [r["name"] for r in q("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    ddl = [r["sql"] for r in q("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' "
                               "ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, rowid")]
    cols = {t: [c["name"] for c in q(f'PRAGMA table_info("{t}")')] for t in tables}
    fks = {t: [f"{f['from']} -> {f['table']}({f['to']})" for f in q(f'PRAGMA foreign_key_list("{t}")')] for t in tables}
    out = {"user_version": q("PRAGMA user_version")[0][0], "journal_mode": q("PRAGMA journal_mode")[0][0],
           "bytes": os.path.getsize(LEDGER), "wal_bytes": os.path.getsize(LEDGER + "-wal") if os.path.exists(LEDGER + "-wal") else 0,
           "ddl": ddl, "columns": cols, "foreign_keys": fks,
           "rows": {t: q(f'SELECT COUNT(*) FROM "{t}"')[0][0] for t in tables}}
    out["catalog"] = {t: [dict(zip(c, [money_free(r[x]) if r[x] is not None else None for x in c]))
                          for r in q(f'SELECT {", ".join(c)} FROM "{t}" ORDER BY 1')]
                      for t, c in ((t, [x for x in cs if x in cols.get(t, [])]) for t, cs in CATALOG.items()) if t in cols}
    out["thresholds"] = [r["key"] for r in q("SELECT key FROM thresholds ORDER BY key")] if "thresholds" in cols else []
    out["category_rules"] = {r[0]: r[1] for r in q("SELECT category, COUNT(*) FROM category_rules GROUP BY 1 ORDER BY 2 DESC")} \
        if "category_rules" in cols else {}
    out["category_keywords"] = {r[0]: r[1] for r in q("SELECT category, COUNT(*) FROM category_keywords GROUP BY 1 ORDER BY 2 DESC")} \
        if "category_keywords" in cols else {}
    cards = {r["id"]: r["alias"] for r in q("SELECT id, alias FROM cards")}
    accts = {r["id"]: r["alias"] for r in q("SELECT id, alias FROM accounts")}
    cov = {}
    cov["statements"] = [dict(card=cards.get(r["card_id"]), n=r["n"], first=r["f"], last=r["l"], last_due=r["d"], reconciled=r["rc"],
                              paid_marked=r["p"], lines_ok=r["lo"])
                         for r in q("SELECT card_id, COUNT(*) n, MIN(statement_date) f, MAX(statement_date) l, MAX(due_date) d,"
                                    " SUM(reconciled) rc, SUM(paid_at IS NOT NULL) p, SUM(lines_status='ok') lo FROM statements GROUP BY 1")]
    cov["statement_lines_status"] = {str(r[0]): r[1] for r in q("SELECT lines_status, COUNT(*) FROM statements GROUP BY 1")}
    cov["transactions_by_source_month"] = defaultdict(dict)
    for r in q("SELECT source, substr(txn_date,1,7) m, COUNT(*) n FROM transactions GROUP BY 1, 2 ORDER BY 2"):
        cov["transactions_by_source_month"][r["source"]][r["m"]] = r["n"]
    cov["transactions_by_owner"] = {f"card:{cards.get(r[0])}" if r[0] else f"account:{accts.get(r[1])}": r[2]
                                    for r in q("SELECT card_id, account_id, COUNT(*) FROM transactions GROUP BY 1, 2")}
    cov["transactions_flags"] = dict(q("SELECT 'merged', COUNT(*) FROM transactions WHERE merged_into IS NOT NULL")[0:1]
                                     + q("SELECT 'unverified', COUNT(*) FROM transactions WHERE status='unverified'")
                                     + q("SELECT 'uncategorised', COUNT(*) FROM transactions WHERE category IS NULL OR category=''"))
    cov["transactions_categories"] = {str(r[0]): r[1] for r in q("SELECT category, COUNT(*) FROM transactions GROUP BY 1 ORDER BY 2 DESC")}
    cov["transactions_span"] = list(q("SELECT MIN(txn_date), MAX(txn_date) FROM transactions")[0])
    cov["mutation_files"] = [dict(account=accts.get(r["account_id"]), n=r["n"], first=r["f"], last=r["l"], reconciled=r["rc"])
                             for r in q("SELECT account_id, COUNT(*) n, MIN(period_start) f, MAX(period_end) l, SUM(reconciled) rc"
                                        " FROM mutation_files GROUP BY 1")]
    cov["card_lines"] = defaultdict(dict)
    for r in q("SELECT card_id, cycle, COUNT(*) n FROM card_lines GROUP BY 1, 2 ORDER BY 2"):
        cov["card_lines"][cards.get(r["card_id"])][r["cycle"]] = r["n"]
    cov["card_line_kinds"] = {r[0]: r[1] for r in q("SELECT kind, COUNT(*) FROM card_lines GROUP BY 1 ORDER BY 2 DESC")}
    cov["card_installments"] = {cards.get(r[0]): r[1] for r in q("SELECT card_id, COUNT(*) FROM card_installments GROUP BY 1")}
    cov["card_installment_scans"] = q("SELECT COUNT(*) FROM card_installment_scans")[0][0]
    cov["balance_reports"] = [dict(account=accts.get(r[0]), n=r[1], last=r[2]) for r in
                              q("SELECT account_id, COUNT(*), MAX(as_of) FROM balance_reports GROUP BY 1")]
    cov["fund_reports"] = [dict(fund=r[0], n=r[1], last=r[2]) for r in q("SELECT fund, COUNT(*), MAX(reported_on) FROM fund_reports GROUP BY 1")]
    cov["card_payments"] = [dict(card=cards.get(r[0]), n=r[1], last=r[2]) for r in q(
        "SELECT s.card_id, COUNT(*), MAX(p.paid_on) FROM card_payments p JOIN statements s ON s.id = p.statement_id GROUP BY 1")]
    cov["debt_payments"] = [dict(debt=r[0], how=r[1], n=r[2], last=r[3]) for r in
                            q("SELECT debt_alias, how, COUNT(*), MAX(paid_on) FROM debt_payments GROUP BY 1, 2")]
    cov["plan_progress"] = {r[0]: r[1] for r in q("SELECT payday, COUNT(*) FROM plan_progress GROUP BY 1 ORDER BY 1")}
    cov["plans"] = {"count": q("SELECT COUNT(*) FROM plans")[0][0],
                    "by_payday": {r[0]: r[1] for r in q("SELECT payday, COUNT(*) FROM plans GROUP BY 1 ORDER BY 1")},
                    "latest": dict(q("SELECT id, payday, created_at FROM plans ORDER BY id DESC LIMIT 1")[0]) if q("SELECT 1 FROM plans LIMIT 1") else None}
    cov["change_log"] = [dict(tbl=r[0], action=r[1], n=r[2], last=r[3]) for r in
                         q("SELECT tbl, action, COUNT(*), MAX(at) FROM change_log GROUP BY 1, 2 ORDER BY 1, 2")]
    cov["processed_messages"] = dict(q("SELECT COUNT(*) n, MAX(processed_at) last FROM processed_messages")[0])
    cov["skipped_files"] = {free(r[0], 80): r[1] for r in q("SELECT reason, COUNT(*) FROM skipped_files GROUP BY 1 ORDER BY 2 DESC")}
    cov["doc_files"] = {"count": q("SELECT COUNT(*) FROM doc_files")[0][0],
                        "path_kinds": dict(Counter(fkind(os.path.basename(r[0] or "")) for r in q("SELECT path FROM doc_files")).most_common(15))}
    cov["ingest_checks"] = q("SELECT COUNT(*) FROM ingest_checks")[0][0]
    cov["net_snapshots"] = [r[0] for r in q("SELECT month FROM net_snapshots ORDER BY 1")]
    cov["subscriptions_by_status"] = {f"{r[0]}{' essential' if r[1] else ''}": r[2] for r in
                                      q("SELECT status, essential, COUNT(*) FROM subscriptions GROUP BY 1, 2")}
    out["coverage"] = json.loads(json.dumps(cov, default=str))
    out["usulan"] = [dict(id=r["id"], created=r["created_at"][:10], status=r["status"], title=free(r["title"], 120),
                          resolution=free(r["resolution"], 260) if r["resolution"] else None)
                     for r in q("SELECT id, created_at, status, title, resolution FROM feature_requests ORDER BY id")]
    return out


def cuti():
    out = {}
    for p in (os.path.join(DATA, "cuti_bersama.json"),) + tuple(
            os.path.join(d, "vault_tools", "data", "cuti_bersama.json") for d in sys.path if d and os.path.isdir(os.path.join(d, "vault_tools"))):
        if os.path.exists(p) and p not in out:
            try:
                j = json.load(open(p))
            except ValueError:
                out[p] = "<unreadable>"
                continue
            if isinstance(j, dict):
                out[p] = {str(k): (len(v) if isinstance(v, (list, dict)) else type(v).__name__) for k, v in sorted(j.items())}
            else:
                out[p] = {"items": len(j) if isinstance(j, list) else type(j).__name__}
    return out


def packages():
    from importlib import metadata
    return sorted(f"{d.metadata['Name']}=={d.version}" for d in metadata.distributions() if d.metadata["Name"])


result = {"python": sys.version.split()[0], "user": os.getuid(), "cwd": os.getcwd(),
          "env_names": sorted(os.environ), "env_safe": {k: scrub(os.environ[k]) for k in ("HTTPS_PROXY", "NO_PROXY", "TZ", "PYTHONPATH")
                                                        if k in os.environ}}
for key, fn in (("packages", packages), ("data", data_files), ("ingest", lambda: tree(INGEST, 3)), ("secrets", secrets),
                ("sockets", sockets), ("ledger", ledger), ("cuti", cuti)):
    try:
        result[key] = fn()
    except Exception as exc:
        result[key] = {"<error>": f"{type(exc).__name__}: {scrub(exc)[:200]}"}
result["collected_at"] = datetime.now(WIB).isoformat(timespec="seconds")
print(json.dumps(result, sort_keys=True, default=str))
