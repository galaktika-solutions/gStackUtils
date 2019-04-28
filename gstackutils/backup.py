# import importlib
import time
import os

import click

from .conf import Config
from .db import wait_for_db
from .helpers import env
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


def backup(
    dbformat="custom", files=True, conf=None, prefix=None, backup_dir=None,
    backup_uid=None, backup_gid=None, data_files_dir=None
):
    # print(dbformat, files)
    config = conf or Config()
    backup_dir = env(backup_dir, "GSTACK_BACKUP_DIR", "/host/backup")
    backup_uid = env(backup_uid, "GSTACK_BACKUP_UID", config.pu)
    backup_gid = env(backup_gid, ("GSTACK_BACKUP_GID", "GSTACK_BACKUP_UID"), config.pg)
    set_backup_perms(backup_dir, backup_uid, backup_gid)

    if dbformat:
        wait_for_db(conf=config)
        timestamp = time.strftime('%Y-%m-%d-%H-%M-%S', time.gmtime())
        prefix = env(prefix, "GSTACK_DB_BACKUP_PREFIX", config.get("HOST_NAME", default="backup"))
        filename = f"{prefix}-db-{timestamp}.backup"
        if dbformat == 'plain':
            filename += '.sql'
        filename = os.path.join(backup_dir, 'db', filename)
        cmd = ['pg_dump', '-v', '-F', dbformat, '-f', filename]
        run(cmd)

    if files:
        source = env(data_files_dir, "GSTACK_DATA_FILES_DIR", "/data/files")
        if source[-1] != '/':
            source += '/'
        cmd = [
            'rsync', '-v', '-a', '--delete', '--stats',
            source, os.path.join(backup_dir, 'files/')
        ]
        run(cmd)
    set_backup_perms(backup_dir, backup_uid, backup_gid)


@click.command(name="backup")
@click.option("--dbformat", "-d", type=click.Choice(["plain", "custom"]), default=None)
@click.option("--files", "-f", is_flag=True)
@click.option("--backupdir", "-b", type=click.Path(file_okay=False))
@click.option("--uid", "-u", type=int)
@click.option("--gid", "-g", type=int)
@click.option("--data-files-dir", type=click.Path(file_okay=False))
def cli(dbformat, files, backupdir, uid, gid, data_files_dir):
    backup(
        dbformat, files,
        backup_dir=backupdir, backup_uid=uid, backup_gid=gid,
        data_files_dir=data_files_dir,
    )
