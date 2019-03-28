import unittest
import os

from gstackutils.conf.storage import (
    EnvFileStorage,
    SecretFileStorage,
    EnvVarStorage,
    SecretStorage
)
from gstackutils.conf import EnvString, SecretString, Config
from gstackutils.conf.exceptions import ConfigMissingError, ValidationError
from gstackutils.exceptions import ImproperlyConfigured


class CleanConfTestCase(unittest.TestCase):
    class config:
        env_file_path = "tests/.env"
        secret_file_path = "tests/.secret.env"
        secret_dir = "tests/secrets"

    def setUp(self):
        if not os.path.isfile(self.config.env_file_path):
            open(self.config.env_file_path, "w").close()
        if not os.path.isfile(self.config.secret_file_path):
            open(self.config.secret_file_path, "w").close()
        if not os.path.isdir(self.config.secret_dir):
            os.mkdir(self.config.secret_dir)

    def tearDown(self):
        if os.path.isfile(self.config.env_file_path):
            os.remove(self.config.env_file_path)
        if os.path.isfile(self.config.secret_file_path):
            os.remove(self.config.secret_file_path)
        if os.path.isdir(self.config.secret_dir):
            for f in os.listdir(self.config.secret_dir):
                os.remove(os.path.join(self.config.secret_dir, f))
            os.rmdir(self.config.secret_dir)


class TestEnvFileStoreage(CleanConfTestCase):
    def test_nonexistent(self):
        efs = EnvFileStorage(self.config.env_file_path)
        self.assertEqual(efs.read("somevar"), None)

    def test_readwrite(self):
        efs = EnvFileStorage(self.config.env_file_path)
        efs.write("x", b"abc")
        self.assertEqual(efs.read("x"), b"abc")

    def test_readwritemore(self):
        efs = EnvFileStorage(self.config.env_file_path)
        efs.write("x", b"abc")
        efs.write("y", b"lmn")
        efs.write("z", b"pqr")
        self.assertEqual(efs.read("y"), b"lmn")
        efs.delete("y")
        self.assertEqual(efs.read("y"), None)
        self.assertEqual(efs.read("z"), b"pqr")
        efs.write("z", b"new")
        self.assertEqual(efs.read("z"), b"new")


class TestSecretFileStoreage(CleanConfTestCase):
    def test_nonexistent(self):
        sfs = SecretFileStorage(self.config.env_file_path)
        self.assertEqual(sfs.read("somevar"), None)

    def test_readwrite(self):
        sfs = SecretFileStorage(self.config.env_file_path)
        sfs.write("x", b"abc")
        self.assertEqual(sfs.read("x"), b"abc")


class TestEnvVarStorage(CleanConfTestCase):
    def test_nonexistent(self):
        evs = EnvVarStorage()
        self.assertEqual(evs.read("somevar"), None)

    def test_readwrite(self):
        evs = EnvVarStorage()
        evs.write("x", b"abc")
        self.assertEqual(evs.read("x"), b"abc")

    def test_delete(self):
        evs = EnvVarStorage()
        evs.write("x", b"abc")
        evs.delete("x")
        self.assertEqual(evs.read("x"), None)


class TestSecretStorage(CleanConfTestCase):
    def test_nonexistent(self):
        ses = SecretStorage(dir=self.config.secret_dir)
        self.assertEqual(ses.read("somevar"), None)

    def test_readwrite(self):
        evs = SecretStorage(dir=self.config.secret_dir)
        evs.write("x", b"abc", uid=1000, gid=1000, mode=0o440)
        self.assertEqual(evs.read("x"), b"abc")

    def test_delete(self):
        evs = SecretStorage(dir=self.config.secret_dir)
        evs.write("x", b"abc", uid=1000, gid=1000, mode=0o440)
        evs.delete("x")
        self.assertEqual(evs.read("x"), None)


class TestEnvString(CleanConfTestCase):
    def test_nonexistent(self):
        conffield = EnvString()
        conffield.setup_field(self.config, "X")
        with self.assertRaises(ConfigMissingError):
            conffield.get(root=True)

    def test_simple_set_get(self):
        conffield = EnvString()
        conffield.setup_field(self.config, "X")
        conffield.set("hello")
        self.assertEqual(conffield.get(root=True), "hello")

    def test_default_used(self):
        conffield = EnvString(default="world")
        conffield.setup_field(self.config, "X")
        self.assertEqual(conffield.get(root=True), "world")

    def test_delete(self):
        conffield = EnvString()
        conffield.setup_field(self.config, "X")
        conffield.delete()
        conffield.set("hello")
        self.assertEqual(conffield.get(root=True), "hello")
        conffield.delete()
        with self.assertRaises(ConfigMissingError):
            conffield.get(root=True)

    def test_validation(self):
        conffield = EnvString(min_length=5, max_length=9)
        conffield.setup_field(self.config, "X")
        with self.assertRaises(ValidationError):
            conffield.set("x")
        with self.assertRaises(ValidationError):
            conffield.set("1234567890")
        with self.assertRaises(ValidationError):
            conffield.set(0)


class TestSecretStrint(CleanConfTestCase):
    def test_prepare(self):
        conffield = SecretString()
        conffield.setup_field(self.config, "X")
        conffield.set("x")
        conffield.prepare(uid=1000)
        p = os.path.join(self.config.secret_dir, "X")
        with open(p, "r") as f:
            self.assertEqual(f.read(), "x")
        stat = os.stat(p)
        self.assertEqual(stat.st_uid, 1000)


class TestConfig(unittest.TestCase):
    def setUp(self):
        os.chdir("tests/fixtures")
        os.makedirs(".git", exist_ok=True)

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

    def test_wrong_prod(self):
        os.rmdir(".git")
        with self.assertRaises(ImproperlyConfigured):
            Config()

    def test_init(self):
        conf = Config(
            config_module="gstack_conf",
            env_file_path=".env",
            secret_file_path=".secret.env",
            root_mode=True
        )
        # print(conf.fields)
        self.assertEqual(conf.env_file_path, ".env")
