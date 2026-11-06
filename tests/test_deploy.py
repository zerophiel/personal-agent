"""What a local checkout holds besides the code never reaches the VPS or an image: make deploy's rsync and the build
contexts of the images built from the repo."""
import os
import re
import shlex
import subprocess
import tempfile
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
        self.assertLessEqual({".git", ".claude", "secrets/*.dec*", "graphify-out", "CLAUDE.md", "__pycache__", "/private/"},
                             excluded)

    def test_delete_never_reaches_what_is_excluded(self):
        # --delete-excluded would remove the VPS's own copies of what is left out here
        args = deploy_rsync()
        self.assertIn("--delete", args)
        self.assertNotIn("--delete-excluded", args)


def steps(target, **extra):
    """The commands make would run for a target, with a test address."""
    variables = [f"{k}={v}" for k, v in {"VPS_HOST": "alamat", "VPS_USER": "pemilik", **extra}.items()]
    done = subprocess.run(["make", "-n", "--no-print-directory", "-C", ROOT, target, *variables], capture_output=True, text=True,
                          timeout=30, check=True)
    return done.stdout.splitlines()


GUARD = "bash scripts/deploy-guard.sh {} pemilik@alamat"


class Targets(unittest.TestCase):
    def test_sync_copies_exactly_what_deploy_copies(self):
        def line(target):
            body = read("Makefile").split(f"\n{target}:\n", 1)[1].split("\n\n", 1)[0]
            (one,) = [x for x in body.splitlines() if x.strip().startswith("rsync ")]
            return one
        self.assertEqual(line("sync"), line("deploy"))

    def test_sync_copies_and_nothing_else_inside_the_guard(self):
        (start, copy, end) = steps("sync")
        self.assertEqual((start, end), (GUARD.format("start"), GUARD.format("end")))
        self.assertTrue(copy.startswith("rsync "))
        self.assertTrue(copy.endswith(" ./ pemilik@alamat:/opt/personal-agent/"))

    def test_up_makes_the_folders_first_and_the_job_image_last_inside_the_guard(self):
        (start, remote, end) = steps("up")
        self.assertEqual((start, end), (GUARD.format("start"), GUARD.format("end")))
        order = [remote.index(x) for x in ("scripts/data-dirs.sh", " up -d --build", "--profile jobs build ingest-gmail")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("install-timers", remote)
        self.assertNotIn("--profile front", remote)

    def test_deploy_stays_what_it_was(self):
        (start, copy, remote, end) = steps("deploy")
        self.assertEqual((start, end), (GUARD.format("start"), GUARD.format("end")))
        self.assertTrue(copy.startswith("rsync "))
        self.assertIn("sudo bash scripts/install-timers.sh && sudo bash scripts/data-dirs.sh && ", remote)
        self.assertTrue(remote.endswith(" up -d --build'"))

    def test_front_starts_only_its_profile(self):
        (remote,) = steps("front")
        self.assertIn("--profile front up -d --build --wait change-proposals front", remote)

    def test_the_envs_of_the_running_zones_are_rendered_and_never_comms(self):
        (remote,) = steps("render-envs")
        self.assertIn("sudo bash scripts/render-vault-env.sh && sudo bash scripts/render-front-env.sh", remote)
        self.assertNotIn("comms", remote)

    def test_the_small_targets(self):
        self.assertIn("sudo bash scripts/secrets-check.sh", steps("secrets-check")[0])
        self.assertIn("sudo bash scripts/install-timers.sh", steps("timers")[0])
        self.assertIn("sudo bash services/applier/install.sh", steps("applier")[0])

    def test_docker_and_the_journal_need_sudo_on_the_vps(self):
        # the login account is not in the docker group: `make status` stopped at its last command
        for target in ("status", "logs", "backup", "up", "deploy", "front", "prune", "prune-dry"):
            for line in steps(target):
                for word in re.findall(r"(?:^|[\s'])(\S*\s?(?:docker|journalctl))\s", line):
                    self.assertTrue(word.startswith("sudo") or " sudo " in f" {word}", (target, line))

    def test_the_payee_key_needs_its_flag_said_out_loud(self):
        self.assertNotIn("--first-install", steps("secret-gen", NAME="vault_tools_key", TYPE="key")[-1])
        self.assertIn("vault_tools_key key --first-install;", steps("secret-gen", NAME="vault_tools_key", TYPE="key", FIRST_INSTALL="1")[-1])

    def test_the_venv_is_outside_the_repo_and_the_tests_and_the_copy_use_it(self):
        made = tempfile.TemporaryDirectory()
        self.addCleanup(made.cleanup)
        home = made.name
        os.makedirs(os.path.join(home, ".venv-personal-agent", "bin"))
        python = os.path.join(home, ".venv-personal-agent", "bin", "python")
        with open(python, "w", encoding="utf-8") as f:
            f.write("")
        (venv,) = steps("venv", HOME=home)
        self.assertEqual(venv, f"bash scripts/make-venv.sh {home}/.venv-personal-agent")
        self.assertTrue(all(line.split(" -I ")[0].split()[-1] == python for line in steps("test", HOME=home)))
        self.assertIn(f"MIRROR_PY=${{MIRROR_PY:-{python}}} bash scripts/mirror.sh pemilik@alamat", steps("mirror", HOME=home))

    def test_without_a_venv_the_system_python_runs_them(self):
        self.assertTrue(all(" python3 -I " in f" {line}" for line in steps("test", HOME="/tidak/ada")))


@unittest.skipUnless(yaml, "needs PyYAML")
class DataFolders(unittest.TestCase):
    def test_every_folder_compose_mounts_is_made_by_data_dirs(self):
        # a missing bind source is created by Docker as root 0755, and the service then cannot write its own folder
        with open(os.path.join(ROOT, "config", "data.manifest"), encoding="utf-8") as f:
            made = {line.split()[0] for line in f if line.strip() and not line.startswith("#")}
        mounted = set()
        for path in ("compose/docker-compose.yml", "compose/docker-compose.comms.yml"):
            for svc in yaml.safe_load(read(path))["services"].values():
                for volume in svc.get("volumes", []):
                    source = volume.split(":")[0]
                    if source.startswith("/opt/personal-agent-data/"):
                        mounted.add(source[len("/opt/personal-agent-data/"):])
        self.assertTrue(mounted)
        self.assertLessEqual(mounted, made)
        self.assertEqual({x.split("/")[0] for x in made}, {x.split("/")[0] for x in mounted})


@unittest.skipUnless(yaml, "needs PyYAML")
class BuildContexts(unittest.TestCase):
    def test_an_image_that_copies_a_folder_ignores_python_caches(self):
        services = {}
        for path in ("compose/docker-compose.yml", "compose/docker-compose.comms.yml"):   # M4 builds the comms brokers
            services.update(yaml.safe_load(read(path))["services"])
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
        self.assertEqual(sorted(checked), ["calendar-broker", "gmail-broker", "ingest-gmail", "vault-tools"])


if __name__ == "__main__":
    unittest.main()
