import os
import importlib
import time

import click
import psycopg2

from . import ImproperlyConfigured, DatabaseNotPresent
from .helpers import uid, gid, cp
from .run import run
from .conf import Config


def fb(var, env, default):
    return var if var is not None else os.environ.get(env, default)


def ensure(pg_hba_orig=None, pg_conf_orig=None, pg_init_module=None):
    pg_hba_orig = fb(pg_hba_orig, "GSTACK_PG_HBA_ORIG", "config/pg_hba.conf")
    pg_conf_orig = fb(pg_conf_orig, "GSTACK_PG_CONF_ORIG", "config/postgresql.conf")
    pg_init_module = fb(pg_init_module, "GSTACK_PG_INIT_MODULE", "config.pg_init")
    config = Config()
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
                    pass
        conn.close()

    # stop the internally started postgres
    cmd = ("pg_ctl", "stop", "-s", "-w", "-m", "fast")
    run(cmd, usr="postgres")


def wait_for_db(timeout=10, pg_init_module=None):
    pg_init_module = fb(pg_init_module, "GSTACK_PG_INIT_MODULE", "config.pg_init")
    mod = importlib.import_module(pg_init_module)
    healthcheck = mod.healthcheck
    config = Config()

    start = time.time()
    while True:
        try:
            healthcheck(config)
        except Exception as e:
            print(e)
            now = time.time()
            if now - start > timeout:
                break
            time.sleep(1)
            continue
        else:
            print("OK")
            return
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
    wait_for_db(timeout=timeout)
