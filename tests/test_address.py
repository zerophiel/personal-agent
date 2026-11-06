"""config/vps.env is the one place the address of the VPS lives, so a move changes two lines there and nothing else. Failures name
the file and line, never the address."""
import ipaddress
import os
import re
import subprocess
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
ADDRESS = os.path.join(ROOT, "config", "vps.env")
IPV4 = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])")


def settings():
    with open(ADDRESS, encoding="utf-8") as f:
        return dict(line.strip().split("=", 1) for line in f if "=" in line and not line.startswith("#"))


def is_public(text):
    try:
        return ipaddress.ip_address(text).is_global
    except ValueError:
        return False


def make(target, *variables, **env):
    clean = {k: v for k, v in os.environ.items() if k not in ("VPS_HOST", "VPS_USER")}
    done = subprocess.run(["make", "-n", "--no-print-directory", "-C", ROOT, target, *variables], env=dict(clean, **env),
                          capture_output=True, text=True, timeout=30, check=True)
    return done.stdout


class OneFile(unittest.TestCase):
    def test_no_other_file_names_a_public_address(self):
        listed = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT,
                                capture_output=True, text=True, check=True, timeout=30).stdout.split("\0")
        self.assertIn("config/vps.env", listed)
        found = []
        for name in listed:
            if not name or name == "config/vps.env" or name.endswith(".lock"):   # a lock holds versions, some with four parts
                continue
            try:
                with open(os.path.join(ROOT, name), encoding="utf-8") as f:
                    found += [f"{name}:{n}" for n, line in enumerate(f, 1) if any(is_public(x) for x in IPV4.findall(line))]
            except (OSError, UnicodeDecodeError):   # deleted in the working tree, or not text
                continue
        self.assertEqual(found, [])

    def test_the_file_names_a_host_and_a_login(self):
        vps = settings()
        self.assertEqual(sorted(vps), ["VPS_HOST", "VPS_USER"])
        self.assertTrue(is_public(vps["VPS_HOST"]) or re.fullmatch(r"[a-z0-9.-]+", vps["VPS_HOST"]), "VPS_HOST")
        self.assertRegex(vps["VPS_USER"], r"^[a-z_][a-z0-9_-]*$")


class Make(unittest.TestCase):
    def test_it_reads_the_file(self):
        vps = settings()
        self.assertTrue(make("status").startswith(f"ssh {vps['VPS_USER']}@{vps['VPS_HOST']} "), "make status")

    def test_another_host_on_the_command_line(self):
        self.assertTrue(make("status", "VPS_HOST=lama", "VPS_USER=orang").startswith("ssh orang@lama "))

    def test_another_host_in_the_environment(self):
        self.assertTrue(make("status", VPS_HOST="lama", VPS_USER="orang").startswith("ssh orang@lama "))

    def test_the_runtime_map_goes_to_the_same_host(self):
        self.assertIn("collect.py --host orang@lama", make("runtime-map", "VPS_HOST=lama", "VPS_USER=orang"))


if __name__ == "__main__":
    unittest.main()
