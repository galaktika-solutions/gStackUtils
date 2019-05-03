# import importlib
import time
import os

import click

from .config import Config
from .db import wait_for_db
from .helpers import ask, uid, gid
from .run import run


def set_backup_perms(backup_dir, backup_uid, backup_gid):
    os.makedirs(os.path.join(backup_dir, 'db'), exist_ok=True)
    os.makedirs(os.path.join(backup_dir, 'files'), exist_ok=True)

    for root, dirs, files in os.walk(backup_dir):
        os.chown(root, backup_uid, backup_gid)
        os.chmod(root, 0o700)
        for f in files:
            path = os.path.join(root, f)
            os.chown(path, backup_uid, backup_gid)
            os.chmod(path, 0o600)
    os.chmod(backup_dir, 0o755)


def set_files_perms(data_files_dir):
    os.makedirs(data_files_dir, exist_ok=True)
    u, g = uid('django'), gid('nginx')
    for root, dirs, files in os.walk(data_files_dir):
        os.chown(root, u, g)
        os.chmod(root, 0o2750)
        for f in files:
            path = os.path.join(root, f)
            os.chown(path, u, g)
            os.chmod(path, 0o640)


def backup(
    dbformat="custom", files=True, conf=None, backup_dir=None,
    backup_uid=None, backup_gid=None, data_files_dir=None
):
    config = conf or Config()
    backup_dir = backup_dir or config.env("GSTACK_BACKUP_DIR", "/host/backup")
    backup_uid = backup_uid or config.env("GSTACK_BACKUP_UID", config.pu)
    backup_gid = backup_gid or config.env(("GSTACK_BACKUP_GID", "GSTACK_BACKUP_UID"), config.pg)
    set_backup_perms(backup_dir, backup_uid, backup_gid)

    if dbformat:
        wait_for_db(conf=config)
        timestamp = time.strftime('%Y-%m-%d-%H-%M-%S', time.gmtime())
        prefix = config.env("GSTACK_DB_BACKUP_PREFIX", "gstack")
        filename = f"{prefix}-db-{timestamp}.backup"
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
        run(cmd, extraenv=extraenv)

    if files:
        source = data_files_dir or config.env("GSTACK_DATA_FILES_DIR", "/data/files")
        if source[-1] != '/':
            source += '/'
        cmd = [
            'rsync', '-v', '-a', '--delete', '--stats',
            source, os.path.join(backup_dir, 'files/')
        ]
        run(cmd)
    set_backup_perms(backup_dir, backup_uid, backup_gid)


def restore(files, db_backup_file, conf=None, backup_dir=None, data_files_dir=None):
    config = conf or Config()
    backup_dir = backup_dir or config.env("GSTACK_BACKUP_DIR", "/host/backup")
    extraenv = {
        "PGHOST": "postgres",
        "PGUSER": "postgres",
        "PGDATABASE": "postgres",
        "PGPASSWORD": config.get("DB_PASSWORD_POSTGRES"),
    }

    if db_backup_file:
        wait_for_db(conf=config)
        db_backup_file = os.path.join(backup_dir, 'db', db_backup_file)
        if db_backup_file.endswith('.backup'):
            cmd = [
                'pg_restore', '-d', 'postgres', '--exit-on-error', '--verbose',
                '--clean', '--create', db_backup_file
            ]
            run(cmd, extraenv=extraenv)
        elif db_backup_file.endswith('.backup.sql'):
            cmd = [
                'psql', '-v', 'ON_ERROR_STOP=1',
                '-f', db_backup_file
            ]
            run(cmd, extraenv=extraenv)

    if files:
        data_files_dir = data_files_dir or config.env("GSTACK_DATA_FILES_DIR", "/data/files")
        cmd = [
            'rsync', '-v', '-a', '--delete', '--stats',
            os.path.join(backup_dir, 'files/'), data_files_dir
        ]
        run(cmd, log_command=True)
        set_files_perms(data_files_dir)


@click.command(name="backup")
@click.option("--dbformat", "-d", type=click.Choice(["plain", "custom"]))
@click.option("--files", "-f", is_flag=True)
@click.option("--backupdir", "-b", type=click.Path(file_okay=False))
@click.option("--uid", "-u", type=int)
@click.option("--gid", "-g", type=int)
@click.option("--data-files-dir", type=click.Path(file_okay=False))
def backup_cli(dbformat, files, backupdir, uid, gid, data_files_dir):
    backup(
        dbformat, files,
        backup_dir=backupdir, backup_uid=uid, backup_gid=gid,
        data_files_dir=data_files_dir,
    )


@click.command(name="restore")
@click.option("--files", "-f", is_flag=True)
@click.option("--db", "-d", is_flag=True)
@click.option("--db-backup-file", "-b")
@click.option("--backupdir", "-b", type=click.Path(file_okay=False))
@click.option("--data-files-dir", type=click.Path(file_okay=False))
def restore_cli(files, db, db_backup_file, backupdir, data_files_dir):
    config = Config()
    if db and db_backup_file is None:
        backupdir = backupdir or config.env("GSTACK_BACKUP_DIR", "/host/backup")
        db_backup_dir = os.path.join(backupdir, "db")
        entries = os.listdir(db_backup_dir)
        entries = sorted([
            e
            for e in entries
            if os.path.isfile(os.path.join(db_backup_dir, e))
        ])
        if len(entries) == 0:
            raise click.ClickException("No db backup files found.")
        if len(entries) == 1:
            a = ask(yesno=True, default="y", prompt=f"Is it OK to use file {entries[0]}?")
            if not a:
                raise click.Abort()
            db_backup_file = entries[0]
        else:
            db_backup_file = ask(entries, prompt='Which db backup file would you like to use?')
    restore(files, db_backup_file, conf=config, backup_dir=backupdir, data_files_dir=data_files_dir)
