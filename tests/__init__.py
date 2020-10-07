import unittest
import os
import shutil


class CWDTestCase(unittest.TestCase):
    def setUp(self):
        self._orig_cwd = os.getcwd()
        os.makedirs(self.cwd, exist_ok=True)
        os.chdir(self.cwd)
    def tearDown(self):
        os.chdir(self._orig_cwd)
        shutil.rmtree(self.cwd)
