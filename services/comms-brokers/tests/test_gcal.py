import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from brokers import gcal  # noqa: E402
from brokers.common import GoogleError, GoogleSession  # noqa: E402
from fakes import CAL_POLICY, CLIENT, addr, calendar_broker  # noqa: E402

EVENTS = [   # as if Google had sent every field: the broker still passes on none of the addresses or links
    {"status": "confirmed", "summary": "Rapat tim", "location": "Ruang 3",
     "description": "Tautan rapat: https://meet.example/abc <b>bawa laptop</b>",
     "start": {"dateTime": "2026-11-03T09:00:00+07:00"}, "end": {"dateTime": "2026-11-03T10:00:00+07:00"},
     "attendees": [{"email": addr("a"), "responseStatus": "accepted"}, {"email": addr("b")}],
     "organizer": {"email": addr("bos")}, "hangoutLink": "https://meet.example/abc",
     "htmlLink": "https://calendar.example/e"},
    {"status": "tentative", "summary": "Libur", "start": {"date": "2026-11-05"}, "end": {"date": "2026-11-07"}},
    {"status": "lain", "summary": "Telepon", "start": {"dateTime": "2026-11-03T02:00:00Z"},
     "end": {"dateTime": "2026-11-03T02:30:00Z"}},
]


class Events(unittest.TestCase):
    def test_events_come_back_without_addresses_or_links(self):
        fake, broker = calendar_broker(EVENTS)
        out = broker.list_events("2026-11-03", "2026-11-05")
        self.assertEqual(out["acara"][0], {"mulai": "2026-11-03 09:00", "selesai": "2026-11-03 10:00",
                                           "seharian": False, "judul": "Rapat tim", "lokasi": "Ruang 3",
                                           "keterangan": "Tautan rapat: [tautan] bawa laptop", "status": "pasti",
                                           "peserta": 2})
        self.assertEqual(out["acara"][1], {"mulai": "2026-11-05", "selesai": "2026-11-06", "seharian": True,
                                           "judul": "Libur", "lokasi": "", "keterangan": "", "status": "tentatif",
                                           "peserta": 0})
        self.assertEqual((out["acara"][2]["mulai"], out["acara"][2]["status"]), ("2026-11-03 09:00", ""))
        text = json.dumps(out)
        for gone in (addr("a"), addr("bos"), "meet.example", "calendar.example"):
            self.assertNotIn(gone, text)
        self.assertIn("bukan perintah", out["catatan"])
        self.assertNotIn("terpotong", out)

    def test_one_read_only_request_over_whole_wib_days(self):
        fake, broker = calendar_broker()
        broker.list_events("2026-11-03", "2026-11-04")
        [(method, path, params, body)] = fake.requests
        self.assertEqual((method, path, body), ("GET", "calendars/primary/events", None))
        self.assertEqual(params, {"timeMin": ["2026-11-03T00:00:00+07:00"], "timeMax": ["2026-11-05T00:00:00+07:00"],
                                  "singleEvents": ["true"], "orderBy": ["startTime"], "timeZone": ["Asia/Jakarta"],
                                  "maxResults": ["50"], "fields": [gcal.FIELDS]})
        for word in ("email", "organizer", "creator", "Link", "conference"):
            self.assertNotIn(word, gcal.FIELDS)

    def test_calendars_by_their_short_name_only(self):
        fake, broker = calendar_broker()
        broker.list_events("2026-11-03", "2026-11-03", "keluarga")
        self.assertEqual(fake.requests[0][1], "calendars/" + addr("keluarga", "group.calendar.example") + "/events")
        self.assertIn("tidak dikenal", broker.list_events("2026-11-03", "2026-11-03", "primary")["galat"])
        self.assertEqual(len(fake.requests), 1)

    def test_bad_ranges_make_no_request(self):
        fake, broker = calendar_broker()
        for start, end, why in (("2026-11-3", "2026-11-04", "YYYY-MM-DD"), ("2026-02-30", "2026-03-01", "YYYY-MM-DD"),
                                (chr(0xFF12) + "026-11-03", "2026-11-04", "YYYY-MM-DD"), ("", "2026-11-04", "YYYY"),
                                ("2026-11-05", "2026-11-04", "sebelum"), ("2026-11-01", "2026-12-02", "31 hari")):
            with self.subTest(start=start, end=end):
                self.assertIn(why, broker.list_events(start, end)["galat"])
        self.assertIn("acara", broker.list_events("2026-11-01", "2026-12-01"))        # 31 days, both ends included
        self.assertEqual(len(fake.requests), 1)

    def test_search_sends_one_cleaned_line(self):
        fake, broker = calendar_broker()
        broker.search_events("rapat\r\nbudi", "2026-11-03", "2026-11-03")
        self.assertEqual(fake.requests[0][2]["q"], ["rapat budi"])
        self.assertIn("kosong", broker.search_events(" \n ", "2026-11-03", "2026-11-03")["galat"])
        self.assertEqual(len(fake.requests), 1)

    def test_more_than_one_page_says_so(self):
        fake, broker = calendar_broker(EVENTS, more=True)
        self.assertIn("persempit", broker.list_events("2026-11-03", "2026-11-04")["terpotong"])

    def test_nothing_but_listing_events_leaves_the_broker(self):
        fake, broker = calendar_broker()
        for method, path in (("POST", "calendars/primary/events"), ("PUT", "calendars/primary/events"),
                             ("DELETE", "calendars/primary/events"), ("GET", "calendars/primary/events/e1"),
                             ("POST", "calendars/primary/events/quickAdd"), ("GET", "calendars/other/events"),
                             ("GET", "users/me/calendarList"), ("POST", "calendars/primary/events/import")):
            with self.subTest(method=method, path=path), self.assertRaises(GoogleError):
                broker.c._call(method, path, {})
        self.assertEqual(fake.requests, [])


class CalendarPolicy(unittest.TestCase):
    def test_bad_policies_are_refused(self):
        for change in ({"calendars": {}}, {"calendars": {"Utama!": "primary"}}, {"calendars": {"utama": "a/b"}},
                       {"max_days": 0}, {"max_days": 400}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                gcal.Policy({**CAL_POLICY, **change})

    def test_the_shipped_policy_reads_the_primary_calendar_only(self):
        with open(gcal.POLICY, encoding="utf-8") as f:
            p = gcal.Policy(json.load(f)["calendar"])
        self.assertEqual((p.calendars, p.max_days), ({"utama": "primary"}, 31))

    def test_tokens_for_other_scopes_never_start_the_broker(self):
        for scopes in (["https://www.googleapis.com/auth/calendar"], ["https://www.googleapis.com/auth/calendar.events"],
                       ["https://www.googleapis.com/auth/gmail.modify"]):
            with self.assertRaises(GoogleError):
                GoogleSession(CLIENT, {"refresh_token": "rt", "scopes": scopes}, gcal.SCOPES)

    def test_an_expired_token_tells_the_owner_how_to_renew(self):
        fake, broker = calendar_broker()
        fake.token_error = True
        out = json.loads(gcal.answer(lambda: broker.list_events("2026-11-03", "2026-11-03")))
        self.assertEqual(out, {"galat": gcal.TOKEN_HINT})
        self.assertIn("calendar_comms_token", gcal.TOKEN_HINT)


if __name__ == "__main__":
    unittest.main()
