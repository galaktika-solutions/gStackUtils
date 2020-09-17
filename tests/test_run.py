import os
import unittest
# import unittest.mock

from . import CleanTestCase
from gstackutils import run


@unittest.skip("refactoring")
class TestRun(CleanTestCase):
    def test_it_works(self):
        ret = run.run(
            ["touch", "tests/to_delete/x"],
            usr=999, grp="postgres", silent=True)
        self.assertEqual(ret, 1)
        with self.assertRaises(SystemExit):
            ret = run.run(
                ["touch", "tests/to_delete/x"],
                grp="postgres", silent=True, exit=True)
        stat = os.stat("tests/to_delete/x")
        self.assertEqual(stat.st_uid, 0)
        self.assertEqual(stat.st_gid, 999)

    def test_no_user(self):
        with self.assertRaises(KeyError):
            run.run(["id"], usr="foo")

    def test_no_group(self):
        with self.assertRaises(KeyError):
            run.run(["id"], grp="foo")
