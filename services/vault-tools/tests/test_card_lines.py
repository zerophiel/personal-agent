import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import TODAY, full_world  # noqa: E402

from vault_tools import card_installments as ci  # noqa: E402
from vault_tools import card_lines as cl  # noqa: E402
from vault_tools import reports, tools  # noqa: E402
from vault_tools.statements import record_statement  # noqa: E402

try:
    from vault_tools.server import create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False

OCT = date(2026, 10, 19)


class Amounts(unittest.TestCase):
    def test_every_bank_number_style(self):
        for text, want in (("125.000", 125_000), ("304,140.01", 304_140), ("7,000.00", 7_000), ("2,274,554", 2_274_554),
                           ("1.234,56", 1_235), ("1,950,604.24", 1_950_604), ("99.50", 100), ("0,49", 0), ("15,000,000", 15_000_000)):
            self.assertEqual(cl.parse_amount(text), want, text)


class Parsing(unittest.TestCase):
    def test_the_seven_layouts_seen_in_real_statements(self):
        text = "\n".join([
            "12-OKT 12-OKT BIAYA IURAN TAHUNAN 125.000",                         # day-MON (Indonesian months)
            "30-SEP 30-SEP PEMBAYARAN - MBCA 727.869 CR",
            "25/09 26/09 SQSP* WORKSP#252263611 NEW YORK USA 304,140.01",       # day/month, cents
            "16/10 16/10 GoPro.com/Subscription SAN MATEO USA BILLED AS USD 65.16(1 USD = 18202.45 IDR 1,186,072.29",
            "15-Sep-26 17-Sep-26 IDM QRIS LIVIN Jakarta 7,000.00",              # day-Mon-yy
            "30/09/2026 30/09/2026 PAYMENT VIA BIFAST RECEIVED 2,274,554 CR",    # day/month/year
            "22/10/2026 22/10/2026 Tokopedia 03 OF 12 1,855,353",
            "09/30 09/30 Payment BIFAST Rp. 1,215,273CR",                        # month/day (DBS), Rp. prefix, CR glued
            "10/20 10/20 INSTLMNT Tokopedia (006/018) Rp. 200,244",
            "07 Okt 2026 08 Okt 2026 ANTHROPIC* CLAUDE SUB USCA (USD 107.23) 1,950,604.24",   # Jenius
            "22SEP 21SEP APPLE.COM/BILLCORKIE 319,000",                          # HSBC: squashed
            "16OCT 15OCT PaymentBANKMANDIRI JP 23,100,000CR",
            # noise that must NOT become lines
            "16-Oct-26 05-Nov-26",
            "10/25/2026 11/10/2026 Rp. 2,386,662 Rp. 201,221",
            "1 dari 5",
            "30 DES'26.INFO 1500888",
        ])
        lines = cl.parse_text(text, OCT)
        self.assertEqual(len(lines), 12)
        by = {x["description"][:12]: x for x in lines}
        self.assertEqual(by["BIAYA IURAN "]["amount"], 125_000)
        self.assertEqual(by["PEMBAYARAN -"]["amount"], -727_869)
        self.assertEqual(by["GoPro.com/Su"]["amount"], 1_186_072)                 # the IDR figure, not the USD one
        self.assertEqual(by["Payment BIFA"]["amount"], -1_215_273)
        self.assertEqual(by["ANTHROPIC* C"]["amount"], 1_950_604)
        self.assertEqual(by["PaymentBANKM"]["amount"], -23_100_000)
        self.assertEqual(by["BIAYA IURAN "]["txn_date"], "2026-10-12")
        self.assertEqual(by["APPLE.COM/BI"]["txn_date"], "2026-09-22")

    def test_month_first_dates_for_dbs(self):
        (x,) = cl.parse_text("09/24 09/28 HALODOC JAKARTA Rp. 395,200", OCT, month_first=True)
        self.assertEqual(x["txn_date"], "2026-09-24")

    def test_a_december_line_on_a_january_statement_is_last_year(self):
        (x,) = cl.parse_text("15-DES 16-DES TOKO 100.000", date(2026, 1, 12))
        self.assertEqual(x["txn_date"], "2025-12-15")


class Classify(unittest.TestCase):
    def test_kinds(self):
        cases = [("PEMBAYARAN - MBCA", -1, "pembayaran"), ("PAYMENT THANK YOU - Livin", -1, "pembayaran"),
                 ("MANDIRICASHMANAGEMENTJKT ID ID", -1, "pembayaran"), ("TOKOPEDIA JAKARTA ID", -1, "refund"),
                 ("CICILAN BCA KE 10 DARI 12, TOKOPEDIA.COM", 1, "cicilan"), ("Tokopedia 03 OF 12", 1, "cicilan"),
                 ("INSTLMNT CICIL TAGIHAN MIN DU (010/018)", 1, "cicilan"), ("INSTALLMENT - 3/6 @ SHOPEE 6 MONTHS", 1, "cicilan"),
                 ("INTEREST CHARGE", 1, "bunga"), ("BIAYA BUNGA", 1, "bunga"), ("FINANCE CHARGES", 1, "bunga"),
                 ("PAYMENT FEE VIA MANDIRI", 1, "biaya"), ("STAMPDUTYFEE", 1, "biaya"), ("OVERLIMIT FEE", 1, "biaya"),
                 ("E-BILLING STATEMENT CHRGE", 1, "biaya"), ("BIAYA KETERLAMBATAN", 1, "biaya"),
                 ("KOPI COFFEE SHOP", 1, "belanja"), ("NETFLIX.COM SINGAPORE", 1, "belanja")]
        for desc, sign, want in cases:
            self.assertEqual(cl.classify(desc, sign * 1000), want, desc)


def card_world():
    conn = full_world()
    tools.upsert_card(conn, "bca-1", "BCA", "1111", 12, 28, 10_000_000)
    return conn


STATEMENT = "\n".join([
    "12-OKT 12-OKT BIAYA IURAN TAHUNAN 125.000",
    "14-SEP 15-SEP OPENAI SAN FRANCISCO US 99.510",
    "21-SEP 21-SEP STEAMGAMES.COM 337.995",
    "27-SEP 27-SEP GOPAYID JAKARTA ID 109.350",
    "01-OKT 01-OKT CICILAN BCA KE 10 DARI 12, TOKOPEDIA.COM 289.853",
    "05-OKT 05-OKT KOPI KENANGAN JAKARTA 93.500",
    "12-OKT 12-OKT TOKO ELEKTRONIK JAKARTA 2.500.000",
    "12-OKT 12-OKT BIAYA BUNGA 150.928",
    "29-SEP 29-SEP BIAYA KETERLAMBATAN 90.502",
    "30-SEP 30-SEP PEMBAYARAN - MBCA 727.869 CR",
])
DEBITS = 125_000 + 99_510 + 337_995 + 109_350 + 289_853 + 93_500 + 2_500_000 + 150_928 + 90_502


def add_statement(conn, h="a" * 64, prev=9_050_165, paid=727_869, debits=DEBITS):
    total = prev - paid + debits
    return record_statement(conn, "bca-1", h, "2026-10-12", "2026-10-28", prev, paid, debits - 241_430, 241_430, total, 100_000)["statement_id"]


class Store(unittest.TestCase):
    def test_lines_that_add_up_are_marked_cocok_and_classified(self):
        conn = card_world()
        sid = add_statement(conn)
        out = cl.store(conn, sid, cl.parse_text(STATEMENT, date(2026, 10, 12)))
        self.assertEqual((out["status"], out["diff"], out["lines"]), ("cocok", 0, 10))
        got = {r["description"][:10]: (r["kind"], r["category"]) for r in conn.execute("SELECT * FROM card_lines")}
        self.assertEqual(got["OPENAI SAN"], ("langganan", "langganan"))
        self.assertEqual(got["STEAMGAMES"], ("belanja", "game-digital"))
        self.assertEqual(got["GOPAYID JA"], ("belanja", "top-up e-wallet"))
        self.assertEqual(got["KOPI KENAN"], ("belanja", "makan"))
        self.assertEqual(got["CICILAN BC"], ("cicilan", "cicilan"))
        self.assertEqual(got["BIAYA BUNG"], ("bunga", "bunga"))
        self.assertEqual(got["PEMBAYARAN"], ("pembayaran", "pembayaran"))

    def test_a_missing_line_is_reported_not_hidden(self):
        conn = card_world()
        sid = add_statement(conn)
        out = cl.store(conn, sid, cl.parse_text(STATEMENT, date(2026, 10, 12))[1:])      # the 125.000 fee line lost
        self.assertEqual((out["status"], out["diff"]), ("selisih", -125_000))
        self.assertIn("selisih Rp 125.000", cl.format_summary(cl.summary(conn)))

    def test_a_masked_instalment_line_is_filled_from_the_known_instalments(self):
        conn = card_world()
        ci.record(conn, "bca-1", "2026-10-12", [{"description": "Cicilan toko elektronik", "amount": 152_097, "seq": 28, "total": 36}])
        sid = add_statement(conn, debits=DEBITS + 152_097)
        out = cl.store(conn, sid, cl.parse_text(STATEMENT, date(2026, 10, 12)))
        self.assertEqual(out["status"], "cocok")
        self.assertIn("diisi dari daftar cicilan", out["note"])

    def test_owner_keywords_win_over_the_rules(self):
        conn = card_world()
        conn.execute("INSERT INTO category_keywords VALUES ('toko elektronik', 'sekali:laptop-anak')")
        conn.commit()
        sid = add_statement(conn)
        cl.store(conn, sid, cl.parse_text(STATEMENT, date(2026, 10, 12)))
        self.assertEqual(conn.execute("SELECT category FROM card_lines WHERE description LIKE 'TOKO ELEK%'").fetchone()[0], "sekali:laptop-anak")

    def test_summary_separates_what_can_be_cut_and_flags_big_one_offs(self):
        conn = card_world()
        sid = add_statement(conn)
        cl.store(conn, sid, cl.parse_text(STATEMENT, date(2026, 10, 12)))
        s = cl.summary(conn)
        k = s["by_month"]["2026-10"]["kinds"]
        self.assertEqual(k["belanja"], 337_995 + 109_350 + 93_500 + 2_500_000)
        self.assertEqual(k["langganan"], 99_510)
        self.assertEqual((k["cicilan"], k["bunga"], k["biaya"]), (289_853, 150_928, 125_000 + 90_502))
        text = cl.format_summary(s)
        self.assertIn("pembelian besar sekali: TOKO ELEKTRONIK", text)
        self.assertIn("game-digital Rp 337.995", text)
        html = reports.build(conn, "belanja", TODAY)
        self.assertIn("🛒 Belanja: <b>Rp 3.040.845</b>", html)


class Accuracy(unittest.TestCase):
    def test_an_instalment_without_the_word_cicilan_is_recognised_by_its_exact_amount(self):
        conn = card_world()
        ci.record(conn, "bca-1", "2026-10-12", [{"description": "Tokopedia 378922", "amount": 378_922, "seq": 10, "total": 18}])
        text = STATEMENT + "\n03-OKT 03-OKT MID*Tokopedia 378.922\n04-OKT 04-OKT MID*Tokopedia 378.922"
        sid = add_statement(conn, debits=DEBITS + 2 * 378_922)
        self.assertEqual(cl.store(conn, sid, cl.parse_text(text, date(2026, 10, 12)))["status"], "cocok")
        kinds = sorted(r[0] for r in conn.execute("SELECT kind FROM card_lines WHERE description LIKE 'MID*%'"))
        self.assertEqual(kinds, ["belanja", "cicilan"])                       # one instalment matches one line only

    def test_an_instalment_already_printed_as_one_does_not_claim_a_purchase_of_the_same_amount(self):
        conn = card_world()
        ci.record(conn, "bca-1", "2026-10-12", [{"description": "Shopee 12 bulan", "amount": 476_990, "seq": 11, "total": 12}])
        text = STATEMENT + "\n03-OKT 03-OKT TOKOPEDIA JAKARTA 476.990\n04-OKT 04-OKT INSTALLMENT 11/12 SHOPEE 476.990"
        sid = add_statement(conn, debits=DEBITS + 2 * 476_990)
        self.assertEqual(cl.store(conn, sid, cl.parse_text(text, date(2026, 10, 12)))["status"], "cocok")
        got = dict(conn.execute("SELECT substr(description,1,9), kind FROM card_lines WHERE amount=476990").fetchall())
        self.assertEqual(got, {"TOKOPEDIA": "belanja", "INSTALLME": "cicilan"})

    def test_more_merchants_have_a_category(self):
        conn = card_world()
        cases = {"CATHAY PACIFIC AIRWAYS HKG": "liburan", "PLN PREPAID 5123": "listrik", "SAMSUNG ERF JAKARTA": "elektronik",
                 "ADIDAS GRAND INDONESIA": "pakaian-perawatan", "POP MART PIK": "hobi", "CEMARA JAYA BAN": "otomotif",
                 "SPBU 34-12345": "transport", "HERO SUPERMARKET": "belanja-harian", "ALP*OTHERRETAIL": "belanja-online",
                 "AMAZON WEB SERVICES": "langganan", "SOTO KUDUS BLOK M": "makan"}
        for desc, want in cases.items():
            self.assertEqual(cl.categorize(conn, desc), want, desc)

    def test_a_credit_from_m_bca_is_a_payment_not_a_refund(self):
        self.assertEqual(cl.classify("M-BCA ID", -500_000), "pembayaran")

    def test_a_purchase_credited_back_is_neither_spending_nor_refund(self):
        conn = card_world()
        text = STATEMENT + "\n02-OKT 02-OKT SAMSUNG ERF JAKARTA 6.800.000\n10-OKT 10-OKT SAMSUNG ERF JAKARTA 6.800.000 CR"
        sid = add_statement(conn)                                             # the purchase and its credit cancel out
        self.assertEqual(cl.store(conn, sid, cl.parse_text(text, date(2026, 10, 12)))["status"], "cocok")
        d = cl.summary(conn)["by_month"]["2026-10"]
        self.assertEqual(d["kinds"]["belanja"], 337_995 + 109_350 + 93_500 + 2_500_000)
        self.assertNotIn("refund", d["kinds"])
        self.assertEqual(d["cancelled"], 6_800_000)
        self.assertNotIn("SAMSUNG", " ".join(x[0] for x in d["big"]))
        self.assertIn("dibatalkan/dikonversi ke cicilan", cl.format_summary(cl.summary(conn)))


class Recovery(unittest.TestCase):
    """Real layouts that hid an amount: the statement totals let the code recover it, but only when it is unambiguous."""

    def test_foreign_purchase_with_its_dates_on_the_next_line(self):
        text = "11/08/2026 12/08/2026 COWAY-IPG JAKARTA IDN 2,280,000\nANTHROPIC* CLAUDE SUB ANTHROPIC.COMUSA 364,119\n12/08/2026 13/08/2026\nUSD 20.000 @Rp. 18205.995"
        lines = cl.parse_text(text, date(2026, 8, 22))
        self.assertEqual([(x["description"][:9], x["amount"], x["txn_date"]) for x in lines],
                         [("COWAY-IPG", 2_280_000, "2026-08-11"), ("ANTHROPIC", 364_119, "2026-08-12")])

    def test_summary_rows_without_dates_are_never_lines(self):
        text = "4201-94XX-XXXX-5855 NAMA S U B T O T AL 166,335\n12/08/2026 13/08/2026\nTOTAL PAYMENTS 445,077 CR\n12/08/2026 13/08/2026"
        self.assertEqual(cl.parse_text(text, date(2026, 8, 22)), [])

    def test_one_masked_amount_is_recovered_when_its_visible_digits_agree(self):
        conn = card_world()
        sid = add_statement(conn, debits=DEBITS + 223_514)
        lines = cl.parse_text(STATEMENT + "\n13-OKT 13-OKT Telkomsel [[NUM:****8223]],514.00", date(2026, 10, 12))
        out = cl.store(conn, sid, lines)
        self.assertEqual(out["status"], "cocok")
        self.assertIn("tersamar dipulihkan", out["note"])
        self.assertEqual(conn.execute("SELECT amount FROM card_lines WHERE description LIKE 'Telkomsel%'").fetchone()[0], 223_514)

    def test_a_masked_amount_that_does_not_fit_is_left_as_a_mismatch(self):
        conn = card_world()
        sid = add_statement(conn, debits=DEBITS + 223_999)                                   # digits disagree with ",514"
        out = cl.store(conn, sid, cl.parse_text(STATEMENT + "\n13-OKT 13-OKT Telkomsel [[NUM:****8223]],514.00", date(2026, 10, 12)))
        self.assertEqual(out["status"], "selisih")

    def test_payments_shown_only_as_a_summary_come_from_the_statement(self):
        conn = card_world()
        sid = add_statement(conn, paid=445_077)
        no_payment_line = [x for x in cl.parse_text(STATEMENT, date(2026, 10, 12)) if x["amount"] > 0]
        out = cl.store(conn, sid, no_payment_line)
        self.assertEqual(out["status"], "cocok")
        self.assertEqual(conn.execute("SELECT amount, kind FROM card_lines WHERE description LIKE 'Pembayaran (dari%'").fetchone()[:], (-445_077, "pembayaran"))


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class ThroughTheTools(unittest.TestCase):
    def test_recording_a_statement_reads_its_lines_without_the_model(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "bca.txt"), "w") as f:
                f.write(STATEMENT + "\n")
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                             today=lambda: TODAY, ingest_dir=d, passwords_path=None)
            call = lambda n, a=None: json.loads(json.dumps(asyncio.run(app.state.mcp.call_tool(n, a or {})), default=str))  # noqa: E731
            call("upsert_card", {"alias": "bca-1", "bank": "BCA", "last4": "1111", "statement_day": 12, "due_day": 28, "credit_limit": 10_000_000})
            h = json.dumps(call("ingest_statement", {"file_ref": "bca.txt"})).split("file_hash=")[1][:64]
            prev, paid = 9_050_165, 727_869
            out = json.dumps(call("record_statement", {"card_alias": "bca-1", "file_hash": h, "statement_date": "2026-10-12", "due_date": "2026-10-28",
                                                        "previous_balance": prev, "payments": paid, "charges": DEBITS - 241_430, "fees": 241_430,
                                                        "total_due": prev - paid + DEBITS, "minimum_due": 100_000}))
            self.assertIn("baris", out)
            self.assertRegex(out, r"lines.{0,8}10")
            self.assertIn("cocok", out)
            self.assertIn("game-digital", json.dumps(call("belanja_kartu", {})))


if __name__ == "__main__":
    unittest.main()
