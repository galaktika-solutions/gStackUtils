import unittest
import os
import shutil


class CleanTestCase(unittest.TestCase):
    def setUp(self):
        os.environ["GSTACK_CONFIG_MODULE"] = "tests.fixtures.gstack_conf"
        try:
            shutil.rmtree("tests/to_delete")
        except Exception:
            pass
        os.makedirs("tests/to_delete")

    def tearDown(self):
        shutil.rmtree("tests/to_delete")
