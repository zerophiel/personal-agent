import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import cuti_fetch as cf  # noqa: E402
from vault_tools import tools  # noqa: E402

CAL = {f"2026-{m:02d}-{d:02d}": {"holiday": True, "summary": ["x"]} for m, d in
       [(1, 1), (1, 16), (2, 17), (3, 19), (3, 20), (3, 23), (3, 24), (5, 14), (5, 15), (5, 27), (5, 28), (12, 24), (12, 25)]}
CAL["2026-03-21"] = {"holiday": True, "summary": ["Idul Fitri"]}        # Saturday
CAL["2026-06-02"] = {"holiday": False, "summary": ["bukan libur"]}
ICS = ("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20261224\r\nSUMMARY:Cuti Bersama Natal\r\nEND:VEVENT\r\n"
       "BEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20260216\r\nSUMMARY:Cuti Bersama Imlek\r\nEND:VEVENT\r\n"
       "BEGIN:VEVENT\r\nDTSTART;VALUE=DATE:20260101\r\nSUMMARY:Tahun Baru\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")


class Parse(unittest.TestCase):
    def test_github_only_flagged_days_of_year(self):
        got = cf.parse_github(json.dumps({**CAL, "2027-01-01": {"holiday": True}}), 2026)
        self.assertIn(date(2026, 5, 28), got)
        self.assertNotIn(date(2026, 6, 2), got)
        self.assertTrue(all(d.year == 2026 for d in got))

    def test_ics_only_cuti_bersama(self):
        self.assertEqual(cf.parse_ics_cuti(ICS, 2026), {date(2026, 12, 24), date(2026, 2, 16)})

    def test_candidate_drops_weekends_and_ignores_garbage(self):
        cand = cf.candidate_days(json.dumps({**CAL, "not-a-date": {"holiday": True}}), ICS, 2026)
        self.assertNotIn(date(2026, 3, 21), cand)  # Saturday
        self.assertIn(date(2026, 2, 16), cand)     # from ICS, absent from github dict


class Decide(unittest.TestCase):
    def base(self):
        return cf.candidate_days(json.dumps(CAL), ICS, 2026)

    def test_first_baseline_applies(self):
        self.assertEqual(cf.decide(set(), self.base())[0], "apply")

    def test_no_change(self):
        c = self.base()
        self.assertEqual(cf.decide(set(c), c)[0], "none")

    def test_small_change_applies_large_change_needs_review(self):
        c = self.base()
        self.assertEqual(cf.decide(c - {date(2026, 12, 24)}, c)[0], "apply")
        far = {date(2026, 7, d) for d in range(1, 8)}
        self.assertEqual(cf.decide(far | c, c)[0], "review")

    def test_implausible_counts_rejected(self):
        self.assertEqual(cf.decide({date(2026, 1, 1)}, set())[0], "reject")
        self.assertEqual(cf.decide(set(), {date(2026, 1, 1)})[0], "reject")


class Override(unittest.TestCase):
    def test_override_wins_per_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cuti.json")
            with open(path, "w") as f:
                json.dump({"2026": ["2026-07-01"], "_source": "t"}, f)
            os.environ["CUTI_OVERRIDE"] = path
            try:
                h = tools.id_holidays(2026)
                self.assertIn(date(2026, 7, 1), h)
                self.assertNotIn(date(2026, 3, 20), h)  # bundled 2026 list replaced by override
                self.assertIn(date(2026, 3, 19), h)     # python-holidays national still applies
            finally:
                del os.environ["CUTI_OVERRIDE"]

    def test_merge_file_roundtrip(self):
        out = cf.merge_file({"2026": ["2026-01-01"], "_source": "old"}, 2027, {date(2027, 1, 1)}, "n")
        self.assertEqual(out["2026"], ["2026-01-01"])
        self.assertEqual(out["2027"], ["2027-01-01"])
        self.assertEqual(out["_source"], "n")


if __name__ == "__main__":
    unittest.main()
