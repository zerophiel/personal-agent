"""Cross-source audit: each rule finds the one inconsistency it is written for, and a clean ledger reports nothing."""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import full_world  # noqa: E402

from vault_tools import audit, reports, tools  # noqa: E402
from vault_tools import card_installments as ci  # noqa: E402
from vault_tools import mutations as mu  # noqa: E402
from vault_tools import subscriptions as sub  # noqa: E402

TODAY = date(2026, 11, 1)


def world():
    conn = full_world()
    tools.upsert_card(conn, "jenius-1", "Jenius", "0480", 26, 13, 30_000_000)
    return conn


def stmt(conn, d, due, total=1_000_000, minimum=100_000, reconciled=1, lines_status="cocok", lines_diff=0, paid=0, card_id=1):
    cur = conn.execute("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
                       "minimum_due,reconciled,recon_diff,ingested_at,paid_amount,lines_status,lines_diff) VALUES (?,?,?,?,0,0,?,0,?,?,?,?,'t',?,?,?)",
                       (card_id, f"{card_id}-{d}".ljust(64, "x"), d, due, total, total, minimum, reconciled, 0 if reconciled else 5_000,
                        paid, lines_status, lines_diff))
    conn.commit()
    return cur.lastrowid


def line(conn, sid, cycle, desc, amount, kind="langganan", card_id=1):
    conn.execute("INSERT INTO card_lines(statement_id,card_id,cycle,txn_date,description,amount,kind,category) VALUES (?,?,?,?,?,?,?,?)",
                 (sid, card_id, cycle, cycle, desc, amount, kind, kind))
    conn.commit()


def found(conn, level=None):
    return [t for s, t in audit.run(conn, TODAY) if level is None or s == level]


class Audit(unittest.TestCase):
    def test_a_clean_ledger_reports_nothing(self):
        conn = world()
        sid = stmt(conn, "2026-10-26", "2026-11-13")
        sub.upsert(conn, "netflix", "Netflix", 186_000, "jenius-1")
        line(conn, sid, "2026-10-26", "NETFLIX.COM SINGAPORE", 186_000)
        tools.set_pot_balance(conn, "hutang-teman", 0, TODAY)
        self.assertEqual(audit.run(conn, TODAY), [])
        self.assertIn("semua sumber cocok", audit.format_audit([]))

    def test_a_bank_row_stored_twice_across_two_files(self):
        conn = world()
        mu.record_mutations(conn, "mandiri-utama", "a" * 64, "2026-10-01", "2026-10-31", 1_000_000, 940_000,
                            [{"date": "2026-10-05", "description": "QRIS KOPI", "amount": -50_000},
                             {"date": "2026-10-15", "description": "BIAYA TRF", "amount": -10_000}])
        self.assertEqual([t for t in found(conn) if t.startswith("Mutasi")], [])
        # what the 1 Nov e-statement did before the fix: another file's copy of a row, worded differently
        conn.execute("INSERT INTO transactions(account_id,txn_date,merchant,amount,status,source,dedupe_key,file_hash)"
                     " SELECT account_id, txn_date, 'QR KOPI', amount, 'unverified', 'mutation', 'b', ? FROM transactions"
                     " WHERE merchant='QRIS KOPI'", ("b" * 64,))
        bad = [t for t in found(conn, "bad") if t.startswith("Mutasi")]
        self.assertEqual(len(bad), 1)
        self.assertIn("mandiri-utama 2026-10-01 s.d. 2026-10-31", bad[0])
        self.assertIn("berjumlah -Rp 110.000", bad[0])
        self.assertIn("selisih Rp 50.000", bad[0])

    def test_statement_totals_and_lines(self):
        conn = world()
        stmt(conn, "2026-09-26", "2026-10-13", reconciled=0, paid=1_000_000)
        stmt(conn, "2026-10-26", "2026-11-13", lines_status="selisih", lines_diff=-125_000)
        self.assertTrue(any("total tidak rekonsiliasi" in t for t in found(conn, "bad")))
        self.assertTrue(any("selisih Rp 125.000" in t for t in found(conn, "warn")))

    def test_a_missing_newest_statement_and_an_unpaid_past_due_bill(self):
        conn = world()
        stmt(conn, "2026-09-20", "2026-10-08", minimum=300_000, paid=100_000)
        bad = found(conn, "bad")
        self.assertTrue(any("belum tercatat dibayar minimal Rp 300.000" in t for t in bad))
        self.assertTrue(any("Tagihan bulan ini belum diunggah" in t for t in found(conn, "warn")))
        conn.execute("UPDATE statements SET paid_amount=300000")
        conn.commit()
        self.assertTrue(any("sisa Rp 700.000" in t and "sudah terpenuhi (tidak telat" in t for t in found(conn, "info")))
        self.assertFalse(any("Rp 700.000" in t for t in found(conn, "warn") + found(conn, "bad")))   # minimum met: no warning

    def test_subscriptions_against_what_the_cards_charged(self):
        conn = world()
        sid = stmt(conn, "2026-10-26", "2026-11-13")
        sub.upsert(conn, "google-one", "Google One", 309_000, "jenius-1")
        sub.upsert(conn, "spotify", "Spotify", 119_900, "hsbc-1")
        for amount in (1_752_690, 876_900, 175_380):
            line(conn, sid, "2026-10-26", "GOOGLE ONE 650-253", amount)
        conn.execute("UPDATE subscriptions SET updated_at='2026-10-01T00:00:00+00:00'")      # recorded before that bill
        conn.commit()
        warn = found(conn, "warn")
        self.assertTrue(any("google-one" in t and "Rp 309.000" in t and "Rp 2.804.970" in t for t in warn))
        self.assertTrue(any("spotify" in t and "tidak terlihat" in t for t in found(conn, "info")))
        conn.execute("UPDATE subscriptions SET updated_at='2026-10-28T00:00:00+00:00' WHERE alias='google-one'")   # the owner explained it after
        conn.commit()
        self.assertFalse(any("google-one" in t for t in found(conn, "warn")))
        self.assertTrue(any("google-one" in t and "diperbarui pemilik setelah tagihan" in t for t in found(conn, "info")))

    def test_two_records_of_one_merchant_are_compared_together(self):
        conn = world()
        sid = stmt(conn, "2026-10-26", "2026-11-13")
        sub.upsert(conn, "squarespace-workspace", "Email domain (Workspace via Squarespace)", 304_140, "cimb-1")
        sub.upsert(conn, "domain-squarespace", "Domain (Squarespace)", 15_349, "cimb-1")
        line(conn, sid, "2026-10-26", "SQSP* WORKSP#123 NEW YORK", 304_140)
        self.assertFalse([t for t in found(conn) if "squarespace" in t])

    def test_a_stopped_subscription_still_charged(self):
        conn = world()
        sid = stmt(conn, "2026-10-26", "2026-11-13")
        sub.upsert(conn, "catchplay", "Catchplay", 0, "cimb-1", status="ended")
        line(conn, sid, "2026-10-26", "CATCHPLAY KOWLOON HKG", 49_950)
        conn.execute("UPDATE subscriptions SET updated_at='2026-10-01T00:00:00+00:00'")
        conn.commit()
        self.assertTrue(any("catchplay" in t and "tercatat BERHENTI" in t for t in found(conn, "warn")))
        conn.execute("UPDATE subscriptions SET updated_at='2026-10-28T00:00:00+00:00'")      # stopped after that bill: fine
        conn.commit()
        self.assertFalse([t for t in found(conn) if "atchplay" in t])

    def test_a_repeating_charge_that_is_not_recorded(self):
        conn = world()
        a = stmt(conn, "2026-09-26", "2026-10-13", paid=1_000_000)
        b = stmt(conn, "2026-10-26", "2026-11-13")
        line(conn, a, "2026-09-26", "CANVA PTE LTD SG", 95_000)
        line(conn, b, "2026-10-26", "CANVA PTE LTD SG", 95_000)
        self.assertTrue(any("'Canva Pte'" in t and "belum tercatat sebagai langganan" in t for t in found(conn, "info")))

    def test_an_instalment_that_left_the_newest_statement(self):
        conn = world()
        ci.record(conn, "jenius-1", "2026-09-26", [{"description": "Shopee 12 bulan", "amount": 476_990, "seq": 10, "total": 12}])
        stmt(conn, "2026-09-26", "2026-10-13", paid=1_000_000)
        sid = stmt(conn, "2026-10-26", "2026-11-13")
        line(conn, sid, "2026-10-26", "TOKOPEDIA", 50_000, kind="belanja")
        self.assertTrue(any("Shopee 12 bulan" in t and "tidak terlihat di tagihan 2026-10-26" in t for t in found(conn, "warn")))
        line(conn, sid, "2026-10-26", "INSTALLMENT 11/12 SHOPEE", 476_990, kind="cicilan")
        self.assertFalse(any("Shopee 12 bulan" in t for t in found(conn)))

    def test_an_old_pot_balance(self):
        conn = world()                                           # the fund was set up on 2026-10-27
        info = [t for s, t in audit.run(conn, date(2026, 12, 15)) if s == "info"]
        self.assertTrue(any("Saldo pot hutang-teman" in t for t in info))

    def test_the_plan_and_the_report_carry_the_findings(self):
        conn = world()
        stmt(conn, "2026-09-20", "2026-10-08", minimum=300_000, paid=100_000)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertTrue(any(w.startswith("Data: ") and "belum tercatat dibayar minimal" in w for w in snap["warnings"]))
        html = reports.build(conn, "periksa", TODAY)
        self.assertIn("Periksa data", html)
        self.assertIn("⛔", html)


if __name__ == "__main__":
    unittest.main()
