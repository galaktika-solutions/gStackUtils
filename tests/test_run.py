import unittest
import unittest.mock
import os

from gstackutils import run, ImproperlyConfigured


class TestCertificates(unittest.TestCase):
    def test_it_works(self):
        with self.assertRaises(SystemExit):
            run(["touch", "/tmp/x"], usr=1234, grp=2345, exit=True)
        stat = os.stat("/tmp/x")
        self.assertEqual(stat.st_uid, 1234)
        self.assertEqual(stat.st_gid, 2345)

    def test_with_username(self):
        run(["ls"], usr="postgres", exit=False, silent=True)
        run(["ls"], usr="postgres", grp="postgres", exit=False, silent=True)
        run(["ls"], usr=1234, grp="postgres", exit=False, silent=True)
        run(["ls"], usr=1234, exit=False, silent=True)

    def test_no_user(self):
        with self.assertRaises(ImproperlyConfigured):
            run(["ls"], usr="x")
