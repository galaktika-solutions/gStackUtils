import unittest

from click.testing import CliRunner

from gstackutils.cli import cli


class TestEnvFileStoreage(unittest.TestCase):
    def test_simple(self):
        runner = CliRunner()
        result = runner.invoke(cli, ['conf'])
        self.assertEqual(result.exit_code, 0)
