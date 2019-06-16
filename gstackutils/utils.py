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


def path_check(path, user=None, group=None, mask=None, fix=False, strict_mode=False):
    """Check the existence, ownership and permissions of a file or directory.
    If the check fails it either fixes it or raises
    :exc:`gstackutils.exceptions.ImproperlyConfigured`.

    :param path:  The file to check. When ends with a slash (/), the directory to check.
    :param user:  The user (for semantics see :meth:`uid`) the file should be owned by.
    :param group: The group (for semantics see :meth:`gid`) that should be the file's
                  group owner.
    :param mask:  The most permissive mode setup the file can have. Should be
                  in the form 0x640.
    :param fix:   If ``True``, possible errors will be fixed by creating the file/directory,
                  modify it's owner/group and mode. if not run as root,
                  :exc:`gstackutils.exceptions.PermissionDenied` will be raised.
    :param strict_mode: It ``True`` mask will not restrict the permissions but set as is.
    """
    if fix and not os.getuid() == 0:
        raise exceptions.PermissionDenied("Only root can fix/create files and directories.")
    isdir = path.endswith("/")

    if not isdir and not os.path.isfile(path):
        if fix:
            try:
                open(path, "w").close()
            except FileNotFoundError as e:
                raise exceptions.ImproperlyConfigured(f"Could not create file: {path}")
            user = user or 0  # when created, we can not leave as is...
            group = group or 0
            mask = mask or 0o600
        else:
            raise exceptions.ImproperlyConfigured(f"No such file: {path}")

    if isdir and not os.path.isdir(path):
        if fix:
            os.makedirs(path)
            user = user or 0  # when created, we can not leave as is...
            group = group or 0
            mask = mask or 0o755
        else:
            raise exceptions.ImproperlyConfigured(f"No such directory: {path}")

    stat = os.stat(path)
    if user is not None:
        _uid = uid(user)
        if stat.st_uid != _uid:
            if fix:
                os.chown(path, _uid, -1)
            else:
                msg = (
                    f"The owner of {'directory' if isdir else 'file'} {path} "
                    f"must be {user}."
                )
                raise exceptions.ImproperlyConfigured(msg)

    if group is not None:
        _gid = gid(group)
        if stat.st_gid != _gid:
            if fix:
                os.chown(path, -1, _gid)
            else:
                msg = (
                    f"The group owner of {'directory' if isdir else 'file'} {path} "
                    f"must be {group}."
                )
                raise exceptions.ImproperlyConfigured(msg)

    st_mode = 0o777 if strict_mode else stat.st_mode
    if mask is not None and (st_mode & 0o777 & ~ mask):
        if fix:
            os.chmod(path, st_mode & mask)
        else:
            msg = (
                f"The {'directory' if isdir else 'file'} {path} "
                f"has wrong permissions: {oct(stat.st_mode & 0o777)} "
                f"(should be {oct(st_mode & mask)})."
            )
            raise exceptions.ImproperlyConfigured(msg)


def cp(source, dest, substitute=False, env={}):
    shutil.copyfile(source, dest)
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
                repl = repl if repl is not None else m.group(2)
                newline = newline.replace(pattern, repl)
            # not defined: remove line
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*-\s*\}\}", pattern)
            if m:
                repl = env.get(m.group(1))
                if repl is None:
                    skipline = True
                    continue
                newline = newline.replace(pattern, repl)
            # not defined: delete
            m = re.fullmatch(r"\{\{\s*([^-\s|]+)\s*\}\}", pattern)
            if m:
                repl = env.get(m.group(1))
                repl = repl if repl is not None else ""
                newline = newline.replace(pattern, repl)
        if not skipline:
            newlines.append(newline)

    with open(dest, "w") as f:
        f.writelines(newlines)


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
