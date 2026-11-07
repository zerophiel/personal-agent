"""docs/REBUILD.md is followed as written, by a person or an AI: what it names must exist and its order must hold."""
import os
import re
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def read(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return f.read()


DOC = read("docs/REBUILD.md")


def section(title):
    return DOC.split(f"\n## {title}\n", 1)[1].split("\n## ", 1)[0]


def targets(text):
    """The make targets named in order: in backticks in the prose, at the start of a line inside a code block."""
    found, code = [], False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            code = not code
        elif code:
            found += re.findall(r"^\s*make ([a-z][a-z-]*)", line)
        else:
            found += re.findall(r"`make ([a-z][a-z-]*)", line)
    return found


def in_order(wanted, found):
    remaining = iter(found)
    return all(step in remaining for step in wanted)


class Names(unittest.TestCase):
    def test_every_make_target_it_names_exists(self):
        have = set(re.findall(r"^([a-z][a-z-]*):", read("Makefile"), re.M))
        named = set(targets(DOC))
        self.assertGreater(len(named), 12)
        self.assertEqual(named - have, set())

    def test_every_repo_file_it_names_exists(self):
        named = set(re.findall(r"`((?:scripts|docs|services|config|host|compose|ops)/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*)", DOC))
        self.assertGreater(len(named), 4)
        self.assertEqual([p for p in sorted(named) if not os.path.exists(os.path.join(ROOT, p))], [])

    def test_it_opens_with_the_prompt_to_paste(self):
        self.assertLess(DOC.index("> Rebuild bot ini ke VPS"), DOC.index("\n## "))
        self.assertIn("jangan\n> menampilkan isi `private/`", DOC)

    def test_every_minimum_it_states_is_what_preflight_checks(self):
        script = read("scripts/preflight.sh")
        self.assertIn("MIN_CPUS=2", script)
        self.assertIn("MIN_MEM_MB=7000", script)
        self.assertIn("MIN_DISK_GB=40", script)
        self.assertIn("at least 2 vCPUs, 7 GB of memory and 40 GB of free disk", DOC)


class TheWay(unittest.TestCase):
    way = section("The way")

    def test_the_steps_keep_their_order(self):
        wanted = ["bootstrap", "preflight", "applied-pull", "mirror", "restore", "applied-pull", "sync", "secrets-check", "render-envs",
                  "up", "front", "applier", "timers", "verify", "applied-pull", "runtime-map", "mirror"]
        self.assertTrue(in_order(wanted, targets(self.way)), targets(self.way))

    def test_the_images_are_made_while_the_old_bot_lives(self):
        """A pin meets a real build here at the latest, and a failure must not cost any downtime."""
        before_the_freeze = self.way.split("### The move", 1)[0]
        self.assertTrue(in_order(["preflight", "sync", "images", "applied-pull"], targets(before_the_freeze)), targets(before_the_freeze))

    def test_the_steps_are_numbered_one_to_eighteen(self):
        self.assertEqual([int(n) for n in re.findall(r"^(\d+)\. ", self.way, re.M)], list(range(1, 19)))

    def test_the_timers_come_after_everything_they_need(self):
        named = targets(self.way)
        last = max(i for i, t in enumerate(named) if t == "timers")
        for start in ("up", "front", "applier"):
            self.assertLess(max(i for i, t in enumerate(named) if t == start), last, start)

    def test_the_freeze_comes_before_anything_starts_and_keeps_the_volumes(self):
        freeze = self.way.split("\n5. ", 1)[1].split("\n6. ", 1)[0]
        self.assertIn("disable --now", freeze)
        self.assertIn(" down\n", freeze)
        for flag in (" -v", "--volumes", "--rmi", "prune"):
            self.assertNotIn(flag, freeze)
        self.assertLess(self.way.index("\n5. "), self.way.index("`make up`"))

    def test_the_copy_of_the_move_must_come_from_a_frozen_host(self):
        self.assertIn("must say `host frozen`", self.way)
        self.assertIn("'frozen' if frozen else 'live'", read("scripts/mirror-check.py"))

    def test_it_warns_of_what_hermes_discards_as_long_as_the_default_holds(self):
        self.assertIn("is lost, and has to be sent again", self.way)
        self.assertLess(self.way.index("is lost, and has to be sent again"), self.way.index("\n5. "))
        configs = [os.path.join(folder, name) for folder, _, names in os.walk(os.path.join(ROOT, "services", "hermes"))
                   for name in names if name.endswith((".yaml", ".yml"))]
        self.assertTrue(configs)
        for path in configs:
            with open(path, encoding="utf-8") as f:
                self.assertNotIn("drop_pending_on_cold_boot", f.read(), path)

    def test_the_steps_that_need_the_owner_are_marked(self):
        for number in ("2", "15", "18"):
            step = re.search(rf"^{number}\. .*?(?=^\d+\. |\Z)", self.way, re.M | re.S).group(0)
            self.assertIn("[owner's terminal]", step, number)


class OtherWays(unittest.TestCase):
    def test_going_back_stops_the_new_host_before_the_old_one_starts(self):
        back = section("Going back")
        self.assertLess(back.index(" down\n"), back.index("make up VPS_HOST=<old address> VPS_USER=<old login>"))
        self.assertTrue(in_order(["up", "front", "applier", "timers", "verify"], targets(back)))
        for line in back.splitlines():
            if line.strip().startswith("make "):
                self.assertIn("VPS_HOST=<old address> VPS_USER=<old login>", line)

    def test_going_back_says_how_to_try_again(self):
        back = section("Going back")
        self.assertIn("A new try starts again at step 1", back)
        self.assertIn("reinstall the instance at the provider", back)

    def test_the_console_repair_reloads_sshd_and_the_script_says_the_same(self):
        repair = "rm -f /etc/ssh/sshd_config.d/00-hardening.conf && ufw disable && systemctl reload-or-restart ssh"
        self.assertIn(repair, DOC)
        self.assertIn(repair, read("scripts/bootstrap.sh"))

    def test_the_r2_limit_is_due_before_restic_first_runs_on_the_new_host(self):
        row = next(line for line in DOC.splitlines() if line.startswith("| Cloudflare R2 |"))
        self.assertIn("before `make timers`", row)
        self.assertIn("in the disaster path before `make snapshots`", row)

    def test_the_disaster_path_decides_by_the_snapshots_and_reports_only(self):
        disaster = section("Disaster: the old host is gone")
        self.assertTrue(in_order(["snapshots", "restore-restic"], targets(disaster)))
        self.assertIn("`make verify R2=1`", disaster)
        self.assertIn("`make mirror ALLOW_SHRINK=1`", disaster)
        self.assertIn("delete the instance before step 11", disaster)

    def test_the_r2_rotation_proves_the_new_key_before_the_old_one_goes(self):
        rotate = section("Rotating the R2 key")
        self.assertTrue(in_order(["mirror", "snapshots"], targets(rotate)))
        self.assertLess(rotate.index("`make snapshots`"), rotate.index("Delete the old token"))
        self.assertIn('"$vps/secrets/restic.env"', read("scripts/restore.sh"))   # why the copy must hold the new key first
        for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD"):
            self.assertIn(name, rotate)

    def test_the_runbook_points_here_for_a_restore(self):
        restore = read("docs/RUNBOOK.md").split("\n## Restore", 1)[1]
        self.assertIn("docs/REBUILD.md", restore)
        self.assertNotIn("scratch directory", restore)


if __name__ == "__main__":
    unittest.main()
