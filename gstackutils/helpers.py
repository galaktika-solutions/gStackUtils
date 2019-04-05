import os
import pwd
import grp

from .exceptions import ImproperlyConfigured


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
