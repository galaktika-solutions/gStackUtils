import subprocess
import os

from gstackutils.db import ensure, wait_for_db
from gstackutils.exceptions import DatabaseNotPresent
from . import CleanTestCase


class TestDB(CleanTestCase):
    def test_ensure(self):
        ensure()

    def test_wait(self):
        env = os.environ.copy()
        env.update({"PYTHONPATH": "."})
        dbprocess = subprocess.Popen(
            ["gstack", "start", "postgres"],
            env=env,
            stderr=subprocess.DEVNULL,
        )
        wait_for_db()
        dbprocess.terminate()
        dbprocess.wait()
        with self.assertRaises(DatabaseNotPresent):
            wait_for_db(timeout=0)
