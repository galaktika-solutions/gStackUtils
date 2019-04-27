import os
import pwd
import grp
import shutil
import hashlib
import re

import click

from .exceptions import ImproperlyConfigured


def env(var, env, default):
    return var if var is not None else os.environ.get(env, default)


def path_check(typ, path, uid=None, gid=None, mask=None, fix=False):
    if typ == "f" and not os.path.isfile(path):
        if fix:
            open(path, "w").close()
        else:
            raise ImproperlyConfigured(f"No such file: {path}")

    if typ == "d" and not os.path.isdir(path):
        if fix:
            os.makedirs(path)
        else:
            raise ImproperlyConfigured(f"No such directory: {path}")

    stat = os.stat(path)
    if uid is not None and stat.st_uid != uid:
        if not fix:
            msg = f"Must be owned by uid {uid}: {path}".format(uid, path)
            raise ImproperlyConfigured(msg)
        os.chown(path, uid, -1)
    if gid is not None and stat.st_gid != gid:
        if not fix:
            msg = f"Must be group owned by gid {gid}: {path}".format(gid, path)
            raise ImproperlyConfigured(msg)
        os.chown(path, -1, gid)
    if mask is not None and stat.st_mode & mask:
        if fix:
            os.chmod(path, stat.st_mode - (stat.st_mode & mask))
        else:
            msg = f"Wrong permissions ({stat.st_mode:o}): {path}"
            raise ImproperlyConfigured(msg)


def passwd(spec):
    if isinstance(spec, int):
        return pwd.getpwuid(spec)
    return pwd.getpwnam(spec)


def group(spec):
    if isinstance(spec, int):
        return grp.getgrgid(spec)
    return grp.getgrnam(str(spec))


def uid(spec):
    try:
        return int(spec)
    except ValueError:
        pw = pwd.getpwnam(spec)
        return pw.pw_uid


def gid(spec):
    try:
        return int(spec)
    except ValueError:
        gr = grp.getgrnam(str(spec))
        return gr.gr_gid


def cp(source, dest, _uid=-1, _gid=-1, mode=None, substitute=False):
    shutil.copyfile(source, dest)
    os.chown(dest, uid(_uid), gid(_gid))
    if mode is not None:
        os.chmod(dest, mode)
    if not substitute:
        return

    with open(dest, "r") as f:
        lines = f.readlines()

    newlines = []
    for l in lines:
        newline = l
        skipline = False
        for pattern in re.findall(r"\{\{.+\}\}", l):
            # not defined: default
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*\|\s*(.*?)\s*\}\}", pattern)
            if m:
                repl = os.environ.get(m.group(1))
                repl = repl if repl is not None else m.group(2)
                newline = newline.replace(pattern, repl)
            # not defined: remove line
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*-\s*\}\}", pattern)
            if m:
                repl = os.environ.get(m.group(1))
                if repl is None:
                    skipline = True
                    continue
                newline = newline.replace(pattern, repl)
            # not defined: delete
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*\}\}", pattern)
            if m:
                repl = os.environ.get(m.group(1))
                repl = repl if repl is not None else ""
                newline = newline.replace(pattern, repl)
        if not skipline:
            newlines.append(newline)

    with open(dest, "w") as f:
        f.writelines(newlines)


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def pg_pass(user, password):
    return f"md5{md5(password + user)}"


@click.group(name="helpers")
def cli():
    pass


@cli.command(name="cp")
@click.argument("source", type=click.Path(exists=True))
@click.argument("dest", type=click.Path())
@click.option("--uid", "-u")
@click.option("--gid", "-g")
@click.option("--mode", "-m")
@click.option("-s", "--substitute", is_flag=True)
def cp_cli(source, dest, uid, gid, mode, substitute):
    cp(source, dest, -1 if uid is None else uid, -1 if gid is None else gid, mode, substitute)
