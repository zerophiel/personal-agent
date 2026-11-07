"""Every image is fixed by digest and every Python package by version, so a rebuild on a new host runs the same code.
A tag or a loose package would move on its own between now and the move, and nobody would see it until the bot behaves differently."""
import glob
import os
import re
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}$")
LOCK_LINE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9.+!_-]*$")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def in_repo(pattern):
    return sorted(glob.glob(os.path.join(ROOT, pattern)))


def short(path):
    return os.path.relpath(path, ROOT)


def package_name(name):
    return re.sub(r"[-_.]+", "-", name).lower()


def pins(path):
    """{package: version} from the name==version lines of a requirements file."""
    rows = (line.strip() for line in read(path).splitlines())
    return {package_name(row.split("==")[0]): row.split("==")[1] for row in rows if "==" in row and not row.startswith("#")}


def dockerfiles():
    paths = in_repo("services/*/Dockerfile")
    assert len(paths) >= 5, paths
    return paths


class Images(unittest.TestCase):
    def test_every_compose_image_names_a_digest(self):
        paths = in_repo("compose/*.yml")
        self.assertGreaterEqual(len(paths), 2)
        for path in paths:
            images = re.findall(r"^\s*image:\s*(\S+)", read(path), re.M)
            self.assertTrue(images, short(path))
            for image in images:
                self.assertRegex(image, DIGEST, short(path))

    def test_every_dockerfile_starts_from_a_digest(self):
        for path in dockerfiles():
            bases = re.findall(r"^FROM\s+(\S+)", read(path), re.M)
            self.assertTrue(bases, short(path))
            for base in bases:
                self.assertRegex(base, DIGEST, short(path))

    def test_all_services_share_one_base_and_all_zones_one_squid(self):
        self.assertEqual(len({re.search(r"^FROM\s+(\S+)", read(path), re.M).group(1) for path in dockerfiles()}), 1)
        squids = {image for path in in_repo("compose/*.yml") for image in re.findall(r"^\s*image:\s*(ubuntu/squid\S+)", read(path), re.M)}
        self.assertEqual(len(squids), 1)


class Locks(unittest.TestCase):
    def locks(self):
        paths = in_repo("services/*/requirements.lock")
        self.assertGreaterEqual(len(paths), 3)
        return paths

    def test_every_service_with_requirements_has_a_lock(self):
        for path in in_repo("services/*/requirements.txt"):
            self.assertTrue(os.path.exists(path[:-len("txt")] + "lock"), short(path))

    def test_a_lock_holds_exact_versions_only(self):
        for path in self.locks():
            rows = [line for line in read(path).splitlines() if not line.startswith("#")]
            self.assertTrue(rows, short(path))
            for row in rows:
                self.assertRegex(row, LOCK_LINE, short(path))
            names = [package_name(row.split("==")[0]) for row in rows]
            self.assertEqual(len(names), len(set(names)), short(path))

    def test_what_a_service_asks_for_is_in_its_lock_at_that_version(self):
        for path in in_repo("services/*/requirements.txt"):
            wanted = pins(path)
            self.assertTrue(wanted, short(path))
            locked = pins(path[:-len("txt")] + "lock")
            for name, version in wanted.items():
                self.assertEqual(locked.get(name), version, f"{short(path)}: {name}")

    def test_an_image_installs_from_its_lock_and_never_from_the_loose_list(self):
        installing = 0
        for path in dockerfiles():
            text = read(path)
            self.assertNotIn("requirements.txt", text, short(path))
            for line in text.splitlines():
                if "pip install" in line:
                    installing += 1
                    self.assertIn("-r requirements.lock", line, short(path))
                    self.assertTrue(os.path.exists(os.path.join(os.path.dirname(path), "requirements.lock")), short(path))
                    self.assertRegex(text, r"(?m)^COPY \S*requirements\.lock \.$", short(path))
        self.assertEqual(installing, 3)


if __name__ == "__main__":
    unittest.main()
