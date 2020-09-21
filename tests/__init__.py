import unittest
import os


class CWDTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        os.chdir(self.cwd)
    def tearDown(self):
        os.chdir(self._orig_cwd)
