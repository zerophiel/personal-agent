"""ops/privacy: the filter on a session's output, the scan before a commit, and that neither holds a copy of the owner's name."""
import importlib.util
import os
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True   # the tools are loaded from their own folders: no caches left there
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
MASK =os.path.join(ROOT, "ops", "privacy", "mask.py")
SCAN = os.path.join(ROOT, "ops", "privacy", "diff_scan.py")
TOKEN_VALUE = "12345" + "6789" + ":" + "AbC1" * 9
KEY_VALUE = "sk-" + "ant-" + "abcDEF123" * 3
EMAIL = "pemilik" + "@" + "contoh.example"
ADDRESS = ".".join("8" * 4)
CARD = "4" * 16
GROUPED = " ".join(["4111"] * 4)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


collect = load("ops/runtime-map/collect.py", "collect_for_privacy")


def run(script, stdin, *args):
    return subprocess.run([sys.executable, "-I", script, *args], input=stdin.encode() if isinstance(stdin, str) else stdin,
                          capture_output=True, timeout=60)


def masked(text, *args):
    done = run(MASK, text, *args)
    assert done.returncode == 0, done.stderr
    return done.stdout.decode()


def diff(*lines, start=1, path="docs/x.md"):
    return "\n".join([f"+++ b/{path}", f"@@ -0,0 +{start},{len(lines)} @@", *(f"+{line}" for line in lines)]) + "\n"


class Mask(unittest.TestCase):
    def test_what_must_not_be_shown_is_masked(self):
        for value in (TOKEN_VALUE, KEY_VALUE, EMAIL, ADDRESS, CARD, GROUPED):
            self.assertNotIn(value, masked(f"sebelum {value} sesudah\n"))

    def test_a_token_inside_a_url_goes_too(self):
        out = masked(f"https://api.telegram.org/bot{TOKEN_VALUE}/getMe\n")
        self.assertEqual(out, "https://api.telegram.org/bot[token]/getMe\n")

    def test_ordinary_output_stays_as_it_is(self):
        for line in ("ledger: ok (integrity ok, 31 tables, 4260 rows)\n", "Ran 992 tests in 65.1s\n", "containers: ok (9 of 9 up)\n"):
            self.assertEqual(masked(line), line)

    def test_a_line_is_cut_at_the_width(self):
        self.assertEqual(masked("kata " * 100 + "\n").rstrip("\n"), ("kata " * 100)[:240])
        self.assertEqual(masked("kata " * 100 + "\n", "20").rstrip("\n"), ("kata " * 100)[:20])

    def test_bytes_that_are_not_text_do_not_stop_it(self):
        self.assertIn("biasa", masked(b"\xff\xfe biasa\n"))


class Scan(unittest.TestCase):
    def test_a_clean_diff_passes(self):
        done = run(SCAN, diff("kalimat biasa", "4260 baris"))
        self.assertEqual(done.returncode, 0)
        self.assertEqual(done.stdout.decode(), "scan: no hits in added lines\n")

    def test_each_kind_is_reported_with_file_and_line_and_is_masked(self):
        for value, kind in ((CARD, "digits>=9"), (GROUPED, "grouped number"), (EMAIL, "email"), (TOKEN_VALUE, "token"),
                            ("ghp_" + "aB1" * 10, "github or slack token")):
            done = run(SCAN, diff("biasa", f"nilai {value}", start=3))
            out = done.stdout.decode()
            self.assertEqual(done.returncode, 1, kind)
            self.assertIn(f"docs/x.md [{kind}] x1\n", out)
            self.assertIn("    4: nilai ", out)
            self.assertNotIn(value, out)

    def test_only_added_lines_count(self):
        text = "\n".join(["--- a/docs/x.md", "+++ b/docs/x.md", "@@ -1,1 +1,1 @@", f"-nilai {CARD}", "+biasa"]) + "\n"
        self.assertEqual(run(SCAN, text).returncode, 0)

    def test_the_owner_name_check_is_the_pattern_of_the_runtime_map(self):
        scan = load("ops/privacy/diff_scan.py", "diff_scan_for_test")
        self.assertEqual(scan.CHECKS["owner name"].pattern, collect.OWNER.pattern)
        self.assertEqual(scan.CHECKS["token"].pattern, collect.TOKEN.pattern)


class OneCopy(unittest.TestCase):
    def test_no_tool_holds_a_copy_of_the_owner_name(self):
        for path in (MASK, SCAN, __file__):
            with open(path, encoding="utf-8") as f:
                self.assertIsNone(collect.OWNER.search(f.read()), path)

    def test_no_tracked_file_points_at_a_session_folder(self):
        """A session's temporary folder goes when the session goes: nothing here may depend on it."""
        files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
        self.assertGreater(len(files), 100)
        marker = ".claude/" + "jobs/"
        hits = []
        for path in files:
            if path.startswith(("graphify-out/", "docs/runtime/")):
                continue
            try:
                with open(os.path.join(ROOT, path), encoding="utf-8") as f:
                    if marker in f.read():
                        hits.append(path)
            except (OSError, UnicodeDecodeError):
                continue
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
