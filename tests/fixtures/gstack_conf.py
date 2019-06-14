from gstackutils import conf
from gstackutils import fields
from gstackutils import validators


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

    dummy = conf.Service(SECRET=0, PRIVATEKEY=0)
