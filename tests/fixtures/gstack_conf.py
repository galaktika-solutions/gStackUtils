import psycopg2

from gstackutils.config import Section
from gstackutils.fields import EnvString, SecretString, EnvBool
from gstackutils.helpers import pg_pass


class First(Section):
    ANIMAL = EnvString(default="duck")
    SAIS = SecretString(default="quack", min_length=3, services={"test": []})
    LIKES = EnvString(min_length=5)
    COLOR = EnvString()
    DANGEROUS = EnvBool(default=False)


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
