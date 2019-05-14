import os
import subprocess
import signal
import sys
from grp import getgrall as getgroups

import click

from .helpers import passwd, group
from .exceptions import ImproperlyConfigured


def run(cmd, usr=0, grp=None, stopsignal=None, exit=False, silent=False, cwd=None, extraenv={}):
    """Run a command."""

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


@click.command(name="run")
@click.option('--user', '-u')
@click.option('--group', '-g')
@click.option('--silent', is_flag=True)
@click.option('--signal', '-s')
@click.argument("cmd", nargs=-1, required=True)
def run_cli(user, group, silent, signal, cmd):
    if user is not None:
        try:
            user = int(user)
        except ValueError:
            pass
    if group is not None:
        try:
            group = int(group)
        except ValueError:
            pass
    run(cmd, usr=user, grp=group, silent=silent, stopsignal=signal, exit=True)
