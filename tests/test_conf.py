import unittest
from io import StringIO
import os

from . import CleanTestCase

from gstackutils import conf


class TestConf(CleanTestCase):
    def test_inspect(self):
        config = conf.Config()
        with unittest.mock.patch('sys.stdout', new=StringIO()) as out:
            config.inspect()
            outlines = [l.strip() for l in out.getvalue().split("\n")]
        self.assertTrue("STRING . something" in outlines)

        config.set("USERNAME", "foo")
        self.assertEqual(config.get("USERNAME"), "foo")
        config.set("STRING", "x")
        self.assertEqual(config.get("STRING"), "x")
        config.set("PASSWORD", "bar123456789")
        self.assertEqual(config.get("PASSWORD"), "bar123456789")

        config = conf.Config(root_mode=False)
        os.environ["USERNAME"] = "foo"
        self.assertEqual(config.get("USERNAME"), "foo")
        del os.environ["USERNAME"]
