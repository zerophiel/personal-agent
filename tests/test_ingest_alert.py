import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

ROOT = os.path.join(os.path.dirname(__file__), "..")
_p = os.path.join(ROOT, "scripts", "ingest-alert.py")
_s = importlib.util.spec_from_file_location("ingest_alert", _p)
ia = importlib.util.module_from_spec(_s)
_s.loader.exec_module(ia)

START = 1_793_660_400   # the failed run's start, 3 Nov 2026 06:00 WIB


def ev(ts, type_="error", **kw):
    return json.dumps({"ts": ts, "type": type_, **kw}, sort_keys=True)


class Reasons(unittest.TestCase):
    def test_only_the_failed_runs_errors(self):
        lines = [ev(START - 86400, reason="token_expired"),   # the run of the day before
                 ev(START + 5, "new_statement", bank="dbs", file_ref="ab12.pdf"),
                 ev(START + 6, "rejected", reason="sender_not_allowlisted"),
                 ev(START + 9, reason="gmail_error"), ev(START + 12, reason="gmail_error"), "not json", "[1]", ""]
        self.assertEqual(ia.reasons_since(lines, START), ["gmail_error"])

    def test_an_event_written_in_the_start_second_counts(self):
        self.assertEqual(ia.reasons_since([ev(START, reason="token_expired")], START), ["token_expired"])

    def test_events_without_an_int_time_are_skipped(self):
        lines = [json.dumps({"type": "error", "reason": "token_expired"}), ev("soon", reason="token_expired")]
        self.assertEqual(ia.reasons_since(lines, START), [])


class Message(unittest.TestCase):
    def test_rejected_token_names_the_renewal(self):
        msg = ia.message(["token_expired"])
        self.assertTrue(msg.startswith("Ingest statement Gmail barusan gagal."))
        self.assertIn("Google menolak token Gmail", msg)
        self.assertIn("bash scripts/gmail-renew.sh", msg)

    def test_the_most_urgent_reason_comes_first(self):
        msg = ia.message(["gmail_error", "token_expired"])
        self.assertLess(msg.index("gmail-renew.sh"), msg.index("dicoba lagi besok"))

    def test_a_missing_label_names_it(self):
        self.assertIn('"Keuangan/Kartu Kredit" tidak ditemukan', ia.message(["label_not_found"]))

    def test_no_error_event_points_to_the_journal(self):
        msg = ia.message([])
        self.assertIn("tidak tercatat", msg)
        self.assertIn("journalctl -u pa-ingest", msg)

    def test_an_unknown_reason_is_named_only_when_plain(self):
        self.assertIn("Penyebab tercatat: quota_exceeded.", ia.message(["quota_exceeded"]))
        msg = ia.message(["<a href='http://x'>klik</a>"])
        self.assertNotIn("http", msg)
        self.assertNotIn("Penyebab tercatat", msg)
        self.assertIn("journalctl -u pa-ingest", msg)


class RunStarted(unittest.TestCase):
    def systemctl(self, stdout):
        return mock.patch.object(ia.subprocess, "run", return_value=mock.Mock(stdout=stdout))

    def test_reads_systemds_unix_time(self):
        with self.systemctl(f"@{START}\n") as run:
            self.assertEqual(ia.run_started(), START)
        self.assertIn("--timestamp=unix", run.call_args.args[0])

    def test_none_when_systemd_gives_no_time(self):
        for out in ("", "@0", "n/a", "Tue 2026-11-03 06:00:00 WIB"):
            with self.systemctl(out):
                self.assertIsNone(ia.run_started(), out)

    def test_none_without_systemctl(self):
        with mock.patch.object(ia.subprocess, "run", side_effect=FileNotFoundError):
            self.assertIsNone(ia.run_started())


class Main(unittest.TestCase):
    def run_main(self, lines, argv=(), started=START, path=None):
        sent = []
        with tempfile.TemporaryDirectory() as d:
            if path is None:
                path = os.path.join(d, "_events.jsonl")
                with open(path, "w") as f:
                    f.write("\n".join(lines) + "\n")
            with mock.patch.object(ia, "EVENTS_FILE", path), mock.patch.object(ia, "run_started", return_value=started), \
                    mock.patch.object(ia, "notify", side_effect=sent.append), redirect_stdout(io.StringIO()) as out:
                self.assertEqual(ia.main(list(argv)), 0)
        return sent, out.getvalue()

    def test_sends_one_message(self):
        sent, _ = self.run_main([ev(START + 3, reason="token_expired")])
        self.assertEqual(len(sent), 1)
        self.assertIn("gmail-renew.sh", sent[0])

    def test_dry_run_prints_and_sends_nothing(self):
        sent, out = self.run_main([ev(START + 3, reason="token_expired")], ["--dry-run"])
        self.assertEqual(sent, [])
        self.assertIn("gmail-renew.sh", out)

    def test_without_a_start_time_only_the_last_hours_count(self):
        now = START + 600
        with mock.patch.object(ia.time, "time", return_value=now):
            sent, _ = self.run_main([ev(now - 86400, reason="label_not_found"), ev(now - 60, reason="token_expired")],
                                    started=None)
        self.assertIn("gmail-renew.sh", sent[0])
        self.assertNotIn("Keuangan/Kartu Kredit", sent[0])

    def test_an_unreadable_events_file_still_alerts(self):
        sent, _ = self.run_main([], path="/nonexistent/_events.jsonl")
        self.assertIn("journalctl -u pa-ingest", sent[0])


class Notify(unittest.TestCase):
    def test_the_bot_token_is_never_printed(self):
        url_error = OSError("https://api.telegram.org/bot123:SECRET/sendMessage")
        with mock.patch.object(ia, "open", mock.mock_open(read_data="123:SECRET\n"), create=True), \
                mock.patch.object(ia.urllib.request, "urlopen", side_effect=url_error), \
                mock.patch.dict(os.environ, {"MY_TELEGRAM_ID": "1"}), redirect_stdout(io.StringIO()) as out:
            ia.notify("Ingest statement Gmail barusan gagal.")
        self.assertNotIn("SECRET", out.getvalue())
        self.assertIn("notify failed", out.getvalue())


class Units(unittest.TestCase):
    def unit(self, name):
        with open(os.path.join(ROOT, "host", name)) as f:
            return f.read()

    def test_a_failed_ingest_starts_the_alert(self):
        self.assertIn("OnFailure=pa-ingest-alert.service", self.unit("pa-ingest.service").split("[Service]")[0])

    def test_the_alert_runs_only_on_failure(self):
        # install-timers.sh enables only timer and path units: no [Install] and no timer, so nothing else starts it
        unit = self.unit("pa-ingest-alert.service")
        self.assertNotIn("[Install]", unit)
        self.assertFalse([f for f in os.listdir(os.path.join(ROOT, "host")) if f.startswith("pa-ingest-alert.")
                          and not f.endswith(".service")])
        self.assertIn("EnvironmentFile=/opt/personal-agent/config/stack.env", unit)   # MY_TELEGRAM_ID
        self.assertIn("ExecStart=/usr/bin/python3 /opt/personal-agent/scripts/ingest-alert.py\n", unit)
        self.assertTrue(os.access(_p, os.X_OK))


if __name__ == "__main__":
    unittest.main()
