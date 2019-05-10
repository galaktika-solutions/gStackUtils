import unittest
import os
# import sys


class CleanTestCase(unittest.TestCase):
    def setUp(self):
        os.chdir("tests/fixtures")
        os.makedirs(".git", exist_ok=True)
        os.environ["GSTACK_CONFIG_MODULE"] = "gstack_conf"
        # sys.path.insert(0, ".")

    def tearDown(self):
        if os.path.isfile(".env"):
            os.remove(".env")
        if os.path.isfile(".secret.env"):
            os.remove(".secret.env")
        if os.path.isdir("secrets"):
            for f in os.listdir("secrets"):
                os.remove(os.path.join("secrets", f))
            os.rmdir("secrets")
        del os.environ["GSTACK_CONFIG_MODULE"]
        os.rmdir(".git")
        os.chdir("/src")
        # sys.path.pop(0)
