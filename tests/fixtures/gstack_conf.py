from gstackutils import conf
from gstackutils import fields
from gstackutils import validators
from gstackutils import cert
from gstackutils import exceptions


GSTACK_ENV_FILE = "tests/to_delete/.env"
GSTACK_SECRET_FILE = "tests/to_delete/.secret.env"
GSTACK_SECRET_DIR = "tests/to_delete/"


class CREDENTIALS(conf.Section):
    USERNAME = fields.StringField()
    PASSWORD = fields.StringField(secret=True, min_length=12)

    dummy = conf.Service(
        PASSWORD={"uid": 999, "gid": "postgres", "mode": 0o600},
    )


class TESTING(conf.Section):
    """For testing purposes only."""
    FILE = fields.FileField()
    STRING = fields.StringField(
        default="something",
        max_length=5,
        validators=(validators.LowercaseOnly(),)
    )
    SECRET = fields.StringField(secret=True)
    INTEGER = fields.IntegerField()
    BOOLEAN = fields.BooleanField()
    INTLIST = fields.IntegerListField()
    EMAIL = fields.EmailField()
    PRIVATEKEY = fields.SSLPrivateKeyField()
    CERTIFICATE = fields.SSLCertificateField()
    HOST_NAME = fields.StringField(validators=[validators.HostNameValidator(ip_ok=True)])

    dummy = conf.Service(SECRET=0, PRIVATEKEY=[0, 0])


def validate(config):
    hostname = config.get("HOST_NAME")
    privatekey = config.get("PRIVATEKEY")
    certificate = config.get("CERTIFICATE")

    if not cert.consistent(privatekey, certificate):
        raise exceptions.ValidationError("PRIVATEKEY and CERTIFICATE are inconsistent")
    if not cert.valid_for_name(hostname, certificate):
        raise exceptions.ValidationError(f"CERTIFICATE is not valid for {hostname}")


class Dummy_print(conf.Command):
    "a dummy command"

    def arguments(self, parser):
        parser.add_argument("-x")

    def cmd(self, args):
        print(f"x is {args.x}")
