import time
import os

import click

from .run import run
from .config import Config


def createcerts(names, ips=None, wd=None, silent=False, conf=None):
    """Generates certificates for development purposes.
    Commands run in the directory given by ``wd`` directory which must exist.
    The CN (common name) is the first item in ``names``.
    The following files will be created:

    - ``[CN]-ca-[timestamp].crt``: CA certificate
    - ``[CN]-[timestamp].key``: Private key
    - ``[CN]-[timestamp].crt``: Certificate

    :param [str] names: Names the certificate is valid for.
    :param [str] ips: IP addresses the certificate is valid for.
    :param path wd: Files will be created in this directory. If not given, the value
        of the environment variable ``GSTACK_CERT_DIR`` will be used if set.
        The default is ``/host``.
    """

    config = conf or Config()
    ips = ips or []
    cn = names[0]
    spec = ["DNS:%s" % n for n in names]
    spec += ["IP:%s" % i for i in ips]
    san = ",".join(spec)
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S", time.gmtime())
    ca_name = "%s-ca-%s" % (cn, timestamp)
    cert_name = "%s-%s" % (cn, timestamp)
    wd = wd or config.env("GSTACK_CERT_DIR", "/host")

    # generate CA private key
    run(["openssl", "genrsa", "-out", ca_name + ".key", "2048"], cwd=wd, silent=silent)
    # self signed CA certificate
    run(
        [
            "openssl", "req", "-x509", "-new", "-nodes",
            "-subj", "/commonName=%s" % ca_name,
            "-key", ca_name + ".key",
            "-sha256", "-days", "999999",
            "-out", ca_name + ".crt",
        ],
        cwd=wd,
        silent=silent,
    )
    # generate private key
    run(["openssl", "genrsa", "-out", cert_name + ".key", "2048"], cwd=wd, silent=silent)
    # certificate request
    with open("/etc/ssl/openssl.cnf", "r") as f:
        orig_conf = f.read()
    with open(os.path.join(wd, "openssl.cnf"), "w") as f:
        f.write(orig_conf)
        f.write("\n[SAN]\nsubjectAltName=%s\n" % san)
    run(
        [
            "openssl", "req", "-new", "-sha256",
            "-subj", "/commonName=%s" % cn,
            "-key", cert_name + ".key", "-reqexts", "SAN",
            "-out", cert_name + ".csr", "-config", "openssl.cnf",
        ],
        cwd=wd,
        silent=silent,
    )
    # sign the certificate with CA
    run(
        [
            "openssl", "x509", "-req", "-in", cert_name + ".csr",
            "-CA", ca_name + ".crt", "-CAkey", ca_name + ".key",
            "-out", cert_name + ".crt", "-days", "999999",
            "-sha256", "-extensions", "SAN", "-CAcreateserial", "-CAserial",
            ca_name + ".srl", "-extfile", "openssl.cnf",
        ],
        cwd=wd,
        silent=silent,
    )

    for f in (ca_name + ".srl", ca_name + ".key", "openssl.cnf", cert_name + ".csr"):
        os.remove(os.path.join(wd, f))

    stat = os.stat(".")
    for f in (cert_name + ".crt", cert_name + ".key", ca_name + ".crt"):
        os.chown(os.path.join(wd, f), stat.st_uid, stat.st_gid)


@click.command(name="cert")
@click.option(
    "--name", "-n", multiple=True,
    help="Name the generated certificate is valid for."
)
@click.option(
    "--ip", "-i", multiple=True,
    help="IP address the generated certificate is valid for."
)
@click.option('--silent', is_flag=True)
def cert_cli(name, ip, silent):
    """Generates certificates for development purposes."""

    if not name:
        raise click.ClickException("No name given.")
    createcerts(name, ips=ip, wd=os.getcwd(), silent=silent)
