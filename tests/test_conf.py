import unittest
from io import StringIO

from . import CleanTestCase

from gstackutils import conf


class TestConf(CleanTestCase):
    def test_inspect(self):
        config = conf.Config()
        with unittest.mock.patch('sys.stdout', new=StringIO()) as out:
            config.inspect()
            outlines = [l.strip() for l in out.getvalue().split("\n")]
        # print(outlines)
        self.assertTrue("STRING . something" in outlines)
