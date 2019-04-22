import os
import importlib
import time
import signal
import sys

import click
import psycopg2

from . import ImproperlyConfigured, DatabaseNotPresent
from .helpers import uid, gid, cp
from .run import run
from .conf import Config
from .helpers import env, pg_pass


def pg_init(conf):
    postgres_pass = pg_pass("postgres", conf.get("DB_PASSWORD_POSTGRES"))
    django_pass = pg_pass("django", conf.get("DB_PASSWORD_DJANGO"))

    return([
        (
            "postgres", "postgres",
            "ALTER ROLE postgres ENCRYPTED PASSWORD %s", (postgres_pass,),
        ),
        (
            "template1", "postgres",
            "CREATE EXTENSION unaccent; CREATE EXTENSION fuzzystrmatch", (),
        ),
        (
            "postgres", "postgres",
            "CREATE ROLE django", (),
        ),
        (
            "postgres", "postgres",
            "ALTER ROLE django ENCRYPTED PASSWORD %s LOGIN CREATEDB", (django_pass,),
        ),
        (
            "postgres", "django",
            "CREATE DATABASE django", (),
        ),
    ])


def healthcheck(conf):
    dbname = "django"
    user = "django"
    password = conf.get("DB_PASSWORD_DJANGO")
    host = "postgres"
    psycopg2.connect(dbname=dbname, user=user, password=password, host=host)


def ensure(pg_hba_orig=None, pg_conf_orig=None, pg_init_module=None, conf=None):
    pg_hba_orig = env(pg_hba_orig, "GSTACK_PG_HBA_ORIG", "config/pg_hba.conf")
    pg_conf_orig = env(pg_conf_orig, "GSTACK_PG_CONF_ORIG", "config/postgresql.conf")
    pg_init_module = env(pg_init_module, "GSTACK_PG_INIT_MODULE", "gstackutils.db")
    config = conf or Config()
    pgdata = os.environ.get('PGDATA')

    if not pgdata:
        raise ImproperlyConfigured("No PGDATA found in the environment.")

    os.makedirs(pgdata, exist_ok=True)
    os.chmod(pgdata, 0o700)
    os.chown(pgdata, uid("postgres"), gid("postgres"))

    pg_version = os.path.join(pgdata, "PG_VERSION")
    if not os.path.isfile(pg_version) or os.path.getsize(pg_version) == 0:
        run(usr="postgres", cmd=("initdb", ), silent=True)

    dest = os.path.join(pgdata, "pg_hba.conf")
    cp(pg_hba_orig, dest, "postgres", "postgres", 0o600)

    dest = os.path.join(pgdata, "postgresql.conf")
    cp(pg_conf_orig, dest, "postgres", "postgres", 0o600)

    # start postgres locally
    cmd = ("pg_ctl", "-o", "-c listen_addresses='127.0.0.1'", "-w", "start",)
    run(cmd, usr="postgres", silent=True)

    mod = importlib.import_module(pg_init_module)
    for dbname, user, sql, params in mod.pg_init(config):
        # click.echo(sql, nl=False)
        conn = psycopg2.connect(dbname=dbname, user=user, host="127.0.0.1")
        with conn:
            conn.autocommit = True
            with conn.cursor() as curs:
                try:
                    curs.execute(sql, params)
                except (
                    psycopg2.errors.DuplicateObject,
                    psycopg2.errors.DuplicateDatabase,
                ):
                    # click.echo(" duplicate")
                    pass
                # else:
                #     click.echo(" OK")
        conn.close()

    # stop the internally started postgres
    cmd = ("pg_ctl", "stop", "-s", "-w", "-m", "fast")
    run(cmd, usr="postgres")


def wait_for_db(timeout=10, pg_init_module=None, conf=None):
    pg_init_module = env(pg_init_module, "GSTACK_PG_INIT_MODULE", "gstackutils.db")
    mod = importlib.import_module(pg_init_module)
    healthcheck = mod.healthcheck
    config = conf or Config()
    stopped = [False]  # easier to use variable in the handler

    # we need a signal handling mechanism because:
    #   - pid 1 problem
    #   - psycopg2 does not play nicely with SIGINT
    original_sigterm_handler = signal.getsignal(signal.SIGTERM)
    original_sigint_handler = signal.getsignal(signal.SIGINT)

    def handler(signum, frame):
        stopped[0] = True

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    exitreason = "S"
    start = time.time()
    while not stopped[0]:
        try:
            healthcheck(config)
        except Exception as e:
            # print("healthcheck failed", str(e)[:20])
            now = time.time()
            if now - start > timeout:
                exitreason = "T"
                break
            time.sleep(0.5)
            continue
        else:
            # print("OK")
            exitreason = "O"
            break

    signal.signal(signal.SIGTERM, original_sigterm_handler)
    signal.signal(signal.SIGINT, original_sigint_handler)

    if exitreason == "T":
        raise DatabaseNotPresent()


@click.group(name="db")
def cli():
    pass


@cli.command(name="ensure")
def ensure_cli():
    ensure()


@cli.command(name="start")
def start_cli():
    ensure()
    run(["postgres"], usr="postgres", exit=True)


@cli.command(name="wait")
@click.option("--timeout", "-t", default=10)
def wait_cli(timeout):
    try:
        wait_for_db(timeout=timeout)
    except DatabaseNotPresent:
        sys.exit(1)
