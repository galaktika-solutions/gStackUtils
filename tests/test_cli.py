import os

from click.testing import CliRunner

from .test_conf import ConfTestCase
from gstackutils.cli import cli
from gstackutils.run import run


class TestConfCLI(ConfTestCase):
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

    def test_prepare(self):
        runner = CliRunner()
        runner.invoke(cli, ["conf", "set", "-n", "LIKES", "-v", "green stuff"])
        runner.invoke(cli, ["conf", "set", "-n", "COLOR", "-v", "yellow"])
        runner.invoke(cli, ["conf", "set", "-n", "SAIS", "-v", "quaackk"])
        runner.invoke(cli, ["conf", "prepare", "test"])
        with open(os.path.join("secrets", "SAIS"), "r") as f:
            self.assertEqual(f.read(), "quaackk")
        result = runner.invoke(cli, ["conf", "get", "SAIS"])
        self.assertEqual(result.output, "quaackk")
        retcode = run(
            ("gstack", "conf", "get", "SAIS"),
            usr="postgres", extraenv={"PYTHONPATH": "."}, silent=True
        )
        self.assertEqual(retcode, 1)


class TestCert(ConfTestCase):
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
