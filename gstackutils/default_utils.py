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


def ensure_postgres(config, actions=[], verbose=False, cpenv={}):
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
    utils.cp(pg_hba_orig, dest, usr="postgres", grp="postgres", mode=0o600)
    dest = os.path.join(pgdata, "postgresql.conf")
    utils.cp(
        pg_conf_orig, dest, usr="postgres", grp="postgres", mode=0o600,
        substitute=True,
        # env={"LOG_FILE_MODE": "0644" if config.is_dev else "0600"},
        env=cpenv,
    )
    echodone()

    # start postgres locally
    cmd = ("pg_ctl", "-o", "-c listen_addresses='127.0.0.1'", "-w", "start",)
    echo("Starting the database server locally")
    # run.run(cmd, usr="postgres", silent=True)
    run.run(cmd, usr="postgres")
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
        psycopg2.connect(
            dbname=dbname, user=user, password=password, host=host, connect_timeout=1
        )
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


def set_backup_perms(config):
    """Set the owner and permission of the backup directory recursively."""

    backup_dir = "/host/backup/"
    backup_uid = config.get("BACKUP_UID")
    backup_gid = config.get("BACKUP_GID")

    os.makedirs(os.path.join(backup_dir, 'db'), exist_ok=True)
    os.makedirs(os.path.join(backup_dir, 'files'), exist_ok=True)

    for root, dirs, files in os.walk(backup_dir):
        os.chown(root, backup_uid, backup_gid)
        os.chmod(root, 0o755)
        for f in files:
            path = os.path.join(root, f)
            os.chown(path, backup_uid, backup_gid)
            os.chmod(path, 0o600)
    os.chmod(backup_dir, 0o755)


def set_files_perms():
    """Set the owner and permissions of the data files directory recursively.

    See Django settings FILE_UPLOAD_DIRECTORY_PERMISSIONS and FILE_UPLOAD_PERMISSIONS.
    Also note the 0o2755 mode (setgid bit): the group of the files created inside this
    directory will not be that of the user who created them, but that of the parent
    directory.
    """

    data_files_dir = "/data/files/"
    os.makedirs(data_files_dir, exist_ok=True)
    u, g = utils.uid('django'), utils.gid('nginx')
    for root, dirs, files in os.walk(data_files_dir):
        os.chown(root, u, g)
        os.chmod(root, 0o2750)
        for f in files:
            path = os.path.join(root, f)
            os.chown(path, u, g)
            os.chmod(path, 0o640)


def backup(dbformat="custom", files=True, config=None):
    config = config or conf.Config()
    backup_dir = "/host/backup/"
    data_files_dir = "/data/files/"
    set_backup_perms(config)

    if dbformat:
        wait_for_db(config=config)
        timestamp = time.strftime('%Y-%m-%d-%H-%M-%S', time.gmtime())
        filename = f"db-{timestamp}.backup"
        if dbformat == 'plain':
            filename += '.sql'
        filename = os.path.join(backup_dir, 'db', filename)
        cmd = ['pg_dump', '-v', "--clean", "--create", '-F', dbformat, '-f', filename]
        extraenv = {
            "PGHOST": "postgres",
            "PGUSER": "postgres",
            "PGDATABASE": "django",
            "PGPASSWORD": config.get("DB_PASSWORD_POSTGRES"),
        }
        run.run(cmd, extraenv=extraenv)

    if files:
        set_files_perms()
        cmd = [
            'rsync', '-v', '-a', '--delete', '--stats',
            data_files_dir, os.path.join(backup_dir, 'files/')
        ]
        run.run(cmd)
    set_backup_perms(config)


def restore(dumpfile=None, files=True, config=None):
    config = config or conf.Config()
    backup_dir = "/host/backup/"
    data_files_dir = "/data/files/"
    root = "/host"
    extraenv = {
        "PGHOST": "postgres",
        "PGUSER": "postgres",
        "PGDATABASE": "postgres",
        "PGPASSWORD": config.get("DB_PASSWORD_POSTGRES"),
    }

    if dumpfile:
        dumpfile = os.path.join(root, dumpfile)
        if not os.path.isfile(dumpfile):
            raise exceptions.InvalidUsage("The dumpfile argument is invalid")

        if dumpfile.endswith('.backup'):
            cmd = [
                'pg_restore', '-d', 'postgres', '--exit-on-error', '--verbose',
                '--clean', '--create', dumpfile
            ]
            run.run(cmd, extraenv=extraenv)
        elif dumpfile.endswith('.backup.sql'):
            cmd = [
                'psql', '-v', 'ON_ERROR_STOP=1',
                '-f', dumpfile
            ]
            run.run(cmd, extraenv=extraenv)
        else:
            raise exceptions.InvalidUsage("Not a valid dump file")

    if files:
        cmd = [
            'rsync', '-v', '-a', '--delete', '--stats',
            os.path.join(backup_dir, 'files/'), data_files_dir
        ]
        run.run(cmd)
        set_files_perms()
