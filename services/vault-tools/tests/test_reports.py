import html.parser
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import TODAY, full_world, statement  # noqa: E402

from vault_tools import card_installments as ci  # noqa: E402
from vault_tools import reports  # noqa: E402
from vault_tools import subscriptions as sub  # noqa: E402
from vault_tools import tools  # noqa: E402


def world():
    conn = full_world()
    tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000)
    tools.upsert_card(conn, "cimb-2", "CIMB", "2222", 5, 5, 10_000_000)
    statement(conn, 1, 8_000_000, 800_000)
    statement(conn, 2, 3_000_000, 300_000)
    ci.record(conn, "bca-1", "2026-10-05", [{"description": "TOKOPEDIA", "amount": 1_000_000, "seq": 3, "total": 12}])
    sub.upsert(conn, "spotify", "Spotify", 119_900, "bca-1")
    return conn


class Balanced(html.parser.HTMLParser):
    """Telegram rejects a message with an unbalanced or unsupported tag."""
    ALLOWED = {"b", "i", "code", "pre"}

    def __init__(self):
        super().__init__()
        self.stack, self.bad = [], []

    def handle_starttag(self, tag, attrs):
        (self.stack.append(tag) if tag in self.ALLOWED else self.bad.append(tag))

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            self.bad.append("/" + tag)


def check_html(testcase, text, name):
    p = Balanced()
    p.feed(text)
    testcase.assertEqual((p.bad, p.stack), ([], []), name)


class Reports(unittest.TestCase):
    def test_every_command_renders_valid_telegram_html_in_paragraphs_that_stand_alone(self):
        conn = world()
        for name in reports.NAMES:
            text = reports.build(conn, name, TODAY)
            self.assertTrue(text.strip(), name)
            self.assertLess(len(text), 20000, name)
            check_html(self, text, name)
            for para in text.split("\n\n"):                  # the plugin may cut between paragraphs
                check_html(self, para, f"{name}: {para[:40]}")

    def test_unknown_report_is_refused(self):
        with self.assertRaises(ValueError):
            reports.build(world(), "rincian", TODAY)

    def test_tagihan_is_readable_not_a_dump(self):
        text = reports.build(world(), "tagihan", TODAY)
        self.assertIn("<b>BCA …1111</b>", text)
        self.assertIn("Sisa <b>Rp 8.000.000</b> · minimum Rp 800.000", text)
        self.assertIn("<b>Total sisa: Rp 11.000.000</b>", text)
        self.assertNotIn("bca-1", text)                       # no technical aliases
        self.assertNotIn("2026-11", text)                     # dates read "20 Nov", not ISO
        self.assertIn("\n\n", text)                           # blank lines between cards
        self.assertNotIn("106879418405", text)

    def test_overdue_and_paid_have_their_own_marks(self):
        conn = world()
        self.assertIn("LEWAT", reports.build(conn, "tagihan", date(2026, 12, 1)))
        conn.execute("UPDATE statements SET paid_amount=total_due, paid_at='2026-10-28' WHERE card_id=1")
        conn.commit()
        self.assertIn("✅ <b>BCA …1111</b>\n    Lunas", reports.build(conn, "tagihan", TODAY))

    def test_rencana_groups_by_date_with_friendly_names_and_no_raw_tool_lines(self):
        text = reports.build(world(), "rencana", TODAY)
        self.assertIn("📅 <b>Rencana gajian", text)
        self.assertIn("(hari gajian)", text)
        self.assertIn("• Hutang teman: <b>Rp 9.000.000</b>", text)
        self.assertNotIn("(tagihan kartu - ", text)
        self.assertNotIn("\n> ", text)
        self.assertNotIn("\n! ", text)
        self.assertNotRegex(text, r"\d{4}-\d{2}-\d{2}")       # no ISO dates

    def test_cicilan_lists_installments_and_subscriptions(self):
        text = reports.build(world(), "cicilan", TODAY)
        self.assertIn("TOKOPEDIA 3/12", text)
        self.assertIn("• Spotify (BCA …1111): <b>Rp 119.900</b>/bulan", text)

    def test_special_characters_are_escaped(self):
        conn = world()
        sub.upsert(conn, "evil", "A <b>&</b> B", 1000, "bca-1")
        text = reports.build(conn, "cicilan", TODAY)
        self.assertIn("A &lt;b&gt;&amp;&lt;/b&gt; B", text)
        check_html(self, text, "escaped")

    def test_help_names_every_menu_command(self):
        for cmd in ("/rencana", "/tagihan", "/cicilan", "/anggaran", "/peta", "/kondisi", "/data", "/rincian", "/rekening", "/va", "/new", "/stop"):
            self.assertIn(cmd, reports.HELP)
        self.assertIn("Nomor lengkap tidak pernah saya lihat", reports.HELP)
        check_html(self, reports.HELP, "bantuan")


if __name__ == "__main__":
    unittest.main()
