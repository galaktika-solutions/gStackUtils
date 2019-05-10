import os

from click.testing import CliRunner

from .test_conf import CleanTestCase
from gstackutils.cli import cli


class TestConfCLI(CleanTestCase):
    def test_inspect(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["conf", "inspect"])
        self.assertTrue(result.output.find("ANIMAL . duck") >= 0)
        self.assertTrue(result.output.find("LIKES ?") >= 0)

        runner.invoke(cli, ["conf", "set", "-n", "ANIMAL", "-v", "myduck"])
        result = runner.invoke(cli, ["conf", "inspect"])
        self.assertTrue(result.output.find("ANIMAL   myduck") >= 0)

        result = runner.invoke(cli, ["conf", "set", "-n", "LIKES", "-v", "me"])
        self.assertTrue(result.output.find("Error") >= 0)

        runner.invoke(cli, ["conf", "set", "--no-validate", "-n", "LIKES", "-v", "me"])
        result = runner.invoke(cli, ["conf", "inspect"])
        self.assertTrue(result.output.find("LIKES !") >= 0)

    def test_setget(self):
        runner = CliRunner(mix_stderr=False)

        result = runner.invoke(cli, ["conf", "set", "-n", "XXX", "-v", "cat"])
        self.assertEqual(result.stderr.strip(), "Error: No such config: XXX")

        result = runner.invoke(cli, ["conf", "set", "-n", "LIKES", "-v", "me"])
        self.assertEqual(result.stderr.strip(), "Error: Too short (2 < 5)")

        result = runner.invoke(cli, ["conf", "set", "-n", "ANIMAL", "-v", "cat"])
        result = runner.invoke(cli, ["conf", "get", "ANIMAL"])
        self.assertEqual(result.output, "cat")

        result = runner.invoke(cli, ["conf", "get", "XXX"])
        self.assertEqual(result.stderr.strip(), "Error: No such config: XXX")

        result = runner.invoke(cli, ["conf", "get", "LIKES"])
        self.assertEqual(
            result.stderr.strip(),
            "Error: The config is not set and no default specified."
        )

        os.environ["GSTACK_CONFIG_MODULE"] = "bad_conf"
        result = runner.invoke(cli, ["conf", "inspect"])
        self.assertEqual(
            str(result.exception),
            "Config 'ANIMAL' was defined multiple times."
        )


class TestCert(CleanTestCase):
    def test_cert(self):
        runner = CliRunner()
        runner.invoke(cli, ["cert", "-n", "mysite.com", "--silent"])
        fs = [f for f in os.listdir(".") if f.startswith("mysite.com")]
        self.assertEqual(len(fs), 3)
        for f in fs:
            os.remove(f)

    def test_cert_without_name(self):
        runner = CliRunner()
        res = runner.invoke(cli, ["cert"])
        self.assertEqual(res.exit_code, 1)
