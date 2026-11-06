"""Dry run of NEW vault-tools code on a COPY of the live ledger: migration, re-reading every statement's lines, the audit,
the payday plan for the coming 1st and the pot projection. The live ledger is never written.
Run (from the repo root):
  ssh ubuntu@<vps> 'mkdir -p dry-vt' && rsync -az --delete services/vault-tools/vault_tools/ ubuntu@<vps>:dry-vt/vault_tools/
  ssh ubuntu@<vps> 'sudo docker exec personal-agent-vault-tools-1 rm -rf /tmp/dry && sudo docker exec personal-agent-vault-tools-1 mkdir -p /tmp/dry \
    && tar -C dry-vt -cf - vault_tools | sudo docker exec -i personal-agent-vault-tools-1 tar -C /tmp/dry -xf - \
    && sudo docker exec -i personal-agent-vault-tools-1 python -' < ops/calibration/dry_run.py
  then: ssh ubuntu@<vps> 'rm -rf dry-vt'   (docker cp cannot write into the container's /tmp; tar can)
Every statement must come back 'cocok' before a deploy."""
import sqlite3
import sys
from datetime import date

sys.path.insert(0, "/tmp/dry")
src = sqlite3.connect("/data/ledger.db")
dst = sqlite3.connect("/tmp/dry/ledger.db")
src.backup(dst)
src.close()
dst.close()

from vault_tools import audit, card_lines, statement_pdf, tools  # noqa: E402
from vault_tools.ledger import SCHEMA_VERSION, connect  # noqa: E402

conn = connect("/tmp/dry/ledger.db")
print("schema", conn.execute("PRAGMA user_version").fetchone()[0], "expected", SCHEMA_VERSION)
pw = statement_pdf.load_passwords("/run/secrets/pdf_passwords")
st = {}
for r in conn.execute("SELECT id FROM statements ORDER BY statement_date").fetchall():
    s = card_lines.process_statement(conn, r["id"], "/ingest", pw)["status"]
    st[s] = st.get(s, 0) + 1
print("re-read:", st, "of", conn.execute("SELECT count(*) FROM statements").fetchone()[0])
today = tools.wib_today()
print("\n" + audit.format_audit(audit.run(conn, today)))
first = date(today.year + (today.month == 12), today.month % 12 + 1, 1) if today.day > 7 else today
snap = tools.generate_payday_plan(conn, first)
print("\n" + tools.summarize_plan(snap))
print("\n" + tools.sinking_status(conn, today))
