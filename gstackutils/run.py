import os
import subprocess
import signal
import sys
from grp import getgrall as getgroups

from . import utils
from . import exceptions


def run(
    cmd,
    usr=None, grp=None,
    stopsignal=None,
    exit=False,
    silent=False,
    cwd=None,
    extraenv={}
):
    """Run a command."""
    usr = usr if usr is not None else 0
    grp = grp if grp is not None else usr

    try:
        pw = utils.uid(usr, all=True)
    except KeyError:
        raise exceptions.ImproperlyConfigured(f"User does not exist: {usr}")
    uid, uname, homedir = pw.pw_uid, pw.pw_name, pw.pw_dir

    try:
        gr = utils.gid(grp, all=True)
    except KeyError:
        raise exceptions.ImproperlyConfigured(f"Group does not exist: {grp}")
    gid = gr.gr_gid
    groups = [g.gr_gid for g in getgroups() if uname in g.gr_mem]

    def preexec_fn():  # pragma: no cover
        os.setgroups(groups)
        os.setgid(gid)
        os.setuid(uid)

    env = os.environ.copy()
    env["USER"] = env["USERNAME"] = uname
    env["HOME"] = homedir
    env["UID"] = str(uid)
    env["GID"] = str(gid)
    env.update(extraenv)

    sig = getattr(signal, stopsignal) if stopsignal else None

    proc = subprocess.Popen(
        cmd, preexec_fn=preexec_fn, env=env,
        stdout=subprocess.DEVNULL if silent else None,
        stderr=subprocess.DEVNULL if silent else None,
        start_new_session=True,  # CVE-2016-2779
    )

    original_sigterm_handler = signal.getsignal(signal.SIGTERM)
    original_sigint_handler = signal.getsignal(signal.SIGINT)

    def handler(signum, frame):
        proc.send_signal(sig if sig is not None else signum)

    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    returncode = proc.wait()
    signal.signal(signal.SIGTERM, original_sigterm_handler)
    signal.signal(signal.SIGINT, original_sigint_handler)

    if exit:
        sys.exit(returncode)
    return returncode
