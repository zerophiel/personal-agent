"""scripts/finish-merge.sh, the owner's last step of the merge, on a real repository with a real worktree."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SCRIPT = os.path.join(ROOT, "scripts", "finish-merge.sh")
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
       "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


class Base(unittest.TestCase):
    """A main folder with the worktree merged into it, as it stands after the owner's git pull."""

    def setUp(self):
        self.top = tempfile.mkdtemp(prefix="finish-merge-")
        self.addCleanup(shutil.rmtree, self.top, True)
        self.main = os.path.join(self.top, "personal-agent")
        self.old = os.path.join(self.main, ".claude", "worktrees", "m1-skeleton")
        os.mkdir(self.main)
        self.git("init", "-q", "-b", "main")
        self.write(self.main, ".gitignore", "/private/\n.claude/*\ngraphify-out/*\n!graphify-out/graph.json\n")
        self.commit(self.main, "empty")
        self.git("worktree", "add", "-q", "-b", "work", self.old)
        self.write(self.old, "docs/REBUILD.md", "# jalan\n")
        self.write(self.old, "Makefile", "deploy:\n\trsync --exclude /private/ ./ x:y/\n")
        self.write(self.old, "graphify-out/graph.json", "lama\n")
        os.makedirs(os.path.join(self.old, "scripts"))
        shutil.copy(SCRIPT, os.path.join(self.old, "scripts", "finish-merge.sh"))
        self.commit(self.old, "the work")
        self.write(self.old, "graphify-out/cache/chunk.json", "cache")
        self.write(self.old, "graphify-out/.graphify_build_state.json", "{}")
        self.git("merge", "-q", "--no-ff", "-m", "merge", "work")
        self.write(self.main, "private/vps/MIRROR.json", "{}")

    def git(self, *args, where=None):
        return subprocess.run(["git", *args], cwd=where or self.main, env=ENV, check=True, capture_output=True, text=True).stdout

    def write(self, where, name, text):
        path = os.path.join(where, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def commit(self, where, message):
        self.git("add", "-A", where=where)
        self.git("commit", "-q", "-m", message, where=where)

    def run_it(self, where=None):
        return subprocess.run(["bash", os.path.join(where or self.main, "scripts", "finish-merge.sh")], env=ENV, capture_output=True,
                              text=True, timeout=60)

    def in_main(self, name):
        return os.path.join(self.main, name)

    def assert_stopped(self, why, where=None):
        done = self.run_it(where)
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("tidak ada yang dihapus", done.stderr)
        self.assertIn(why, done.stderr)
        self.assertTrue(os.path.isfile(os.path.join(self.old, "docs", "REBUILD.md")), "the worktree must stay")
        self.assertFalse(os.path.exists(self.in_main("graphify-out/cache")), "nothing is moved before every check has passed")


class Finish(Base):
    def test_it_keeps_the_caches_and_removes_the_worktree(self):
        done = self.run_it()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("selesai", done.stdout)
        self.assertFalse(os.path.exists(self.old))
        self.assertTrue(os.path.isfile(self.in_main("graphify-out/cache/chunk.json")))
        self.assertFalse(os.path.exists(self.in_main("graphify-out/.graphify_build_state.json")))
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_the_committed_graph_stays_as_main_has_it(self):
        self.write(self.main, "graphify-out/graph.json", "baru\n")
        self.commit(self.main, "newer graph on main")
        self.assertEqual(self.run_it().returncode, 0)
        with open(self.in_main("graphify-out/graph.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "baru\n")

    def test_running_it_again_is_fine(self):
        self.assertEqual(self.run_it().returncode, 0)
        done = self.run_it()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("selesai", done.stdout)

    def test_a_worktree_the_session_already_removed_is_fine(self):
        shutil.rmtree(self.old)
        done = self.run_it()
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_it_never_touches_the_copy(self):
        self.write(self.main, "private/vps/data/ledger.db", "isi")
        self.assertEqual(self.run_it().returncode, 0)
        self.assertTrue(os.path.isfile(self.in_main("private/vps/data/ledger.db")))


class Stops(Base):
    def test_from_inside_the_worktree(self):
        self.assert_stopped("bukan di worktree", where=self.old)

    def test_on_another_branch(self):
        self.git("checkout", "-q", "-b", "lain")
        self.assert_stopped("cabang main")

    def test_without_the_rebuild_doc(self):
        self.git("rm", "-q", "docs/REBUILD.md")
        self.git("commit", "-q", "-m", "gone")
        self.assert_stopped("docs/REBUILD.md")

    def test_when_a_deploy_would_send_private(self):
        self.write(self.main, "Makefile", "deploy:\n\trsync ./ x:y/\n")
        self.commit(self.main, "no exclude")
        self.assert_stopped("Makefile")

    def test_when_git_would_track_private(self):
        self.write(self.main, ".gitignore", ".claude/*\ngraphify-out/*\n!graphify-out/graph.json\n")
        self.git("add", ".gitignore")
        self.git("commit", "-q", "-m", "no ignore")
        self.assert_stopped("tidak mengabaikan private/")

    def test_without_a_copy(self):
        os.unlink(self.in_main("private/vps/MIRROR.json"))
        self.assert_stopped("make mirror")

    def test_with_uncommitted_changes_here(self):
        self.write(self.main, "catatan.md", "belum")
        self.assert_stopped("folder ini punya perubahan")

    def test_with_a_private_folder_in_the_worktree(self):
        self.write(self.old, "private/vps/MIRROR.json", "{}")
        self.assert_stopped("di dalam worktree")

    def test_with_uncommitted_work_in_the_worktree(self):
        self.write(self.old, "catatan.md", "belum")
        self.assert_stopped("worktree punya perubahan")

    def test_with_commits_main_lacks(self):
        self.write(self.old, "catatan.md", "sudah")
        self.commit(self.old, "after the merge")
        self.assert_stopped("worktree punya commit")


if __name__ == "__main__":
    unittest.main()
