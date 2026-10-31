import hashlib
import importlib.util
import itertools
import os
import re
import unittest

_p = os.path.join(os.path.dirname(__file__), "..", "ops", "runtime-map", "collect.py")
_s = importlib.util.spec_from_file_location("collect", _p)
rm = importlib.util.module_from_spec(_s)
_s.loader.exec_module(rm)


def digest_with_digit_run(start=0):
    """A real sha256 whose hex holds a run of 9+ digits: the shape scrub() used to break (about 1 hash in 4)."""
    for i in itertools.count(start):
        h = hashlib.sha256(str(i).encode()).hexdigest()
        if re.search(r"\d{9,}", h):
            return i, h


class Scrub(unittest.TestCase):
    def test_whole_value_digests_survive(self):
        _, h = digest_with_digit_run()
        self.assertEqual(rm.scrub(h), h)
        self.assertEqual(rm.scrub(h[:40]), h[:40])
        self.assertEqual(rm.deep_scrub({"deployed_tree": {"a.py": h}}), {"deployed_tree": {"a.py": h}})

    def test_drift_compares_hashes_that_have_digit_runs(self):
        i, h1 = digest_with_digit_run()
        _, h2 = digest_with_digit_run(i + 1)
        local = {"services/vault-tools/vault_tools/tools.py": h1, "docs/PROGRESS.md": h2}
        vps = rm.deep_scrub({"deployed_tree": dict(local)})   # what run_probe() hands the renderer
        out = rm.render_drift(vps, {}, local)
        self.assertIn("2 identical", out)
        self.assertIn("runtime files that differ: none", out)

    def test_numbers_in_text_are_still_masked(self):
        _, h = digest_with_digit_run()
        got = rm.scrub(f"rekening 1234567890123, kartu 4111 1111 1111 1111, hash {h}")
        self.assertNotRegex(got, r"\d{9,}")
        self.assertIn("[nomor]", got)
        self.assertEqual(rm.scrub("1" * 64), "[angka]")   # digits only: never mistaken for a digest
        self.assertEqual(rm.scrub("9" * 40), "[angka]")


if __name__ == "__main__":
    unittest.main()
