import importlib.util
import json
import os
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

_path = os.path.join(os.path.dirname(__file__), "..", "plugins", "cardguard", "__init__.py")
_spec = importlib.util.spec_from_file_location("cardguard", _path)
cg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cg)
OWNER = "99"


def ev(text, chat_type="dm", mid=1, user_id=OWNER):
    return SimpleNamespace(text=text, message_id=mid,
                           source=SimpleNamespace(chat_type=chat_type, chat_id=99, user_id=user_id))


class Fake:
    """Stands in for vault-tools and the Telegram Bot API."""
    def __init__(self):
        self.posts, self.bot_calls, self.status, self.body = [], [], 200, None
        self.store = {}

    def post(self, path, body, timeout=8):
        self.posts.append((path, body))
        if self.body is not None:
            return self.status, self.body
        if path == "/internal/store_payee":
            alias = self.store.setdefault(body["number"], body["alias"])
            return 200, json.dumps({"ok": True, "alias": alias}).encode()
        return 200, "2026-11-05 dbs-1111\n  Rp 300.000\n  `4111111111111111`".encode()

    def bot(self, method, **params):
        self.bot_calls.append((method, params))
        return {"message_id": 777} if method == "sendMessage" else True


class CardGuard(unittest.TestCase):
    def setUp(self):
        self.f = Fake()
        cg._post, cg._bot = self.f.post, self.f.bot
        self.tmp = tempfile.TemporaryDirectory()
        cg.TTL_FILE = os.path.join(self.tmp.name, "ttl", "rincian.jsonl")
        env = mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": OWNER})
        env.start()
        self.addCleanup(env.stop)

    def tearDown(self):
        self.tmp.cleanup()

    def methods(self):
        threading.Event().wait(0.1)  # background delete thread
        return [m for m, _ in self.f.bot_calls]

    def test_report_commands_are_answered_by_code_and_never_reach_the_model(self):
        self.f.body = "Tagihan kartu terbuka\n- BCA ...9706: LUNAS".encode()
        for cmd in ("/rencana", "/tagihan", "/CICILAN", "/anggaran@danoevault_agent", "/peta", "/kondisi", "/data", "/bantuan"):
            self.f.posts.clear(); self.f.bot_calls.clear()
            self.assertEqual(cg.on_inbound(ev(cmd)), {"action": "skip"}, cmd)
            self.assertEqual(self.f.posts[0][0], "/internal/report")
            self.assertEqual(self.f.posts[0][1]["name"], cmd.lstrip("/").split("@")[0].lower())
            self.assertEqual([m for m, _ in self.f.bot_calls], ["sendMessage"])
        self.f.bot_calls.clear()
        self.assertIsNone(cg.on_inbound(ev("/rencana besok")))                      # not an exact command: a normal message
        self.assertIsNone(cg.on_inbound(ev("/model")))
        self.f.posts.clear()
        self.assertEqual(cg.on_inbound(ev("/rencana", chat_type="group")), {"action": "skip"})   # private chat only:
        self.assertEqual((self.f.posts, self.f.bot_calls), ([], []))                              # dropped, unanswered

    def test_reports_go_out_as_html_split_on_blank_lines_under_the_telegram_limit(self):
        paras = [f"<b>Bagian {i}</b>\n" + ("baris panjang " * 60) for i in range(12)]          # about 900 characters each
        self.f.body = "\n\n".join(paras).encode()
        cg.on_inbound(ev("/data"))
        sent = [p for m, p in self.f.bot_calls if m == "sendMessage"]
        self.assertGreater(len(sent), 1)
        for p in sent:
            self.assertLessEqual(len(p["text"]), 3800)
            self.assertEqual(p["parse_mode"], "HTML")
            self.assertEqual(p["text"].count("<b>"), p["text"].count("</b>"))                     # never cut inside a tag
        self.assertEqual("\n\n".join(p["text"] for p in sent), "\n\n".join(paras))

    def test_a_single_huge_paragraph_is_hard_cut_as_a_last_resort(self):
        self.f.body = ("x" * 9000).encode()
        cg.on_inbound(ev("/data"))
        self.assertEqual([len(p["text"]) for m, p in self.f.bot_calls if m == "sendMessage"], [3800, 3800, 1400])

    def test_if_telegram_rejects_the_html_the_same_text_is_sent_plain(self):
        calls = []

        def bot(method, **params):
            calls.append((method, params))
            return None if params.get("parse_mode") == "HTML" else {"message_id": 1}
        cg._bot = bot
        self.f.body = "<b>Judul</b>\nisi &amp; lagi".encode()
        cg.on_inbound(ev("/tagihan"))
        sent = [p for m, p in calls if m == "sendMessage"]
        self.assertEqual(len(sent), 2)
        self.assertEqual(sent[1]["text"], "Judul\nisi & lagi")
        self.assertNotIn("parse_mode", sent[1])

    def test_a_failing_report_tells_the_owner_and_still_skips(self):
        self.f.status, self.f.body = 500, b"boom"
        self.assertEqual(cg.on_inbound(ev("/tagihan")), {"action": "skip"})
        self.assertIn("Gagal mengambil laporan", self.f.bot_calls[-1][1]["text"])

    def test_menu_is_the_owners_list_in_both_scopes_and_valid_for_telegram(self):
        self.assertEqual(cg.push_menu(), 2)
        calls = [p for m, p in self.f.bot_calls if m == "setMyCommands"]
        self.assertEqual(sorted(json.loads(p["scope"])["type"] for p in calls), ["all_private_chats", "default"])
        cmds = json.loads(calls[0]["commands"])
        names = [c["command"] for c in cmds]
        self.assertEqual(len(names), len(set(names)))
        for c in cmds:
            self.assertRegex(c["command"], r"^[a-z0-9_]{1,32}$")
            self.assertTrue(1 <= len(c["description"]) <= 256)
        for must in ("bantuan", "rencana", "tagihan", "rincian", "rekening", "va", "new", "stop"):
            self.assertIn(must, names)
        self.assertNotIn("model", names)                                              # stock commands are not shown

    def test_the_menu_is_restored_only_when_hermes_has_overwritten_it(self):
        shown = {"default": [{"command": "help", "description": "stock"}], "all_private_chats": [{"command": "help", "description": "stock"}]}
        calls = []

        def bot(method, **params):
            calls.append(method)
            scope = json.loads(params["scope"])["type"]
            if method == "getMyCommands":
                return shown[scope]
            shown[scope] = json.loads(params["commands"])
            return True
        cg._bot = bot
        self.assertTrue(cg.ensure_menu())                          # stock menu on screen: restore ours
        self.assertEqual(calls.count("setMyCommands"), 2)
        calls.clear()
        self.assertFalse(cg.ensure_menu())                         # already ours: no write at all
        self.assertEqual(calls.count("setMyCommands"), 0)
        shown["default"] = [{"command": "help", "description": "stock"}]                  # Hermes reconnects and overwrites
        self.assertTrue(cg.ensure_menu())

    def test_a_failing_bot_api_never_raises_from_the_menu_check(self):
        cg._bot = lambda method, **p: None
        self.assertTrue(cg.ensure_menu() in (True, False))

    def test_rewrites_to_alias_token_and_deletes_raw(self):
        for raw in ("4111 1111 1111 1111", "4111111111111111", "4111-1111-1111-1111"):
            out = cg.on_inbound(ev(f"kartu {raw} ok"))
            self.assertEqual(out, {"action": "rewrite", "text": "kartu [[CARD:num-1111]] ok"})
        self.assertIn("deleteMessage", self.methods())
        sent = json.dumps(self.f.posts)
        self.assertIn("raw_text", sent)  # raw text goes only to vault-tools (same zone)

    def test_two_numbers_two_aliases(self):
        self.f.store["5500000000000004"] = "num-0004"
        out = cg.on_inbound(ev("a 4111111111111111 b 5500 0000 0000 0004"))
        self.assertEqual(out["text"], "a [[CARD:num-1111]] b [[CARD:num-0004]]")

    def test_plain_text_and_non_luhn_untouched(self):
        self.assertIsNone(cg.on_inbound(ev("gaji Rp 10000000 masuk")))
        self.assertIsNone(cg.on_inbound(ev("ref 4111111111111112")))
        self.assertIsNone(cg.on_inbound(ev(None)))
        self.assertEqual(self.f.posts, [])

    def test_cvv_rejected_message_deleted_owner_told(self):
        self.f.status, self.f.body = 422, b'{"ok": false, "error": "cvv_or_expiry_rejected"}'
        self.assertEqual(cg.on_inbound(ev("4111111111111111 cvv 123")), {"action": "skip"})
        ms = self.methods()
        self.assertIn("deleteMessage", ms)
        self.assertIn("sendMessage", ms)

    def test_vault_down_fails_closed(self):
        def boom(*a, **k):
            raise ConnectionError("down")
        cg._post = boom
        self.assertEqual(cg.on_inbound(ev("4111111111111111")), {"action": "skip"})

    def test_vault_error_fails_closed_and_deletes(self):
        self.f.status, self.f.body = 500, b"{}"
        self.assertEqual(cg.on_inbound(ev("4111111111111111")), {"action": "skip"})
        self.assertIn("deleteMessage", self.methods())

    def test_group_chat_with_number_dropped_without_storing(self):
        self.assertEqual(cg.on_inbound(ev("4111111111111111", chat_type="group")), {"action": "skip"})
        self.assertEqual(self.f.posts, [])

    def test_rincian_sent_directly_recorded_and_skipped(self):
        out = cg.on_inbound(ev(" /Rincian "))
        self.assertEqual(out, {"action": "skip"})
        self.assertEqual(self.f.posts[0][0], "/internal/rincian")
        method, params = self.f.bot_calls[0]
        self.assertEqual((method, params["chat_id"], params["parse_mode"]), ("sendMessage", 99, "Markdown"))
        with open(cg.TTL_FILE) as f:
            rec = json.loads(f.readline())
        self.assertEqual((rec["c"], rec["m"]), (99, 777))

    def test_rekening_command_stored_deleted_skipped_model_never_sees_it(self):
        self.f.body = json.dumps({"ok": True, "alias": "bca-rek"}).encode()
        out = cg.on_inbound(ev("/rekening bca-rek BCA 1234 5678 90"))
        self.assertEqual(out, {"action": "skip"})
        path, body = self.f.posts[0]
        self.assertEqual(path, "/internal/store_payee")
        self.assertEqual((body["alias"], body["kind"], body["bank"], body["number"]), ("bca-rek", "account", "BCA", "1234567890"))
        ms = self.methods()
        self.assertIn("deleteMessage", ms)
        said = [p["text"] for m, p in self.f.bot_calls if m == "sendMessage"][0]
        self.assertIn("bca-rek ****7890", said)
        self.assertNotIn("1234567890", said)

    def test_va_command_uses_va_kind_and_botname_suffix(self):
        self.f.body = json.dumps({"ok": True, "alias": "sekolah-va", "duplicate": True}).encode()
        cg.on_inbound(ev("/va@danoevault_agent sekolah-va Mandiri 8808123456789012"))
        self.assertEqual(self.f.posts[0][1]["kind"], "va")
        said = [p["text"] for m, p in self.f.bot_calls if m == "sendMessage"][0]
        self.assertIn("sudah tersimpan sebelumnya", said)

    def test_malformed_payee_command_still_deleted_and_never_stored(self):
        for bad in ("/rekening", "/rekening bca-rek 1234567890", "/va x BCA 12", "/rekening bca-rek BCA 12345678901234567890123456789"):
            self.f.posts.clear()
            self.assertEqual(cg.on_inbound(ev(bad)), {"action": "skip"}, bad)
            self.assertEqual(self.f.posts, [], bad)
        self.assertIn("deleteMessage", self.methods())

    def test_payee_command_outside_private_chat_dropped_and_never_stored(self):
        out = cg.on_inbound(ev("/rekening bca-rek BCA 1234567890", chat_type="group"))
        self.assertEqual(out, {"action": "skip"})
        self.assertEqual(self.f.posts, [])

    def test_anyone_else_gets_no_command_answered_and_no_number_stored(self):
        for text in ("/rencana", "/rincian", "/usulan", "/rekening bca-rek BCA 1234567890", "/va x BCA 8808123456789012",
                     "4111111111111111", "kartu 4111 1111 1111 1111"):
            self.f.posts.clear(); self.f.bot_calls.clear()
            self.assertEqual(cg.on_inbound(ev(text, user_id="5")), {"action": "skip"}, text)
            self.assertEqual((self.f.posts, self.methods()), ([], []), text)    # no store, no reply, no delete
        self.assertIsNone(cg.on_inbound(ev("halo, saldo saya berapa?", user_id="5")))   # Hermes' own check decides
        self.assertEqual(self.f.posts, [])

    def test_without_an_allowlist_or_a_user_id_nobody_is_the_owner(self):
        self.assertEqual(cg.on_inbound(ev("/rincian", user_id=None)), {"action": "skip"})
        with mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": ""}):
            self.assertEqual(cg.on_inbound(ev("/rincian")), {"action": "skip"})
            self.assertEqual(cg.on_inbound(ev("4111111111111111")), {"action": "skip"})
        self.assertEqual((self.f.posts, self.methods()), ([], []))

    def test_an_empty_allowlist_is_logged_at_boot(self):
        hooks = []
        with mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": ""}), mock.patch.object(cg, "_started", True), \
                self.assertLogs("cardguard", "ERROR") as logs:
            cg.register(SimpleNamespace(register_hook=lambda name, fn: hooks.append(name)))
        self.assertIn("TELEGRAM_ALLOWED_USERS is empty", logs.output[0])
        self.assertIn("pre_gateway_dispatch", hooks)

    def test_the_owner_check_takes_the_id_as_hermes_writes_it(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": " 7, 99 "}):
            self.assertTrue(cg._is_owner(ev("x")))
            self.assertTrue(cg._is_owner(ev("x", user_id=99)))       # an int id compares as its text
            self.assertFalse(cg._is_owner(ev("x", user_id="990")))
            self.assertFalse(cg._is_owner(ev("x", chat_type="group")))

    def test_payee_command_vault_failure_tells_owner_and_deletes(self):
        self.f.status, self.f.body = 500, b"{}"
        self.assertEqual(cg.on_inbound(ev("/rekening bca-rek BCA 1234567890")), {"action": "skip"})
        said = [p["text"] for m, p in self.f.bot_calls if m == "sendMessage"][0]
        self.assertIn("Gagal", said)
        self.assertIn("deleteMessage", self.methods())

    def test_rincian_failure_skips_and_tells_owner(self):
        self.f.status, self.f.body = 500, b""
        self.assertEqual(cg.on_inbound(ev("/rincian")), {"action": "skip"})
        self.assertEqual([m for m, _ in self.f.bot_calls], ["sendMessage"])

    def test_ttl_sweep_deletes_only_expired(self):
        os.makedirs(os.path.dirname(cg.TTL_FILE))
        with open(cg.TTL_FILE, "w") as f:
            f.write(json.dumps({"c": 1, "m": 10, "exp": 100}) + "\n" + json.dumps({"c": 1, "m": 11, "exp": 900}) + "\n")
        gone = []
        with self.assertLogs("cardguard", "INFO") as logs:
            self.assertEqual(cg.sweep_ttl(now=500, deleter=lambda c, m: gone.append(m) or True), 1)
        self.assertEqual(gone, [10])
        self.assertIn("Telegram deleted 1 of 1 expired message(s), 0 kept", logs.output[0])
        with open(cg.TTL_FILE) as f:
            self.assertEqual([json.loads(line)["m"] for line in f], [11])

    def test_a_refused_delete_is_retried_while_telegram_allows_it(self):
        os.makedirs(os.path.dirname(cg.TTL_FILE))
        with open(cg.TTL_FILE, "w") as f:
            f.write(json.dumps({"c": 1, "m": 10, "exp": 100}) + "\n")
        self.assertEqual(cg.sweep_ttl(now=200, deleter=lambda c, m: None), 0)          # refused: kept
        with open(cg.TTL_FILE) as f:
            self.assertEqual([json.loads(line)["m"] for line in f], [10])
        self.assertEqual(cg.sweep_ttl(now=300, deleter=lambda c, m: True), 1)          # next sweep: deleted
        with open(cg.TTL_FILE, "w") as f:
            f.write(json.dumps({"c": 1, "m": 12, "exp": 100}) + "\n")
        self.assertEqual(cg.sweep_ttl(now=100 + cg.RETRY_SECONDS, deleter=lambda c, m: None), 1)   # past 48 h: dropped
        with open(cg.TTL_FILE) as f:
            self.assertEqual(f.read(), "")

    def test_error_inside_hook_fails_closed(self):
        class Boom:
            message_id = 9
            source = SimpleNamespace(chat_type="dm", chat_id=1)
            @property
            def text(self):
                raise RuntimeError("boom")
        self.assertEqual(cg.on_inbound(Boom()), {"action": "skip"})


class NumberGuard(unittest.TestCase):
    TOOL = "Pot hutang-teman: setoran gajian ini Rp 0; perkiraan terkumpul Rp 121.437.703, KURANG Rp 13.562.297; dbs: 1903656"

    def setUp(self):
        cg._seen.clear()

    def test_amount_forms(self):
        self.assertEqual(cg.amounts("Rp 1.234.567"), [(1_234_567, 0)])
        self.assertEqual(cg.amounts("Rp 13,56 jt dan 500 rb", money_only=True), [(13_560_000, 5_000), (500_000, 500)])
        self.assertEqual(cg.amounts("bunga 1,75% per bulan, 15 gajian, …5915", money_only=True), [])

    def test_numbers_from_the_tools_and_the_owner_pass_and_made_up_ones_are_flagged(self):
        cg.on_pre_llm(session_id="s1", user_message="sisa uang harian 4.994.157", conversation_history=[])
        cg.on_tool_result(session_id="s1", result=self.TOOL)
        ok = "Pot kurang **Rp 13.562.297** (sekitar Rp 13,56 jt); DBS Rp 1.903.656; sisa harianmu Rp 4.994.157."
        self.assertIsNone(cg.on_llm_output(response_text=ok, session_id="s1"))
        out = cg.on_llm_output(response_text=ok + " Totalnya Rp 15.465.953.", session_id="s1")   # the model's own sum
        self.assertTrue(out.startswith(ok))
        self.assertIn("⚠️ Cek angka: Rp 15.465.953", out)

    def test_amounts_in_a_photo_description_pass(self):
        # the gateway describes a photo with amounts written the English way (31 Oct: a receipt total read as 174,075)
        cg.on_pre_llm(session_id="p", user_message="[image] Receipt total: 174,075; cash 200,000.00", conversation_history=[])
        self.assertIsNone(cg.on_llm_output(response_text="Struk Rp 174.075, dibayar tunai Rp 200.000.", session_id="p"))
        self.assertIn("Cek angka: Rp 175.075", cg.on_llm_output(response_text="Struk Rp 175.075.", session_id="p"))

    def test_a_new_session_knows_nothing_until_the_tools_speak(self):
        self.assertIn("Cek angka", cg.on_llm_output(response_text="Tagihan Rp 8.993.569.", session_id="fresh"))
        cg.on_pre_llm(session_id="fresh", conversation_history=[{"role": "tool", "content": "sisa Rp 8.993.569"}])
        self.assertIsNone(cg.on_llm_output(response_text="Tagihan Rp 8.993.569.", session_id="fresh"))

    def test_the_guard_never_breaks_a_turn(self):
        self.assertIsNone(cg.on_llm_output(response_text=None, session_id=None))
        self.assertIsNone(cg.on_pre_llm(session_id="x", conversation_history=[object()]))


if __name__ == "__main__":
    unittest.main()
