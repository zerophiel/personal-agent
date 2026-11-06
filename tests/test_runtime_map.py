import hashlib
import importlib.util
import itertools
import os
import re
import tempfile
import unittest
from unittest import mock

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


class LocalTree(unittest.TestCase):
    def test_the_plaintext_copy_is_never_walked(self):
        # local_tree() hashes every file and render_drift() writes names into the tracked docs/runtime
        with tempfile.TemporaryDirectory() as root:
            for rel in ("compose/a.yml", "private/vps/secrets/restic.env", "private/.new/data/x"):
                os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
                with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
                    f.write("x")
            with mock.patch.object(rm, "ROOT", root):
                self.assertEqual(list(rm.local_tree()), ["compose/a.yml"])


class Infra(unittest.TestCase):
    def test_the_host_config_in_a_subfolder_is_on_the_map(self):
        # make capture puts it in host/etc/; an open() of the folder itself used to crash the whole collector
        with tempfile.TemporaryDirectory() as root:
            for rel in ("Makefile", ".gitignore", "config/stack.env", "config/squid/a.conf", "host/pa-x.timer",
                        "host/etc/docker/daemon.json", "services/s/Dockerfile"):
                os.makedirs(os.path.dirname(os.path.join(root, rel)) or root, exist_ok=True)
                with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
                    f.write("x\n")
            with mock.patch.object(rm, "ROOT", root):
                text = rm.render_infra()
        for rel in ("config/squid/a.conf", "host/pa-x.timer", "host/etc/docker/daemon.json", "services/s/Dockerfile"):
            self.assertIn(f"## {rel}\n", text)


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

    def test_units_compare_with_host_and_the_applier_folder(self):
        def unit(name, digest):
            return {"name": name, "keys": [("Description", name)], "sha256": digest}
        h = {"collected_at": "now", "units": [unit("pa-ingest.timer", "a" * 64), unit("pa-applier.path", "b" * 64),
                                              unit("pa-applier.timer", "c" * 64), unit("pa-other.timer", "d" * 64)]}
        local = {"host/pa-ingest.timer": "a" * 64, "services/applier/systemd/pa-applier.path": "b" * 64,
                 "services/applier/systemd/pa-applier.timer": "e" * 64}
        rows = {line.split("|")[1].strip(): line.split("|")[5].strip()
                for line in rm.render_timers(h, local).splitlines() if line.startswith("| pa-")}
        self.assertEqual(rows, {"pa-ingest.timer": "same", "pa-applier.path": "same", "pa-applier.timer": "DIFFERENT",
                                "pa-other.timer": "not in repo"})

    def test_numbers_in_text_are_still_masked(self):
        _, h = digest_with_digit_run()
        got = rm.scrub(f"rekening 1234567890123, kartu 4111 1111 1111 1111, hash {h}")
        self.assertNotRegex(got, r"\d{9,}")
        self.assertIn("[nomor]", got)
        self.assertEqual(rm.scrub("1" * 64), "[angka]")   # digits only: never mistaken for a digest
        self.assertEqual(rm.scrub("9" * 40), "[angka]")


if __name__ == "__main__":
    unittest.main()
