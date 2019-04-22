import unittest
import os

from click.testing import CliRunner

from gstackutils.cli import cli
from gstackutils.conf import Config
from gstackutils import ImproperlyConfigured


class BaseCLITetsCase(unittest.TestCase):
    config_module = "gstack_conf"

    def setUp(self):
        os.chdir("tests/fixtures")
        os.makedirs(".git", exist_ok=True)
        os.environ["GSTACK_ENV_FILE"] = ".env"
        os.environ["GSTACK_SECRET_FILE"] = ".secret.env"
        os.environ["GSTACK_CONFIG_MODULE"] = self.config_module

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
        del os.environ["GSTACK_ENV_FILE"]
        del os.environ["GSTACK_SECRET_FILE"]
        del os.environ["GSTACK_CONFIG_MODULE"]


class TestCLI(BaseCLITetsCase):
    def test_simple(self):
        runner = CliRunner()
        runner.invoke(cli, ["conf", "set", "ANIMAL", "dog"])
        runner.invoke(cli, ["conf", "set", "--no-validate", "TIMES", "x"])
        result = runner.invoke(cli, ["conf", "inspect"])
        self.assertEqual(result.exit_code, 0)
        lines = result.output.splitlines()
        self.assertEqual(
            lines,
            [
                'First',
                '    ANIMAL   dog',
                '      SAIS . **********',
                '     TIMES ! ',
                '     AFTER ? '
            ]
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

        runner.invoke(cli, ["conf", "set", "--no-validate", "TIMES", "x"])
        result = runner.invoke(cli, ["conf", "get", "TIMES"])
        self.assertEqual(result.stderr.strip(), "Error: Too short (1 < 5)")


class TestBadCLI(BaseCLITetsCase):
    config_module = "bad_conf"

    def test_multidefined_fields(self):
        with self.assertRaises(ImproperlyConfigured):
            Config()


class TestCert(BaseCLITetsCase):
    def test_cert(self):
        runner = CliRunner()
        runner.invoke(cli, ["cert", "-n", "mysite.com"])
        fs = [f for f in os.listdir(".") if f.startswith("mysite.com")]
        self.assertEqual(len(fs), 3)
        for f in fs:
            os.remove(f)

    def test_cert_without_name(self):
        runner = CliRunner()
        res = runner.invoke(cli, ["cert"])
        self.assertEqual(res.exit_code, 1)
