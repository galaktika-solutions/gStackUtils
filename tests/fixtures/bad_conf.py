from gstackutils.config import Section
from gstackutils import fields


GSTACK_ENV_FILE = ".env"
GSTACK_SECRET_FILE = ".secret.env"
GSTACK_SECRET_DIR = "secrets"
GSTACK_THEME = "simple"
GSTACK_PG_HBA_ORIG = "pg_hba.conf"
GSTACK_PG_CONF_ORIG = "postgresql.conf"


class First(Section):
    ANIMAL = fields.StringConfig(default="duck")


class Empty(Section):
    ANIMAL = fields.StringConfig()
