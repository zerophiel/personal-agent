"""Bills paid once (usulan #6, 31 Oct 2026: arrears such as two months of Coway) and undoing an instalment recorded by
mistake. A bill is in the plan of every payday after the day it was recorded whose window reaches its due date, while it is
open: one recorded after the salary came leaves the running plan as it is and is said to be paid from the balance or planned
first at the next payday. The server's day decides, never the host clock."""
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import one_off, simulate, tools  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

from test_payday_progress import BEFORE, HAVE_SERVER, KEY, NOV_1, PAYDAY, world  # noqa: E402

if HAVE_SERVER:
    from vault_tools.server import MCP_TOOL_NAMES, create_app

NOV_10, NOV_15, NOV_30 = date(2026, 11, 10), date(2026, 11, 15), date(2026, 11, 30)


def bill_world(path=":memory:"):
    conn = world(path)
    PayeeVault(conn, KEY).store("coway-va", "va", "BCA", "8" * 12)
    return conn


def catat(conn, today, alias="coway-tunggakan", amount=540_000, due="2026-11-05", **kw):
    return tools.one_off_bills(conn, today, "catat", alias, kw.pop("name", "Coway 2 bulan"), amount, due, **kw)


def amounts(snap):
    out = {}
    for t in snap["transfers"]:
        out[t["to_alias"]] = out.get(t["to_alias"], 0) + t["amount"]
    return out


class Placement(unittest.TestCase):
    def test_recorded_before_the_payday_is_in_its_plan(self):
        conn = bill_world()
        self.assertIn("masuk rencana gajian 2026-10-30", catat(conn, BEFORE, pay_to="coway-va"))
        snap = tools.generate_payday_plan(conn, PAYDAY)
        t = next(t for t in snap["transfers"] if t["to_alias"] == "coway-tunggakan")
        self.assertEqual((t["amount"], t["reason"], t["date"], t["pay_to"]), (540_000, "tagihan sekali bayar", "2026-11-02", "coway-va"))
        self.assertIn("⏳ coway-tunggakan Rp 540.000 [tagihan sekali, jatuh tempo 2026-11-05] (setelah ditransfer: transfer_selesai)",
                      tools.payday_status(conn, PAYDAY))
        self.assertIn("ada di rencana gajian 2026-10-30 (status_gajian)", tools.one_off_bills(conn, NOV_1, "daftar"))

    def test_recorded_after_the_payday_leaves_the_running_plan_as_it_is(self):
        conn = bill_world()
        before = tools.generate_payday_plan(conn, PAYDAY)
        out = catat(conn, NOV_1, "pajak", 300_000, "2026-11-20", name="Pajak motor")
        self.assertIn("dicatat setelah gajian 2026-10-30, jadi tidak ada di rencana yang sedang berjalan: bila harus dibayar "
                      "sebelum gajian 2026-11-30, dari saldo yang ada", out)
        self.assertIn("Nomor tujuannya belum didaftarkan", out)
        now = tools.generate_payday_plan(conn, NOV_1)
        self.assertEqual(now["transfers"], before["transfers"])
        self.assertTrue(any(r.startswith("TAGIHAN SEKALI BAYAR pajak Rp 300.000 jatuh tempo 2026-11-20: dicatat setelah gajian "
                                         "2026-10-30, jadi tidak ada di rencana ini") for r in now["reminders"]))
        self.assertIn("TAGIHAN SEKALI BAYAR pajak", tools.payday_status(conn, NOV_1))
        nxt = tools.generate_payday_plan(conn, NOV_30)        # still open at the next payday: planned there first (overdue)
        t = next(t for t in nxt["transfers"] if t["to_alias"] == "pajak")
        self.assertEqual((t["amount"], t["date"]), (300_000, "2026-11-30"))
        names = [t["to_alias"] for t in nxt["transfers"]]
        self.assertLess(names.index("pajak"), names.index("sekolah-va"))     # overdue: before the bills still to fall due

    def test_recorded_more_than_a_week_after_the_payday(self):
        """current_payday already points at the coming payday then: the answer and the reminder still name the right plan."""
        conn = bill_world()
        out = catat(conn, NOV_10, "pajak", 300_000, "2026-11-20", name="Pajak motor")
        self.assertIn("dicatat setelah gajian 2026-10-30", out)
        self.assertIn("sebelum gajian 2026-11-30", out)
        self.assertIn("masuk rencana gajian 2026-11-30", catat(conn, NOV_10, "servis", 800_000, "2026-12-10", name="Servis"))
        reminders = tools.generate_payday_plan(conn, NOV_10)["reminders"]
        self.assertIn("TAGIHAN SEKALI BAYAR pajak Rp 300.000 jatuh tempo 2026-11-20, SEBELUM gajian 2026-11-30: rencana ini "
                      "membayarnya di hari gajian. Bila harus dibayar sebelum itu: dari saldo yang ada (pemilik yang memutuskan dari "
                      "mana), lalu tagihan_sekali aksi=lunas.", reminders)
        self.assertFalse(any("servis" in r for r in reminders))

    def test_paid_it_leaves_later_plans_and_stays_done_in_its_own(self):
        conn = bill_world()
        catat(conn, BEFORE, pay_to="coway-va")
        tools.generate_payday_plan(conn, PAYDAY)
        self.assertEqual(tools.one_off_bills(conn, NOV_1, "lunas", "coway-tunggakan"),
                         "coway-tunggakan tercatat LUNAS 2026-11-01. Progres rencana gajian 2026-10-30 ikut tercatat.")
        snap = tools.generate_payday_plan(conn, NOV_1)
        self.assertEqual(amounts(snap)["coway-tunggakan"], 540_000)      # the plan is the same; only its progress moved
        it = next(i for i in snap["progress"]["items"] if i["to"] == "coway-tunggakan")
        self.assertEqual((it["done"], it["on"]), (540_000, "2026-11-01"))
        self.assertNotIn("coway-tunggakan", amounts(tools.generate_payday_plan(conn, NOV_30)))

    def test_paid_late_is_still_its_plans(self):
        conn = bill_world()
        catat(conn, BEFORE)
        self.assertIn("Progres rencana gajian 2026-10-30 ikut tercatat.", tools.one_off_bills(conn, NOV_15, "lunas", "coway-tunggakan"))

    def test_paid_before_the_payday_is_outside_every_plan(self):
        conn = bill_world()
        catat(conn, date(2026, 10, 20))
        self.assertIn("Dibayar di luar rencana gajian", tools.one_off_bills(conn, BEFORE, "lunas", "coway-tunggakan"))
        self.assertNotIn("coway-tunggakan", amounts(tools.generate_payday_plan(conn, PAYDAY)))

    def test_the_servers_day_decides_not_the_host_clock(self):
        conn = bill_world()
        catat(conn, BEFORE)
        conn.execute("UPDATE one_off_bills SET created_at = '2026-11-05T09:00:00+07:00'")     # a host clock days ahead
        self.assertIn("coway-tunggakan", amounts(tools.generate_payday_plan(conn, PAYDAY)))


class Flows(unittest.TestCase):
    def test_transfer_selesai_pays_it_and_undo_reopens(self):
        conn = bill_world()
        catat(conn, BEFORE, pay_to="coway-va")
        self.assertIn("Tercatat selesai (gajian 2026-10-30): coway-tunggakan Rp 540.000.",
                      tools.mark_transfers_done(conn, NOV_1, ["coway-tunggakan"]))
        row = conn.execute("SELECT status, paid_on FROM one_off_bills").fetchone()
        self.assertEqual(tuple(row), ("lunas", "2026-11-01"))
        self.assertIn("✅ coway-tunggakan Rp 540.000 (2026-11-01)", tools.payday_status(conn, NOV_1))
        self.assertIn("Tanda selesai dihapus: coway-tunggakan", tools.mark_transfers_done(conn, NOV_1, ["coway-tunggakan"], undo=True))
        self.assertEqual(tuple(conn.execute("SELECT status, paid_on FROM one_off_bills").fetchone()), ("terbuka", None))

    def test_list_cancel_reopen_change(self):
        conn = bill_world()
        catat(conn, BEFORE, pay_to="coway-va", note="dua bulan")
        self.assertIn("- coway-tunggakan (Coway 2 bulan) Rp 540.000, jatuh tempo 2026-11-05, bayar ke coway-va; catatan: dua bulan; "
                      "masuk rencana gajian 2026-10-30", tools.one_off_bills(conn, BEFORE, "daftar"))
        out = catat(conn, BEFORE, amount=600_000, name="", pay_to="", method="", note="")     # empty fields keep what is stored
        self.assertIn("(Coway 2 bulan) Rp 600.000, jatuh tempo 2026-11-05, bayar ke coway-va; catatan: dua bulan", out)
        self.assertIn("dibatalkan", tools.one_off_bills(conn, BEFORE, "batal", "coway-tunggakan"))
        self.assertNotIn("coway-tunggakan", amounts(tools.generate_payday_plan(conn, PAYDAY)))
        self.assertIn("BATAL", tools.one_off_bills(conn, BEFORE, "daftar"))
        self.assertIn("terbuka lagi", tools.one_off_bills(conn, BEFORE, "buka", "coway-tunggakan"))
        self.assertEqual(amounts(tools.generate_payday_plan(conn, PAYDAY))["coway-tunggakan"], 600_000)
        changes = conn.execute("SELECT action FROM change_log WHERE tbl='one_off_bills' ORDER BY id").fetchall()
        self.assertEqual([r[0] for r in changes], ["baru", "ubah", "ubah", "ubah"])

    def test_refused(self):
        conn = bill_world()
        for alias in ("sekolah", "sekolah-va", "dbs-1", "cicilan-mobil", "hutang-teman", "uang-harian", "dana-darurat", "tabungan",
                      "X", "a"):
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                catat(conn, BEFORE, alias)
        for kw in ({"amount": 0}, {"due": "besok"}, {"method": "tunai"}, {"pay_to": "belum-ada"}, {"name": ""}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                catat(conn, BEFORE, **kw)
        catat(conn, BEFORE)
        with self.assertRaises(ValueError):
            tools.one_off_bills(conn, BEFORE, "lunas", "coway-tunggakan", paid_on="2026-10-28")    # after today
        tools.one_off_bills(conn, BEFORE, "lunas", "coway-tunggakan")
        with self.assertRaisesRegex(ValueError, "sudah lunas"):
            catat(conn, BEFORE)
        with self.assertRaises(ValueError):
            tools.one_off_bills(conn, BEFORE, "hapus", "coway-tunggakan")

    def test_numbers_typed_in_are_never_stored(self):
        conn = bill_world()
        catat(conn, BEFORE, name="VA " + "7" * 12, note="rek " + "1" * 10)
        row = conn.execute("SELECT name, note FROM one_off_bills").fetchone()
        self.assertEqual(tuple(row), ("VA [angka]", "rek [angka]"))


class Simulation(unittest.TestCase):
    def test_the_cycle_whose_plan_has_it_pays_it(self):
        conn = bill_world()
        catat(conn, BEFORE)                                              # in the 30 Oct plan
        catat(conn, NOV_1, "pajak", 300_000, "2026-11-20", name="Pajak")  # first in the 30 Nov plan
        tools.set_threshold(conn, "biaya_admin_transfer", 6_500)
        rows = simulate.simulate(conn, NOV_1, months=3)["rows"]
        self.assertEqual([r["once"] for r in rows], [540_000, 300_000, 0])
        self.assertEqual(rows[1]["fees"] - rows[2]["fees"], 6_500)       # with its fee
        plain = simulate.simulate(world(), NOV_1, months=1)["rows"][0]
        self.assertEqual(plain["cash"] - rows[0]["cash"], 540_000 + rows[0]["fees"])


class UndoInstalment(unittest.TestCase):
    def debt(self, conn, alias="cicilan-mobil"):
        return tuple(conn.execute("SELECT tenor_left, outstanding FROM debts WHERE alias=?", (alias,)).fetchone())

    def test_exactly_as_before(self):
        conn = world()
        tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000)
        self.assertEqual(self.debt(conn), (9, 13_500_000))
        out = tools.undo_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000)
        self.assertIn("catatan angsuran jatuh tempo 2026-11-02 (Rp 1.500.000, dicatat dibayar 2026-10-30) dibatalkan. Sisa 10 "
                      "angsuran, sisa utang Rp 15.000.000. Autodebet untuk jatuh tempo itu dihitung lagi.", out)
        self.assertEqual(self.debt(conn), (10, 15_000_000))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM debt_payments").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM change_log WHERE tbl='debt_payments' AND action='hapus'").fetchone()[0], 1)
        self.assertIn("⏳ cicilan-mobil Rp 1.500.000", tools.payday_status(conn, PAYDAY))

    def test_a_balance_clipped_at_zero_comes_back_as_it_was(self):
        conn = world()
        tools.upsert_debt(conn, "cicilan-mobil", "MTF", 100_000, 1_500_000, 1, 2, 815, pay_method="autodebit",
                          debit_account_alias="mandiri-utama")
        tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000)
        self.assertEqual(self.debt(conn), (0, 0))
        tools.undo_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000)
        self.assertEqual(self.debt(conn), (1, 100_000))

    def test_a_record_from_before_the_log(self):
        conn = world()
        conn.execute("INSERT INTO debt_payments(debt_alias, due_date, amount, paid_on, how, created_at) VALUES "
                     "('spaylater', '2026-11-01', 300000, '2026-10-30', 'manual', 't')")
        conn.execute("UPDATE debts SET tenor_left = 4, outstanding = 1200000 WHERE alias = 'spaylater'")
        tools.undo_debt_payment(conn, PAYDAY, "spaylater", 300_000)
        self.assertEqual(self.debt(conn, "spaylater"), (5, 1_500_000))

    def test_the_wrong_record_is_refused(self):
        conn = world()
        with self.assertRaisesRegex(ValueError, "tidak ada angsuran spaylater"):
            tools.undo_debt_payment(conn, PAYDAY, "spaylater", 300_000)
        tools.record_debt_payment(conn, PAYDAY, "spaylater", 300_000)
        with self.assertRaisesRegex(ValueError, "tercatat Rp 300.000, bukan Rp 200.000"):
            tools.undo_debt_payment(conn, PAYDAY, "spaylater", 200_000)
        with self.assertRaises(ValueError):
            tools.undo_debt_payment(conn, PAYDAY, "spaylater", 300_000, "2026-12-01")
        self.assertEqual(self.debt(conn, "spaylater"), (4, 1_200_000))

    def test_one_due_date(self):
        conn = world()
        tools.record_debt_payment(conn, PAYDAY, "spaylater", 300_000, due="2026-11-01")
        tools.record_debt_payment(conn, PAYDAY, "spaylater", 300_000, due="2026-12-01")
        tools.undo_debt_payment(conn, PAYDAY, "spaylater", 300_000, "2026-11-01")
        self.assertEqual([r[0] for r in conn.execute("SELECT due_date FROM debt_payments")], ["2026-12-01"])
        self.assertEqual(self.debt(conn, "spaylater"), (4, 1_200_000))
        tools.undo_debt_payment(conn, PAYDAY, "spaylater", 300_000)             # without a date: the record made last
        self.assertEqual(self.debt(conn, "spaylater"), (5, 1_500_000))


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class ThroughTheTools(unittest.TestCase):
    def test_with_empty_fields_as_a_model_sends_them(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "l.db")
            bill_world(path).close()
            app = create_app(path, KEY, "m" * 40, "i" * 40, allowed_hosts=["testserver"], today=lambda: PAYDAY,
                             ingest_dir=d, passwords_path=None)
            call = lambda n, a=None: json.dumps(asyncio.run(app.state.mcp.call_tool(n, a or {})), default=str, ensure_ascii=False)  # noqa: E731
            self.assertIn("tagihan_sekali", MCP_TOOL_NAMES)
            out = call("tagihan_sekali", {"aksi": "catat", "alias": "coway-tunggakan", "nama": "Coway", "jumlah": 540_000,
                                          "jatuh_tempo": "2026-11-05", "bayar_ke": "", "cara": "", "tanggal": "", "catatan": ""})
            self.assertIn("dicatat setelah gajian 2026-10-30", out)        # recorded on the payday itself: not in its plan
            self.assertIn("coway-tunggakan (Coway) Rp 540.000", call("tagihan_sekali", {"aksi": "daftar", "alias": ""}))
            call("cicilan_dibayar", {"alias": "spaylater", "jumlah": 300_000, "cara": "", "jatuh_tempo": ""})
            self.assertIn("dibatalkan", call("cicilan_dibayar", {"alias": "spaylater", "jumlah": 300_000, "cara": "",
                                                                 "jatuh_tempo": "", "batal": True}))
            db = sqlite3.connect(path)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM debt_payments").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT recorded_on FROM one_off_bills").fetchone()[0], "2026-10-30")
            db.close()


if __name__ == "__main__":
    unittest.main()
