"""What a local checkout holds besides the code never reaches the VPS or an image: make deploy's rsync and the build
contexts of the images built from the repo."""
import os
import re
import shlex
import unittest

try:
    import yaml
except ImportError:  # the vault-tools venv may lack PyYAML; the system python3 used by `make test` has it
    yaml = None

ROOT = os.path.join(os.path.dirname(__file__), "..")


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


def deploy_rsync():
    """The argument list of the rsync line in the Makefile's deploy target."""
    body = read("Makefile").split("\ndeploy:\n", 1)[1].split("\n\n", 1)[0]
    (line,) = [x for x in body.splitlines() if x.strip().startswith("rsync ")]
    return shlex.split(line.strip())


class Rsync(unittest.TestCase):
    def test_caches_secrets_and_the_map_stay_here(self):
        args = deploy_rsync()
        excluded = {args[i + 1] for i, a in enumerate(args) if a == "--exclude"}
        self.assertLessEqual({".git", ".claude", "secrets/*.dec*", "graphify-out", "CLAUDE.md", "__pycache__"},
                             excluded)

    def test_delete_never_reaches_what_is_excluded(self):
        # --delete-excluded would remove the VPS's own copies of what is left out here
        args = deploy_rsync()
        self.assertIn("--delete", args)
        self.assertNotIn("--delete-excluded", args)


@unittest.skipUnless(yaml, "needs PyYAML")
class BuildContexts(unittest.TestCase):
    def test_an_image_that_copies_a_folder_ignores_python_caches(self):
        services = yaml.safe_load(read("compose/docker-compose.yml"))["services"]
        checked = []
        for name, svc in services.items():
            build = svc.get("build")
            if not build:
                continue
            context = os.path.normpath(os.path.join(ROOT, "compose", build if isinstance(build, str) else build["context"]))
            dockerfile = "Dockerfile" if isinstance(build, str) else build.get("dockerfile", "Dockerfile")
            with open(os.path.join(context, dockerfile), encoding="utf-8") as f:
                copies = [shlex.split(x)[1:-1] for x in f.read().splitlines() if re.match(r"COPY\s", x)]
            folders = [s for c in copies for s in c if not s.startswith("--") and os.path.isdir(os.path.join(context, s))]
            if not folders:
                continue
            checked.append(name)
            ignore = os.path.join(context, ".dockerignore")
            self.assertTrue(os.path.isfile(ignore), f"{name} copies {folders} without a .dockerignore")
            with open(ignore, encoding="utf-8") as f:
                patterns = {x.strip() for x in f if x.strip() and not x.startswith("#")}
            self.assertLessEqual({"**/__pycache__", "**/*.pyc"}, patterns, name)
            for folder in folders:   # the ignore file leaves out the caches, never what the image copies
                self.assertFalse(patterns & {"*", "**", folder, folder.rstrip("/")}, name)
        self.assertEqual(sorted(checked), ["ingest-gmail", "vault-tools"])


if __name__ == "__main__":
    unittest.main()
