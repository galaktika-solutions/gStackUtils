"""General utility functions."""

import os
import pwd
import grp
import shutil
import re

from . import exceptions


def _uidgid(spec, all, by_id_getter, by_name_getter, id_attr):
    try:
        spec = int(spec)
    except ValueError:
        pass

    if isinstance(spec, int):
        if not all:
            return spec
        record = by_id_getter(spec)
    else:
        record = by_name_getter(spec)

    return record if all else getattr(record, id_attr)


def uid(spec, all=False):
    """Get uid or passwd data based on the given spec.

    When no user found, ``KeyError`` will be raised. For special cases see below.

    :param spec: The username or uid. If this is an integer or a string that can be
                 converted to an integer the user does not have to exist.
    :param all:  If ``False``, only the uid will be returned, otherwise the whole passwd
                 record. In this case a non-existing uid will also reise an error.
    """
    return _uidgid(spec, all, pwd.getpwuid, pwd.getpwnam, "pw_uid")


def gid(spec, all=False):
    """Get gid or group data based on the given spec.

    Params and semantics are the same as with :meth:`uid`.
    """
    return _uidgid(spec, all, grp.getgrgid, grp.getgrnam, "gr_gid")


def path_check(
    path,
    usr=None, grp=None, mode=None,
    fix=False, allow_stricter=True, recursive=False
):
    """Check the existence, ownership and permissions of a file or directory.
    If the check fails it either fixes it or raises
    :exc:`gstackutils.exceptions.ImproperlyConfigured`.

    :param path:  The file to check. When ends with a slash (/), the directory to check.
    :param usr:   The user (for semantics see :meth:`uid`) the file should be owned by.
    :param grp:   The group (for semantics see :meth:`gid`) that should be the file's
                  group owner.
    :param mode:  The permission bits the file / directory must have. Should be
                  in the form 0x640.
    :param fix:   If ``True``, possible errors will be fixed by creating the file/directory,
                  modify it's owner/group and mode. if not run as root,
                  :exc:`gstackutils.exceptions.PermissionDenied` will be raised.
    :param allow_stricter: If ``True``, less permissive mode is considered OK. When fixing
                  permission bits will be disabled but not enabled.
    :param recursive: If ``True``, fixing directory ownership will be done recursively.
    """
    if fix and not os.getuid() == 0:
        raise exceptions.PermissionDenied("Only root can fix/create files and directories.")
    isdir = path.endswith("/")

    if not isdir and not os.path.isfile(path):
        if not fix:
            raise exceptions.ImproperlyConfigured(f"No such file: {path}")

        dirname = os.path.dirname("path")
        if dirname:
            os.makedirs(path)
        open(path, "w").close()
        usr = usr or 0  # when created, we can not leave as is...
        grp = grp or 0
        mode = mode or 0o600

    if isdir and not os.path.isdir(path):
        if not fix:
            raise exceptions.ImproperlyConfigured(f"No such directory: {path}")

        os.makedirs(path)
        usr = usr or 0  # when created, we can not leave as is...
        grp = grp or 0
        mode = mode or 0o755

    stat = os.stat(path)
    if usr is not None:
        _uid = uid(usr)
        if stat.st_uid != _uid:
            if fix:
                os.chown(path, _uid, -1)
                if recursive and isdir:
                    for root, dirs, files in os.walk(path):
                        for d in dirs:
                            os.chown(os.path.join(root, d), _uid, -1)
                        for f in files:
                            os.chown(os.path.join(root, f), _uid, -1)
            else:
                msg = (
                    f"The owner of {'directory' if isdir else 'file'} {path} "
                    f"must be {usr}."
                )
                raise exceptions.ImproperlyConfigured(msg)

    if grp is not None:
        _gid = gid(grp)
        if stat.st_gid != _gid:
            if fix:
                os.chown(path, -1, _gid)
                if recursive and isdir:
                    for root, dirs, files in os.walk(path):
                        for d in dirs:
                            os.chown(os.path.join(root, d), -1, _gid)
                        for f in files:
                            os.chown(os.path.join(root, f), -1, _gid)
            else:
                msg = (
                    f"The group owner of {'directory' if isdir else 'file'} {path} "
                    f"must be {grp}."
                )
                raise exceptions.ImproperlyConfigured(msg)

    if mode is not None:
        # print(f"{path}: mode is {oct(mode)}")
        st_mode = 0o777 & stat.st_mode
        if not allow_stricter:
            if mode != st_mode:
                if not fix:
                    msg = (
                        f"The {'directory' if isdir else 'file'} {path} "
                        f"has wrong permissions: {oct(st_mode)} "
                        f"(should be {oct(mode)})."
                    )
                    raise exceptions.ImproperlyConfigured(msg)
                os.chmod(path, mode)
        else:
            if st_mode & ~ mode:
                if not fix:
                    msg = (
                        f"The {'directory' if isdir else 'file'} {path} "
                        f"has wrong permissions: {oct(st_mode)} "
                        f"(should be more restrictive than {oct(mode)})."
                    )
                    raise exceptions.ImproperlyConfigured(msg)
                os.chmod(path, st_mode & mode)


def path_fix(path, usr=None, grp=None, mode=None):
    path_check(
        path,
        usr=usr, grp=grp, mode=mode,
        fix=True, recursive=True
    )


def cp(source, dest, substitute=False, env={}, usr=None, grp=None, mode=None):
    shutil.copyfile(source, dest)
    path_check(dest, usr=usr, grp=grp, mode=mode, fix=True, allow_stricter=False)

    if not substitute:
        return

    _env = os.environ.copy()
    _env.update(env)
    env = _env

    with open(dest, "r") as f:
        lines = f.readlines()

    newlines = []
    for l in lines:
        newline = l
        skipline = False
        for pattern in re.findall(r"\{\{.+?\}\}", l):
            # not defined: default
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*\|\s*(.*?)\s*\}\}", pattern)
            if m:
                repl = env.get(m.group(1))
                repl = str(repl) if repl is not None else m.group(2)
                newline = newline.replace(pattern, repl)
            # not defined: remove line
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*-\s*\}\}", pattern)
            if m:
                repl = env.get(m.group(1))
                if repl is None:
                    skipline = True
                    continue
                newline = newline.replace(pattern, str(repl))
            # not defined: delete
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*\}\}", pattern)
            if m:
                repl = env.get(m.group(1))
                repl = str(repl) if repl is not None else ""
                newline = newline.replace(pattern, repl)
        if not skipline:
            newlines.append(newline)

    with open(dest, "w") as f:
        f.writelines(newlines)


def pycclean():
    for root, dirs, files in os.walk("/src/"):
        for d in dirs:
            if d == "__pycache__":
                dir = os.path.join(root, d)
                shutil.rmtree(dir)


# def ask(
#     options=[], prompt='', default=None, multiple=False, marks=[]
# ):
#     """Asks the user to select one (or more) from a list of options."""
#
#     if not options:
#         raise ValueError('Nothing to choose from.')
#     options = [o if isinstance(o, tuple) else (o, o) for o in options]
#     if prompt:
#         click.echo(f"\n{prompt}\n", err=True)
#     else:
#         click.echo("", err=True)
#     for i, o in enumerate(options):
#         d = '•' if o[0] == default else ' '
#         m = '✓' if i in marks else ' '
#         click.echo(f"{i:>3} {m}{d} {o[1]}", err=True)
#     click.echo("", err=True)
#
#     while True:
#         length = len(options) - 1
#         if multiple:
#             msg = f'Enter selected numbers in range 0-{length}, separated by commas: '
#         else:
#             msg = f'Enter a number in range 0-{length}: '
#         click.echo(msg, err=True, nl=False)
#
#         try:
#             i = input()
#         except KeyboardInterrupt:
#             raise SystemExit()
#         if not i and default:
#             return default
#         try:
#             if multiple:
#                 return set([options[int(x)][0] for x in i.split(',')])
#             return options[int(i)][0]
#         except (ValueError, IndexError):
#             continue
