import unittest
import os

from click.testing import CliRunner

from gstackutils.cli import cli
from gstackutils.conf import Config


class TestEnvFileStoreage(unittest.TestCase):
    def setUp(self):
        os.chdir("tests/fixtures")
        os.makedirs(".git", exist_ok=True)
        os.environ["GSTACK_ENV_FILE"] = ".env"
        os.environ["GSTACK_SECRET_FILE"] = ".secret.env"

    def tearDown(self):
        if os.path.isdir(".git"):
            os.rmdir(".git")
        if os.path.isfile(".env"):
            os.remove(".env")
        if os.path.isfile(".secret.env"):
            os.remove(".secret.env")
        if os.path.isdir(".files"):
            for f in os.listdir(".files"):
                os.remove(os.path.join(".files", f))
            os.rmdir(".files")
        os.chdir("../..")

    def test_simple(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["conf", "inspect"])
        self.assertEqual(result.exit_code, 0)
        lines = result.output.splitlines()
        self.assertEqual(
            lines,
            ['First', '    ANIMAL . duck', '      SAIS . **********', '     TIMES ? ']
        )

    def test_setget(self):
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(cli, ["conf", "set", "XXX", "cat"])
        self.assertEqual(result.stderr.strip(), "Error: No such config: XXX")

        result = runner.invoke(cli, ["conf", "set", "TIMES", "x"])
        self.assertEqual(result.stderr.strip(), "Error: Too short (1 < 5)")

        result = runner.invoke(cli, ["conf", "set", "ANIMAL", "cat"])
        result = runner.invoke(cli, ["conf", "get", "ANIMAL"])
        self.assertEqual(result.output, "cat")

        result = runner.invoke(cli, ["conf", "get", "XXX"])
        self.assertEqual(result.stderr.strip(), "Error: No such config: XXX")

        result = runner.invoke(cli, ["conf", "get", "TIMES"])
        self.assertEqual(
            result.stderr.strip(),
            "Error: The config is not set and no default specified."
        )

        config = Config()
        field, _ = config.field_map["TIMES"]
        field.set("x", no_validate=True)
        result = runner.invoke(cli, ["conf", "get", "TIMES"])
        self.assertEqual(result.stderr.strip(), "Error: Too short (1 < 5)")
