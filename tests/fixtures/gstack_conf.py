import psycopg2

from gstackutils.config import Section
from gstackutils import fields
from gstackutils.helpers import pg_pass


GSTACK_ENV_FILE = ".env"
GSTACK_SECRET_FILE = ".secret.env"
GSTACK_SECRET_DIR = "secrets"
GSTACK_THEME = "simple"
GSTACK_PG_HBA_ORIG = "pg_hba.conf"
GSTACK_PG_CONF_ORIG = "postgresql.conf"


class First(Section):
    ANIMAL = fields.StringConfig(default="duck")
    SAIS = fields.StringConfig(secret=True, default="quack", min_length=3, services={"test": {}})
    LIKES = fields.StringConfig(min_length=5)
    COLOR = fields.StringConfig()
    DANGEROUS = fields.BoolConfig(default=False)


class Empty(Section):
    pass


def pg_init(conf):
    postgres_pass = pg_pass("postgres", "postgres")

    return([
        {
            "sql": "ALTER ROLE postgres ENCRYPTED PASSWORD %s",
            "params": (postgres_pass,),
        },
    ])


def healthcheck(conf):
    dbname = "postgres"
    user = "postgres"
    password = "postgres"
    host = "127.0.0.1"
    psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
