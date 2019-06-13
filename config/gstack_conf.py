from gstackutils import conf
from gstackutils import fields


class PYPI_CREDENTIALS(conf.Section):
    PYPI_USERNAME = fields.StringField()
    PYPI_PASSWORD = fields.StringField(secret=True, min_length=12)

    postgres = conf.Service(
        PYPI_PASSWORD={"uid": 999, "gid": "postgres", "mode": 0o600},
    )
