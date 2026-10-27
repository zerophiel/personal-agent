import os
import subprocess
import tempfile
import time
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "sync-uploads.sh")


class SyncUploads(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "cache")
        self.dst = os.path.join(self.tmp.name, "ingest", "telegram")
        os.makedirs(self.src)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, name, data=b"%PDF-1.4 x", age_days=0, where=None):
        p = os.path.join(where or self.src, name)
        open(p, "wb").write(data)
        t = time.time() - age_days * 86400
        os.utime(p, (t, t))
        return p

    def run_sync(self, **env):
        e = {**os.environ, "SRC": self.src, "DST": self.dst, "OWNER": "", **env}
        r = subprocess.run(["bash", SCRIPT], env=e, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip()

    def listing(self):
        return sorted(os.listdir(self.dst)) if os.path.isdir(self.dst) else []

    def test_copies_new_files_once_with_safe_mode(self):
        self.put("mutasi okt.csv", b"a,b\n1,2\n")
        self.assertIn("copied=1", self.run_sync())
        self.assertEqual(self.listing(), ["mutasi okt.csv"])
        self.assertEqual(oct(os.stat(os.path.join(self.dst, "mutasi okt.csv")).st_mode & 0o777), "0o644")
        self.assertIn("copied=0", self.run_sync())                      # idempotent

    def test_same_name_different_content_is_kept_side_by_side(self):
        self.put("s.pdf", b"%PDF-1.4 one")
        self.run_sync()
        self.put("s.pdf", b"%PDF-1.4 two")
        self.run_sync()
        names = self.listing()
        self.assertEqual(len(names), 2)
        self.assertIn("s.pdf", names)
        self.assertEqual(open(os.path.join(self.dst, "s.pdf"), "rb").read(), b"%PDF-1.4 one")   # never overwritten

    def test_symlinks_subdirs_and_oversized_files_skipped(self):
        os.symlink("/etc/passwd", os.path.join(self.src, "link.pdf"))
        os.makedirs(os.path.join(self.src, "sub"))
        self.put("inner.pdf", where=os.path.join(self.src, "sub"))
        self.put("big.pdf", b"x" * 2000)
        self.put("ok.pdf")
        self.run_sync(MAX_BYTES="1000")
        self.assertEqual(self.listing(), ["ok.pdf"])

    def test_retention_deletes_originals_and_copies_older_than_90_days(self):
        self.put("old.pdf", age_days=100)
        self.put("new.pdf", age_days=1)
        os.makedirs(self.dst)
        self.put("old-copy.pdf", age_days=95, where=self.dst)
        self.run_sync()
        self.assertEqual(sorted(os.listdir(self.src)), ["new.pdf"])
        self.assertEqual(self.listing(), ["new.pdf"])

    def test_missing_source_is_a_noop(self):
        os.rmdir(self.src)
        self.assertEqual(self.run_sync(), "")
        self.assertEqual(self.listing(), [])

    def test_no_temp_files_left_behind(self):
        self.put("a.pdf")
        self.run_sync()
        self.assertFalse([n for n in self.listing() if n.startswith(".tmp")])


if __name__ == "__main__":
    unittest.main()
