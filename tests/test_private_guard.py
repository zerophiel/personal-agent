"""private/ is the plaintext copy of the VPS data and secrets (make mirror). Everything that walks or copies the repo
root must leave it alone: git, the deploy rsyncs, the project map and its hook, the runtime map, the assistant."""
import importlib.util
import json
import os
import re
import shlex
import subprocess
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
IN_GIT = os.path.exists(os.path.join(ROOT, ".git"))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def load(name, *parts):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, *parts))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def shell_files():
    """The Makefile and every shell script, tracked or not; caches and the local folders are not code."""
    skip = {".git", ".claude", "graphify-out", "__pycache__", "private"}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip]
        for f in filenames:
            if f == "Makefile" or f.endswith(".sh"):
                yield os.path.join(dirpath, f)


def rsync_commands(path):
    """Each rsync command line in a file, with backslash continuations joined."""
    with open(path, encoding="utf-8") as f:
        text = f.read().replace("\\\n", " ")
    return [ln.strip() for ln in text.splitlines() if re.match(r"\s*rsync\s", ln)]


def copies_the_whole_repo(command):
    """Its source is the repo root (./ or .), not a subfolder or a remote path."""
    return any(a in ("./", ".") for a in shlex.split(command, comments=True))


class Git(unittest.TestCase):
    def test_ignored(self):
        self.assertIn("/private/", read(".gitignore").splitlines())

    @unittest.skipUnless(IN_GIT, "needs a git checkout")
    def test_git_agrees_and_tracks_nothing_there(self):
        for path in ("private/", "private/vps/secrets/restic.env", "private/.new/data/x"):
            done = subprocess.run(["git", "-C", ROOT, "check-ignore", "-q", path])
            self.assertEqual(done.returncode, 0, path)
        tracked = subprocess.run(["git", "-C", ROOT, "ls-files", "private"], capture_output=True, text=True, check=True)
        self.assertEqual(tracked.stdout, "")


class Rsync(unittest.TestCase):
    def test_every_copy_of_the_whole_repo_leaves_it_out(self):
        checked = []
        for path in shell_files():
            for command in rsync_commands(path):
                if not copies_the_whole_repo(command):
                    continue
                checked.append(os.path.relpath(path, ROOT))
                args = shlex.split(command, comments=True)
                excluded = {args[i + 1] for i, a in enumerate(args) if a == "--exclude"}
                self.assertIn("/private/", excluded, path)
        # make deploy and the four old data-fix scripts; a parser that finds nothing must not pass
        self.assertGreaterEqual(len(checked), 5, checked)
        self.assertIn("Makefile", checked)


class ProjectMap(unittest.TestCase):
    def test_graphify_ignores_it(self):
        self.assertIn("private/", read(".graphifyignore").splitlines())

    def test_the_hook_never_names_a_file_there(self):
        hook = load("graph_first_guard", "ops", "graphify", "graph_first.py")
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "graphify-out"))
            with open(os.path.join(root, "graphify-out", "manifest.json"), "w", encoding="utf-8") as f:
                json.dump({"a.md": {"mtime": 0, "semantic_hash": "x"}, "b.py": {"mtime": 0, "ast_hash": "x"}}, f)
            for rel in ("private/vps/data/ingest/rahasia.md", "private/.new/x.py", "baru.md"):
                os.makedirs(os.path.dirname(os.path.join(root, rel)) or root, exist_ok=True)
                with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
                    f.write("x")
            found = hook.behind(root)
        self.assertIn("baru.md (new)", found)   # the walk ran
        self.assertFalse([x for x in found if "private" in x or "rahasia" in x], found)


class Assistant(unittest.TestCase):
    def test_settings_deny_reads_and_edits_in_both_checkouts(self):
        deny = json.loads(read(".claude/settings.json"))["permissions"]["deny"]
        for rule in ("Read(~/personal-agent/private/**)", "Edit(~/personal-agent/private/**)",
                     "Read(/private/**)", "Edit(/private/**)"):
            self.assertIn(rule, deny)

    def test_the_settings_keep_the_map_hook(self):
        hooks = json.loads(read(".claude/settings.json"))["hooks"]["UserPromptSubmit"]
        self.assertIn("graph_first.py", json.dumps(hooks))

    @unittest.skipUnless(os.path.isfile(os.path.join(ROOT, "CLAUDE.md")), "CLAUDE.md is not deployed")
    def test_the_rule_is_in_the_instructions(self):
        self.assertIn("## private/: never read or list it", read("CLAUDE.md"))


if __name__ == "__main__":
    unittest.main()
