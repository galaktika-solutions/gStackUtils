import psycopg2

from gstackutils.conf import Section, EnvString, SecretString
from gstackutils.helpers import pg_pass


class First(Section):
    ANIMAL = EnvString(default="duck")
    SAIS = SecretString(default="quack", min_length=3, services={"test": []})
    TIMES = EnvString(min_length=5)
    AFTER = EnvString()


class Empty(Section):
    pass


def pg_init(conf):
    postgres_pass = pg_pass("postgres", "postgres")

    return([
        (
            "postgres", "postgres",
            "ALTER ROLE postgres ENCRYPTED PASSWORD %s", (postgres_pass,),
        ),
    ])


def healthcheck(conf):
    dbname = "postgres"
    user = "postgres"
    password = "postgres"
    host = "127.0.0.1"
    psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
