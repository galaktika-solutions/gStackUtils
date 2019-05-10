import os

from . import CleanTestCase
from gstackutils import fields
from gstackutils import exceptions
from gstackutils.config import Config
from gstackutils import validators


class TestConfFields(CleanTestCase):
    def config(self):
        return Config(config_module="empty_conf", use_default_config_module=False)

    def test_envstring(self):
        conffield = fields.StringConfig(min_length=2, max_length=5)
        conffield._setup_field(self.config(), "X")

        # missing
        with self.assertRaises(exceptions.ConfigMissingError):
            conffield.get(root=True)
        with self.assertRaises(exceptions.ConfigMissingError):
            conffield.get(root=False)

        # present
        os.environ["X"] = "foo"
        self.assertEqual(conffield.get(root=False), "foo")
        del os.environ["X"]

        # set and get
        conffield.set("baz")
        self.assertEqual(conffield.get(root=True), "baz")
        conffield.set(None)

        # validation
        with self.assertRaises(exceptions.ValidationError):
            conffield.set("b")
        with self.assertRaises(exceptions.ValidationError):
            conffield.set("bazzzz")

        os.environ["X"] = "foooooooo"
        with self.assertRaises(exceptions.ValidationError):
            conffield.get(root=False, validate=True)
        del os.environ["X"]

        # default
        conffield = fields.StringConfig(default="okay")
        conffield._setup_field(self.config(), "X")
        self.assertEqual(conffield.get(root=True), "okay")
        with self.assertRaises(exceptions.DefaultUsedException):
            conffield.get(root=True, default_exception=True)

    def test_secretstring(self):
        conffield = fields.StringConfig(secret=True, min_length=2, max_length=10)
        conffield._setup_field(self.config(), "X")

        conffield.set("secret")
        with open(".secret.env", "r") as f:
            self.assertEqual(f.readlines()[0], "X=c2VjcmV0\n")
        self.assertEqual(conffield.get(root=True), "secret")

    def test_no_file(self):
        conffield = fields.StringConfig()
        conffield._setup_field(self.config(), "x")
        os.remove(".env")
        with self.assertRaises(exceptions.ConfigMissingError):
            conffield.get(root=True)

    def test_multiple_lines(self):
        conffield1 = fields.StringConfig()
        conffield2 = fields.StringConfig()
        conffield3 = fields.StringConfig()
        conffield1._setup_field(self.config(), "one")
        conffield2._setup_field(self.config(), "two")
        conffield3._setup_field(self.config(), "three")

        conffield1.set("1111111111")
        conffield2.set("2222222222")
        conffield3.set("3333333333")
        self.assertEqual(conffield2.get(root=True), "2222222222")
        conffield2.set(None)
        with self.assertRaises(exceptions.ConfigMissingError):
            conffield2.get(root=True)
        conffield1.set("xxx")
        self.assertEqual(conffield1.get(root=True), "xxx")

    def test_human_readable(self):
        conffield = fields.StringConfig()
        conffield._setup_field(self.config(), "x")
        self.assertEqual(conffield.to_human_readable("áíő"), "áíő")

    def test_prepare_secret(self):
        for conffield, expected in [
            (
                fields.StringConfig(secret=True, services=["test"]),
                (0, 0, 0o400)
            ),
            (
                fields.StringConfig(secret=True, services={"test": [1000]}),
                (1000, 1000, 0o400)
            ),
            (
                fields.StringConfig(secret=True, services={"test": [1000, 2000]}),
                (1000, 2000, 0o400)
            ),
            (
                fields.StringConfig(secret=True, services={"test": [1000, 2000, 0o640]}),
                (1000, 2000, 0o640)
            ),
            (
                fields.StringConfig(secret=True, services={"test": {}}),
                (0, 0, 0o400)
            ),
            (
                fields.StringConfig(secret=True, services={"test": {"uid": 1000}}),
                (1000, 1000, 0o400)
            ),
            (
                fields.StringConfig(secret=True, services={"test": {"gid": 1000}}),
                (0, 1000, 0o400)
            ),
        ]:
            conffield._setup_field(self.config(), "X")
            conffield.set("xxx")
            conffield.prepare("test")
            self.assertEqual(conffield.get(root=False), "xxx")
            stat = os.stat("secrets/X")
            self.assertEqual(stat.st_uid, expected[0])
            self.assertEqual(stat.st_gid, expected[1])
            self.assertEqual(stat.st_mode & 0o777, expected[2])
        with self.assertRaises(exceptions.ImproperlyConfigured):
            fields.StringConfig(secret=True, services=None)
        with self.assertRaises(exceptions.ImproperlyConfigured):
            fields.StringConfig(secret=True, services={"test": None})

        conffield = fields.StringConfig(secret=True)
        conffield._setup_field(self.config(), "Y")
        with self.assertRaises(exceptions.ConfigMissingError):
            conffield.get(root=False)
        with self.assertRaises(exceptions.ServiceNotFound):
            conffield.set_app("yyy", "test")

        conffield.prepare("foo")
        with self.assertRaises(exceptions.ConfigMissingError):
            conffield.get_app()

        conffield = fields.StringConfig()
        conffield._setup_field(self.config(), "A")
        conffield.set_app("aaa")
        with self.assertRaises(exceptions.ConfigMissingError):
            conffield.get_app()

    def test_bool(self):
        conffield = fields.BoolConfig()
        conffield._setup_field(self.config(), "one")
        conffield.set(True)
        self.assertEqual(conffield.get(root=True), True)
        conffield.set(False)
        self.assertEqual(conffield.get(root=True), False)
        with self.assertRaises(exceptions.InvalidValue):
            conffield.to_python(b"xxx")

    def test_file(self):
        conffield = fields.FileConfig()
        conffield._setup_field(self.config(), "one")
        conffield.set(b"abc")
        self.assertEqual(conffield.get(root=True), b"abc")
        self.assertEqual(
            conffield.to_human_readable(b"abc"),
            "File of size 3 bytes"
        )
        with open(".env", "r") as f:
            self.assertEqual(f.read(), "one=YWJj\n")

    def test_int(self):
        conffield = fields.IntConfig()
        conffield._setup_field(self.config(), "one")
        conffield.set(42)
        self.assertEqual(conffield.get(root=True), 42)
        with self.assertRaises(exceptions.InvalidValue):
            conffield.to_python(b"x")

    def test_list(self):
        conffield = fields.StringListConfig()
        conffield._setup_field(self.config(), "one")
        conffield.set(["a", "b", "c"])
        self.assertEqual(conffield.get(root=True), ["a", "b", "c"])
        with self.assertRaises(exceptions.ValidationError):
            conffield.set(["a", "b", 42])
        self.assertEqual(conffield.to_human_readable(["1"]), "['1']")

    def test_mail(self):
        conffield = fields.EmailConfig()
        self.assertEqual(conffield.to_python(b"a@b"), ("", "a@b"))
        self.assertEqual(conffield.to_bytes(("", "a@b")), b"a@b")
        self.assertEqual(conffield.to_bytes(("a", "a@b")), b"a <a@b>")

    def test_privatekey(self):
        with self.assertRaises(exceptions.ImproperlyConfigured):
            fields.SSLPrivateKey(secret=False)
        conffield = fields.SSLPrivateKey()
        conffield._setup_field(self.config(), "PK")
        hr = conffield.to_human_readable(validators.CertificateValidator.pk.encode())
        self.assertEqual(hr, "SSL private key file of size 1674 bytes")
