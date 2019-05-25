import os
import unittest
import unittest.mock

from gstackutils import utils
from gstackutils import exceptions

from . import switch_cwd


class TestUidGid(unittest.TestCase):
    def test_it_works(self):
        self.assertEqual(1, 1)

    def test_uid_with_integer(self):
        self.assertEqual(utils.uid(0), 0)
        self.assertEqual(utils.uid(999), 999)
        self.assertEqual(utils.uid(12345), 12345)
        self.assertEqual(utils.uid("0"), 0)
        self.assertEqual(utils.uid("12345"), 12345)
        # fails if all requested
        with self.assertRaises(KeyError):
            utils.uid(12345, all=True)
        self.assertEqual(utils.uid(999, all=True).pw_uid, 999)

    def test_uid_with_name(self):
        self.assertEqual(utils.uid("postgres"), 999)
        with self.assertRaises(KeyError):
            utils.uid("johndoe")

    def test_gid(self):
        self.assertEqual(utils.gid("postgres"), 999)


@switch_cwd("tests/fixtures")
class TestPathCheck(unittest.TestCase):
    def test_fix_not_allowed_when_not_root(self):
        with unittest.mock.patch("gstackutils.utils.os.getuid") as mocked_getuid:
            mocked_getuid.return_value = 1000
            with self.assertRaises(exceptions.PermissionDenied):
                utils.path_check("x", fix=True)

    def test_raises_when_not_fixing(self):
        with self.assertRaisesRegex(exceptions.ImproperlyConfigured, "file"):
            utils.path_check("x")
        with self.assertRaisesRegex(exceptions.ImproperlyConfigured, "directory"):
            utils.path_check("x/")

    def test_creates_file_and_dirs(self):
        utils.path_check("y", fix=True)
        s = os.stat("y")
        os.remove("y")
        self.assertEqual(s.st_uid, 0)
        self.assertEqual(s.st_gid, 0)
        self.assertEqual(oct(s.st_mode)[-3:], "600")

        utils.path_check("y/", fix=True)
        s = os.stat("y")
        os.rmdir("y")
        self.assertEqual(s.st_uid, 0)
        self.assertEqual(s.st_gid, 0)
        self.assertEqual(oct(s.st_mode)[-3:], "755")

        os.chmod("onefile", 0o743)
        os.chown("onefile", 0, 0)
        utils.path_check("onefile", user="postgres", group="999", mask=0o646, fix=True)
        s = os.stat("onefile")
        self.assertEqual(s.st_uid, 999)
        self.assertEqual(s.st_gid, 999)
        self.assertEqual(oct(s.st_mode)[-3:], "642")

        os.chown("onefile", 0, 0)
        with self.assertRaises(exceptions.ImproperlyConfigured):
            utils.path_check("onefile", user=999)

        os.chmod("onefile", 0o777)
        with self.assertRaises(exceptions.ImproperlyConfigured):
            utils.path_check("onefile", mask=0o640)

        with self.assertRaises(exceptions.ImproperlyConfigured):
            utils.path_check("onefile", group="postgres")
