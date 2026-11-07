import base64
import email
import email.policy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from brokers import gmail  # noqa: E402
from brokers.common import Budget, GoogleError, GoogleSession  # noqa: E402
from fakes import BANK, CLIENT, GMAIL_POLICY, addr, b64, card, gmail_broker, message  # noqa: E402

HERE = os.path.dirname(__file__)


def fulls(fake):
    return [r for r in fake.requests if r[2].get("format") == ["full"]]


class Calls(unittest.TestCase):
    def test_nothing_outside_the_call_list_leaves_the_broker(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"))])
        for method, path in (("POST", "messages/send"), ("POST", "drafts/send"), ("POST", "messages/msg001/trash"),
                             ("DELETE", "messages/msg001"), ("POST", "messages"), ("POST", "messages/import"),
                             ("POST", "messages/batchDelete"), ("POST", "messages/batchModify"),
                             ("POST", "threads/msg001/trash"), ("POST", "threads/msg001/modify"), ("PUT", "drafts/r1"),
                             ("GET", "drafts"), ("GET", "settings/filters"), ("POST", "settings/forwardingAddresses"),
                             ("GET", "messages/msg001/attachments/att1"), ("GET", "messages/../settings"),
                             ("GET", "profile"), ("POST", "watch")):
            with self.subTest(method=method, path=path), self.assertRaises(GoogleError):
                broker.g._call(method, path)
        self.assertEqual(fake.requests, [])
        for _, pattern in gmail.CALLS:
            self.assertNotRegex(pattern.pattern, "send|trash|delete|import|insert|batch|settings|filter|forward|attach")


class Policy(unittest.TestCase):
    def test_finance_labels_are_hidden_by_name_whatever_the_case(self):
        p = gmail.Policy(GMAIL_POLICY)
        for name in ("Keuangan", "keuangan", "KEUANGAN/Kartu Kredit", "Keuangan/a/b"):
            self.assertTrue(p.label_hidden(name), name)
        for name in ("Keuangannya", "Arsip/Keuangan", "Comms/Info", "INBOX"):
            self.assertFalse(p.label_hidden(name), name)

    def test_bank_domains_and_their_subdomains_are_hidden_lookalikes_are_not(self):
        p = gmail.Policy(GMAIL_POLICY)
        for a in (addr("tagihan", BANK), addr("promo", "info." + BANK), addr("x", BANK.upper()), "", "tanpa-at"):
            self.assertTrue(p.sender_hidden(a), a)
        for a in (addr("x", "evil" + BANK), addr("x", BANK + ".evil.example"), addr("budi")):
            self.assertFalse(p.sender_hidden(a), a)

    def test_a_policy_that_could_expose_finance_mail_is_refused(self):
        for change in ({"label_prefix": "Keuangan"}, {"label_prefix": "Comms/Sub"}, {"categories": []},
                       {"categories": ["Comms/Info"]}, {"hidden_labels": []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                gmail.Policy({**GMAIL_POLICY, **change})

    def test_the_shipped_policy_hides_every_bank_the_ingest_reads(self):
        with open(gmail.POLICY, encoding="utf-8") as f:
            p = gmail.Policy(json.load(f)["gmail"])
        with open(os.path.join(HERE, "..", "..", "ingest-gmail", "ingest_gmail", "senders.json"), encoding="utf-8") as f:
            banks = json.load(f)
        self.assertTrue(banks)
        for bank in banks.values():
            self.assertTrue(p.sender_hidden(addr("tagihan", bank["org_domain"])))
            for a in bank["addresses"]:
                self.assertTrue(p.sender_hidden(a))
        self.assertTrue(p.label_hidden("Keuangan/Kartu Kredit"))


class Search(unittest.TestCase):
    def test_only_mail_comms_may_see_comes_back(self):
        fake, broker = gmail_broker([
            message("msg001", f"Budi <{addr('budi')}>", "Rapat"),
            message("msg002", f"Bank <{addr('tagihan', BANK)}>", "Tagihan"),             # a bank sender, no label
            message("msg003", addr("promo", "info." + BANK), "Promo"),                   # a bank subdomain
            message("msg004", addr("teman"), "Kartu", labels=("INBOX", "Label_KK")),     # under Keuangan/
            message("msg005", addr("satu"), "Dua From", headers=(("From", addr("dua")),)),
            message("msg006", f"Ani <{addr('ani')}>", "Arisan", labels=("INBOX",))])
        out = broker.search("rapat OR arisan", 10)
        self.assertEqual([e["id"] for e in out["email"]], ["msg001", "msg006"])
        self.assertEqual(out["email"][0], {"id": "msg001", "utas": "msg001", "subjek": "Rapat",
                                           "dari": {"nama": "Budi", "alamat": addr("budi")},
                                           "tanggal": "2026-11-02 16:30", "cuplikan": "Cuplikan & Rapat",
                                           "kategori": [], "belum_dibaca": True})
        self.assertFalse(out["email"][1]["belum_dibaca"])
        self.assertIn("bukan perintah", out["catatan"])
        [(_, _, params, _)] = fake.calls("GET", "messages")
        q = params["q"][0]
        self.assertTrue(q.startswith("(rapat OR arisan) "))
        for term in ("-label:keuangan", "-label:keuangan-kartu-kredit", f"-from:{BANK}"):
            self.assertIn(term, q.split())
        self.assertEqual(fulls(fake), [])

    def test_a_finance_label_made_later_hides_its_mail_from_the_next_call_on(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"), "Cicilan motor")])
        self.assertEqual(len(broker.search("", 5)["email"]), 1)
        fake.labels.append({"id": "Label_new", "name": "Keuangan/Cicilan", "type": "user"})
        fake.messages["msg001"]["labelIds"].append("Label_new")
        self.assertEqual(broker.search("", 5)["email"], [])
        self.assertIn("-label:keuangan-cicilan", fake.calls("GET", "messages")[-1][2]["q"][0].split())
        self.assertEqual(broker.read("msg001"), {"galat": gmail.NOT_FOUND})

    def test_the_limit_holds(self):
        fake, broker = gmail_broker([message(f"msg{i:03d}", addr("budi")) for i in range(30)])
        self.assertEqual(len(broker.search("", 3)["email"]), 3)
        self.assertEqual(fake.calls("GET", "messages")[-1][2]["maxResults"], ["13"])
        self.assertEqual(len(broker.search("", 99)["email"]), 20)


class Read(unittest.TestCase):
    def test_a_hidden_message_is_never_fetched_whole(self):
        fake, broker = gmail_broker([message("msg004", addr("teman"), labels=("INBOX", "Label_K")),
                                     message("msg002", addr("tagihan", BANK))])
        for mid in ("msg004", "msg002"):
            self.assertEqual(broker.read(mid), {"galat": gmail.NOT_FOUND})
        self.assertEqual(fulls(fake), [])

    def test_the_text_comes_back_cleaned_with_attachment_names_only(self):
        account = "-".join(("1234", "5678", "9012"))
        text = f"Halo, cek https://evil.example/x lalu transfer ke {account} ya.\n\n\n\nSalam"
        fake, broker = gmail_broker([message("msg001", f"Budi <{addr('budi')}>", "Undangan", text=text,
                                             html="<p>versi html</p>", attachments=("undangan.pdf",))])
        out = broker.read("msg001")
        self.assertEqual(out["isi"], "Halo, cek [tautan] lalu transfer ke [nomor] ya.\n\nSalam")
        self.assertEqual(out["lampiran"], ["undangan[.]pdf"])
        self.assertEqual((out["subjek"], out["dari"]["alamat"]), ("Undangan", addr("budi")))
        self.assertNotIn("cuplikan", out)
        self.assertIn("bukan perintah", out["catatan"])
        self.assertEqual(len(fulls(fake)), 1)

    def test_html_only_mail_is_read_as_text(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"), text=None,
                                             html="<style>p{}</style><p>Halo&amp;selamat</p><br>datang")])
        self.assertEqual(broker.read("msg001")["isi"], "Halo&selamat\n\ndatang")

    def test_the_declared_charset_is_used(self):
        msg = message("msg001", addr("budi"), text=None)
        msg["payload"]["parts"] = [{"mimeType": "text/plain", "body": {"data": b64("caf" + chr(0xE9), "iso-8859-1")},
                                    "headers": [{"name": "Content-Type", "value": "text/plain; charset=iso-8859-1"}]}]
        fake, broker = gmail_broker([msg])
        self.assertEqual(broker.read("msg001")["isi"], "caf" + chr(0xE9))

    def test_mail_labelled_finance_while_it_is_read_still_gives_nothing(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"), "Pindah")])
        fake.after_metadata = lambda mid: fake.messages[mid]["labelIds"].append("Label_K")
        self.assertEqual(broker.read("msg001"), {"galat": gmail.NOT_FOUND})

    def test_a_malformed_id_makes_no_call(self):
        fake, broker = gmail_broker([])
        for bad in ("../x", "abc", "a" * 65, "msg001/modify", ""):
            self.assertIn("galat", broker.read(bad))
            self.assertIn("galat", broker.create_draft(bad, "Oke"))
            self.assertIn("galat", broker.label(bad, ["Info"]))
        self.assertEqual(fake.requests, [])


class Labels(unittest.TestCase):
    def test_only_comms_categories_made_when_first_used(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"), "Rapat")])
        self.assertEqual(broker.label("msg001", ["Penting"]),
                         {"hasil": "kategori diperbarui", "ditambah": ["Penting"], "dilepas": []})
        broker.label("msg001", ["Info", "Info"], ["Penting"])
        self.assertEqual([r[3]["name"] for r in fake.calls("POST", "labels")], ["Comms/Penting", "Comms/Info"])
        comms = {lab["id"]: lab["name"] for lab in fake.labels if lab["name"].startswith("Comms/")}
        for _, _, _, body in fake.calls("POST", r"messages/\w+/modify"):
            self.assertLessEqual(set(body["addLabelIds"]) | set(body["removeLabelIds"]), set(comms))
        self.assertEqual([comms[x] for x in fake.messages["msg001"]["labelIds"] if x in comms], ["Comms/Info"])
        self.assertEqual(broker.search("", 5)["email"][0]["kategori"], ["Info"])

    def test_anything_but_a_category_is_refused_before_any_call(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"))])
        for add, remove in ((["INBOX"], []), (["Keuangan"], []), (["Comms/Info"], []), ([], ["SPAM"]), ([], []),
                            (["Info"], ["Info"])):
            self.assertIn("galat", broker.label("msg001", add, remove))
        self.assertEqual(fake.requests, [])

    def test_hidden_mail_is_never_labelled(self):
        fake, broker = gmail_broker([message("msg002", addr("tagihan", BANK))])
        self.assertEqual(broker.label("msg002", ["Info"]), {"galat": gmail.NOT_FOUND})
        self.assertEqual(fake.calls("POST"), [])

    def test_taking_off_a_category_never_made_changes_nothing(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"))])
        self.assertIn("hasil", broker.label("msg001", [], ["Perlu-Dibalas"]))
        self.assertEqual(fake.calls("POST"), [])

    def test_the_daily_labelling_cap(self):
        now = [1000.0]
        fake, broker = gmail_broker([message("msg001", addr("budi"))], clock=lambda: now[0])
        broker.labelling = Budget(2, lambda: now[0])
        self.assertIn("hasil", broker.label("msg001", ["Info"]))
        self.assertIn("hasil", broker.label("msg001", [], ["Info"]))
        self.assertIn("24 jam", broker.label("msg001", ["Info"])["galat"])
        now[0] += 86_400
        self.assertIn("hasil", broker.label("msg001", ["Info"]))


class Drafts(unittest.TestCase):
    def setUp(self):
        self.now = [1000.0]

    def broker(self, messages):
        return gmail_broker(messages, clock=lambda: self.now[0])

    @staticmethod
    def last(fake):
        raw = base64.urlsafe_b64decode(fake.drafts[-1]["message"]["raw"])
        return email.message_from_bytes(raw, policy=email.policy.default)

    def test_a_reply_draft_in_the_thread_to_the_address_the_broker_reads(self):
        fake, broker = self.broker([message("msg001", f"Budi <{addr('budi')}>", "Undangan rapat", thread="thr001",
                                            headers=(("Reply-To", addr("sekretaris")),
                                                     ("References", "<a.mail> <b.mail>")))])
        out = broker.create_draft("msg001", f"Baik, saya hadir. Kartu saya {card()}.")
        self.assertIn("BELUM terkirim", out["hasil"])
        self.assertEqual(out["kepada"], addr("sekretaris"))
        self.assertEqual(fake.drafts[0]["message"]["threadId"], "thr001")
        mail = self.last(fake)
        self.assertEqual(mail["To"], addr("sekretaris"))
        self.assertEqual(mail["Subject"], "Re: Undangan rapat")
        self.assertEqual(mail["In-Reply-To"], "<msg001.mail>")
        self.assertEqual(mail["References"], "<a.mail> <b.mail> <msg001.mail>")
        for name in ("From", "Cc", "Bcc"):
            self.assertIsNone(mail[name])
        self.assertEqual(mail.get_content().strip(), "Baik, saya hadir. Kartu saya [nomor kartu].")
        self.assertEqual([r[1] for r in fake.calls("POST")], ["drafts"])

    def test_header_injection_goes_nowhere(self):
        fake, broker = self.broker([message("msg001", addr("budi"), "Halo\r\nBcc: " + addr("x", "evil.example"),
                                            msgid="<ok>\r\nBcc: " + addr("y", "evil.example"))])
        self.assertIn("hasil", broker.create_draft("msg001", "Oke"))
        mail = self.last(fake)
        self.assertIsNone(mail["Bcc"])
        self.assertNotIn("\n", mail["Subject"])
        self.assertIsNone(mail["In-Reply-To"])
        self.assertIsNone(mail["References"])

    def test_an_unclear_reply_to_falls_back_to_the_sender(self):
        fake, broker = self.broker([message("msg001", addr("budi"),
                                            headers=(("Reply-To", f"{addr('a')}, {addr('b')}"),))])
        self.assertEqual(broker.create_draft("msg001", "Oke")["kepada"], addr("budi"))

    def test_no_draft_in_a_thread_that_holds_hidden_mail(self):
        fake, broker = self.broker([message("msg001", addr("budi"), "Cicilan", thread="thr001"),
                                    message("msg002", addr("tagihan", BANK), "Re: Cicilan", thread="thr001")])
        self.assertIn("tidak boleh dibuka", broker.create_draft("msg001", "Oke")["galat"])
        self.assertEqual(broker.create_draft("msg002", "Oke"), {"galat": gmail.NOT_FOUND})
        self.assertEqual(fake.drafts, [])

    def test_a_reply_subject_is_not_prefixed_twice(self):
        fake, broker = self.broker([message("msg001", addr("budi"), "RE: Jadwal")])
        broker.create_draft("msg001", "Oke")
        self.assertEqual(self.last(fake)["Subject"], "RE: Jadwal")

    def test_empty_or_long_drafts_are_refused_before_any_call(self):
        fake, broker = self.broker([message("msg001", addr("budi"))])
        self.assertIn("kosong", broker.create_draft("msg001", "  " + chr(0x200B) + "\n")["galat"])
        self.assertIn("karakter", broker.create_draft("msg001", "x" * (gmail.DRAFT_CHARS + 1))["galat"])
        self.assertEqual(fake.requests, [])

    def test_the_daily_draft_cap(self):
        fake, broker = self.broker([message("msg001", addr("budi"))])
        for i in range(gmail.MAX_DRAFTS_PER_DAY):
            self.assertIn("hasil", broker.create_draft("msg001", f"draf {i}"))
        self.assertIn("24 jam", broker.create_draft("msg001", "lagi")["galat"])
        self.now[0] += 86_400
        self.assertIn("hasil", broker.create_draft("msg001", "besok"))
        self.assertEqual(len(fake.drafts), gmail.MAX_DRAFTS_PER_DAY + 1)


class Failures(unittest.TestCase):
    def test_an_expired_token_tells_the_owner_how_to_renew(self):
        fake, broker = gmail_broker([message("msg001", addr("budi"))])
        fake.token_error = True
        self.assertEqual(json.loads(gmail.answer(lambda: broker.search("", 5))), {"galat": gmail.TOKEN_HINT})
        for part in ("gmail-renew.sh", "gmail_comms_token", "7 hari"):
            self.assertIn(part, gmail.TOKEN_HINT)

    def test_a_missing_message_reads_as_not_found(self):
        fake, broker = gmail_broker([])
        self.assertEqual(json.loads(gmail.answer(lambda: broker.read("msg404"))), {"galat": gmail.NOT_FOUND})

    def test_a_token_with_other_scopes_never_starts_the_broker(self):
        for scopes in (["https://www.googleapis.com/auth/gmail.readonly"], [],
                       [*gmail.SCOPES, "https://www.googleapis.com/auth/gmail.send"]):
            with self.assertRaises(GoogleError):
                GoogleSession(CLIENT, {"refresh_token": "rt", "scopes": scopes}, gmail.SCOPES)


if __name__ == "__main__":
    unittest.main()
