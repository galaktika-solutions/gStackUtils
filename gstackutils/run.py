import os
import subprocess
import signal
import sys
from grp import getgrall as getgroups

from .helpers import passwd, group
from .exceptions import ImproperlyConfigured


def run(cmd, usr=0, grp=None, stopsignal=signal.SIGTERM, exit=True, silent=False):
    try:
        pw = passwd(usr)
    except KeyError:
        if isinstance(usr, int):
            # explicit user id without real user
            uid, uname, homedir = usr, None, None
            pw = None
        else:
            raise ImproperlyConfigured(f"User does not exist: {usr}")
    else:
        uid, uname, homedir = pw.pw_uid, pw.pw_name, pw.pw_dir

    if grp is not None:
        try:
            gr = group(grp)
        except KeyError:
            if isinstance(grp, int):
                gid, groups = grp, [grp]
                gr = None
        else:
            gid, groups = gr.gr_gid, [gr.gr_gid]
    elif pw:
        gr = group(pw.pw_gid)
        gid = gr.gr_gid
        groups = [g.gr_gid for g in getgroups() if uname in g.gr_mem]
    else:
        # No grp given and no user found
        gid, groups = uid, [uid]

    def preexec_fn():  # pragma: no cover
        os.setgroups(groups)
        os.setgid(gid)
        os.setuid(uid)

    env = os.environ.copy()
    if uname:
        env["USER"] = env["USERNAME"] = uname
    if homedir:
        env["HOME"] = homedir
    env["UID"] = str(uid)
    env["GID"] = str(gid)

    proc = subprocess.Popen(
        cmd, preexec_fn=preexec_fn, env=env,
        stdout=subprocess.DEVNULL if silent else None,
        stderr=subprocess.DEVNULL if silent else None,
    )

    def handler(signum, frame):
        proc.send_signal(stopsignal if stopsignal is not None else signum)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)

    returncode = proc.wait()
    if exit:
        sys.exit(returncode)
    return returncode
