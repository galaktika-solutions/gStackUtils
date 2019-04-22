import unittest
import unittest.mock
import os
import subprocess


# from gstackutils import run, ImproperlyConfigured
from gstackutils.db import ensure, wait_for_db
from gstackutils import DatabaseNotPresent


class TestDB(unittest.TestCase):
    def test_ensure(self):
        ensure(pg_init_module="tests.fixtures.gstack_conf")

        env = os.environ.copy()
        env["GSTACK_PG_INIT_MODULE"] = "tests.fixtures.gstack_conf"

        dbprocess = subprocess.Popen(
            ["gstack", "db", "start"],
            env=env
        )
        wait_for_db(pg_init_module="tests.fixtures.gstack_conf")
        dbprocess.terminate()
        dbprocess.wait()

        with self.assertRaises(DatabaseNotPresent):
            wait_for_db(timeout=0, pg_init_module="tests.fixtures.gstack_conf")
