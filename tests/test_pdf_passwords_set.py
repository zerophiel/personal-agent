import importlib.util
import json
import os
import tempfile
import unittest

_p = os.path.join(os.path.dirname(__file__), "..", "scripts", "pdf-passwords-set.py")
_s = importlib.util.spec_from_file_location("pps", _p)
pps = importlib.util.module_from_spec(_s)
_s.loader.exec_module(pps)


class Collect(unittest.TestCase):
    def test_hidden_prompts_build_json_with_awkward_characters(self):
        answers = iter(['p"a\\ss,1', "second", "",          # dbs: two passwords
                        "", "", "", "", "", "", ""])        # remaining banks skipped
        shown = []
        got = pps.collect(prompt=lambda _: next(answers), say=shown.append)
        self.assertEqual(got, {"dbs": ['p"a\\ss,1', "second"]})
        self.assertEqual(json.loads(json.dumps(got)), got)       # round-trips through JSON
        self.assertEqual(shown, ["  dbs: 2 password"])           # only counts are shown, never values

    def test_merge_keeps_unentered_banks_and_overrides_entered(self):
        merged = pps.merge({"CIMB": ["old"], "dbs": ["old"]}, {"dbs": ["new"]})
        self.assertEqual(merged, {"cimb": ["old"], "dbs": ["new"]})

    def test_all_blank_changes_nothing(self):
        self.assertEqual(pps.collect(prompt=lambda _: "", say=lambda *_: None), {})


class InPlace(unittest.TestCase):
    def test_rewrite_keeps_inode(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "pw")
            open(path, "w").write("{}")
            before = os.stat(path).st_ino
            with open(path, "r+") as f:      # same pattern as main()
                f.seek(0); f.truncate(); json.dump({"a": ["b"]}, f)
            self.assertEqual(os.stat(path).st_ino, before)
            self.assertEqual(json.load(open(path)), {"a": ["b"]})


if __name__ == "__main__":
    unittest.main()
