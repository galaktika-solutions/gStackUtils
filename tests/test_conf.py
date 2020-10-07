import unittest
import importlib

from gstackutils import conf
from . import CWDTestCase


class TestConf(CWDTestCase):
    cwd = "tests/temp"

    def test_testframework(self):
        self.assertEqual(1, 1)

    def test_load_config(self):
        conf.Config("tests.fixtures.config_module")

    def test_set_value(self):
        c = conf.Config("tests.fixtures.config_module")
        c.set("STRING", "hello")
        self.assertEqual(c.retrieve("STRING"), "hello")
