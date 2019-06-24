import hashlib
import os
import sys
import signal
import time

import click
import psycopg2

from . import conf
from . import exceptions
from . import utils
from . import run


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def pg_pass(user, password):
    return f"md5{md5(password + user)}"


def ensure_postgres(actions=[], verbose=False):
    def echo(msg):
        if verbose:
            click.echo(f"{msg} ...", nl=False)

    def echodone(msg="OK"):
        if verbose:
            click.echo(f" {msg}")

    pg_hba_orig = "config/pg_hba.conf"
    pg_conf_orig = "config/postgresql.conf"
    pgdata = os.environ.get('PGDATA')

    if not pgdata:
        raise exceptions.ImproperlyConfigured("No PGDATA found in the environment.")

    echo(f"Checking PGDATA (={pgdata}) directory")
    os.makedirs(pgdata, exist_ok=True)
    os.chmod(pgdata, 0o700)
    os.chown(pgdata, utils.uid("postgres"), utils.gid("postgres"))
    echodone()

    pg_version = os.path.join(pgdata, "PG_VERSION")
    if not os.path.isfile(pg_version) or os.path.getsize(pg_version) == 0:
        echo("initdb")
        run.run(cmd=("initdb", ), usr="postgres", silent=True)
        echodone()

    echo("Copying config files")
    dest = os.path.join(pgdata, "pg_hba.conf")
    utils.cp(pg_hba_orig, dest)
    utils.path_check(
        dest, user="postgres", group="postgres", mask=0o600,
        fix=True, strict_mode=True
    )
    dest = os.path.join(pgdata, "postgresql.conf")
    utils.cp(pg_conf_orig, dest)
    utils.path_check(
        dest, user="postgres", group="postgres", mask=0o600,
        fix=True, strict_mode=True
    )
    echodone()

    # start postgres locally
    cmd = ("pg_ctl", "-o", "-c listen_addresses='127.0.0.1'", "-w", "start",)
    echo("Starting the database server locally")
    run.run(cmd, usr="postgres", silent=True)
    echodone()

    for action in actions:
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
    run.run(cmd, usr="postgres")
    echodone()


def db_healthcheck(config, verbose=False):
    host = "postgres"
    user = "django"
    password = config.get("DB_PASSWORD_DJANGO")
    dbname = "django"
    if verbose:
        print("trying to connect ... ", file=sys.stderr, flush=True, end="")
    try:
        psycopg2.connect(dbname=dbname, user=user, password=password, host=host)
    except Exception as e:
        if verbose:
            print(e, file=sys.stderr, flush=True, end="")
        raise
    else:
        if verbose:
            print("OK", file=sys.stderr, flush=True)


def wait_for_db(config=None, timeout=10, verbose=False):
    def echo(msg):
        if verbose:
            click.echo(f"{msg} ...")

    config = config or conf.Config()

    stopped = [False]  # easier to use in the handler

    # we need a signal handling mechanism
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
            db_healthcheck(config, verbose)
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
        raise Exception("Could not connect to the database.")
    elif exitreason == "S":
        raise SystemExit()
