import os
import time
import signal

import click
import psycopg2

from .exceptions import ImproperlyConfigured, DatabaseNotPresent
from .helpers import uid, gid, cp
from .run import run
from .config import Config


def ensure(conf=None, verbose=False):
    def echo(msg):
        if verbose:
            click.echo(f"{msg} ...", nl=False)

    def echodone(msg="OK"):
        if verbose:
            click.echo(f" {msg}")

    config = conf or Config()
    pg_hba_orig = config.env("GSTACK_PG_HBA_ORIG", "config/pg_hba.conf")
    pg_conf_orig = config.env("GSTACK_PG_CONF_ORIG", "config/postgresql.conf")
    pgdata = os.environ.get('PGDATA')

    if not pgdata:
        raise ImproperlyConfigured("No PGDATA found in the environment.")

    echo(f"Checking PGDATA (={pgdata}) directory")
    os.makedirs(pgdata, exist_ok=True)
    os.chmod(pgdata, 0o700)
    os.chown(pgdata, uid("postgres"), gid("postgres"))
    echodone()

    pg_version = os.path.join(pgdata, "PG_VERSION")
    if not os.path.isfile(pg_version) or os.path.getsize(pg_version) == 0:
        echo("initdb")
        run(usr="postgres", cmd=("initdb", ), silent=True)
        echodone()

    echo("Copying config files")
    dest = os.path.join(pgdata, "pg_hba.conf")
    cp(pg_hba_orig, dest, "postgres", "postgres", 0o600)

    dest = os.path.join(pgdata, "postgresql.conf")
    cp(pg_conf_orig, dest, "postgres", "postgres", 0o600)
    echodone()

    # start postgres locally
    cmd = ("pg_ctl", "-o", "-c listen_addresses='127.0.0.1'", "-w", "start",)
    echo("Starting the database server locally")
    run(cmd, usr="postgres", silent=True)
    echodone()

    if hasattr(config.config_module, "pg_init"):
        _pg_init = config.config_module.pg_init
    else:
        from . import default_gstack_conf
        _pg_init = default_gstack_conf.pg_init
    for action in _pg_init(config):
        dbname = action.get("dbname", "postgres")
        user = action.get("user", "postgres")
        sql = action["sql"]
        params = action.get("params", ())
        echo(f"Running SQL in db {dbname} with user {user}: {sql}")
        conn = psycopg2.connect(dbname=dbname, user=user, host="127.0.0.1")
        with conn:
            conn.autocommit = True
            with conn.cursor() as curs:
                try:
                    curs.execute(sql, params)
                except (
                    psycopg2.errors.DuplicateObject,
                    psycopg2.errors.DuplicateDatabase,
                    psycopg2.errors.DuplicateSchema,
                ):
                    echodone("OK (existed)")
                else:
                    echodone()
        conn.close()

    # stop the internally started postgres
    cmd = ("pg_ctl", "stop", "-s", "-w", "-m", "fast")
    echo("Stopping the server")
    run(cmd, usr="postgres")
    echodone()


def wait_for_db(timeout=10, conf=None, verbose=False):
    # print("xxx", verbose)
    def echo(msg):
        if verbose:
            click.echo(f"{msg} ...")

    config = conf or Config()
    if hasattr(config.config_module, "healthcheck"):
        _healthcheck = config.config_module.healthcheck
    else:
        from . import default_gstack_conf
        _healthcheck = default_gstack_conf.healthcheck
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
        # echo("trying to connect")
        try:
            _healthcheck(config, verbose)
        except Exception as e:
            now = time.time()
            if now - start > timeout:
                exitreason = "T"
                echo("timeout")
                break
            time.sleep(0.5)
            continue
        else:
            exitreason = "O"
            echo("OK")
            break

    signal.signal(signal.SIGTERM, original_sigterm_handler)
    signal.signal(signal.SIGINT, original_sigint_handler)

    if exitreason == "T":
        raise DatabaseNotPresent()
    elif exitreason == "S":
        raise SystemExit()
