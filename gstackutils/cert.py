import random
import os

from OpenSSL import crypto
from OpenSSL.SSL import FILETYPE_PEM

from . import exceptions


CERT_NOT_AFTER = 3 * 365 * 24 * 60 * 60


def make_cert(certname):
    cert = crypto.X509()
    cert.set_serial_number(random.randint(0, 2 ** 64 - 1))
    cert.get_subject().CN = certname

    cert.set_version(2)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(CERT_NOT_AFTER)
    return cert


def generate(names, ips=None, cakeyfile=None, cacertfile=None):
    ips = ips or []
    if cakeyfile is None and cacertfile:
        raise exceptions.InvalidUsage("cacertfile wihtout cakeyfile")

    os.chdir("/host")
    cn = names[0]

    if cakeyfile:
        with open(cakeyfile, "rb") as f:
            buf = f.read()
            cakey = crypto.load_privatekey(FILETYPE_PEM, buf)
    else:
        cakey = crypto.PKey()
        cakey.generate_key(crypto.TYPE_RSA, 2048)
        with open(f"{cn}_CA.key", "wb") as f:
            f.write(crypto.dump_privatekey(FILETYPE_PEM, cakey))

    if cacertfile:
        with open(cacertfile, "rb") as f:
            buf = f.read()
            cacert = crypto.load_certificate(FILETYPE_PEM, buf)
    else:
        cacert = make_cert(f"{cn}_CA")
        cacert.set_issuer(cacert.get_subject())
        cacert.set_pubkey(cakey)
        cacert.add_extensions([
            crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:0"),
            crypto.X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),
            crypto.X509Extension(b"subjectKeyIdentifier", False, b"hash", subject=cacert),
        ])
        cacert.sign(cakey, "sha256")
        with open(f"{cn}_CA.crt", "wb") as f:
            f.write(crypto.dump_certificate(FILETYPE_PEM, cacert))

    cakeypub = cakey.to_cryptography_key().public_key().public_numbers()
    cacertpub = cacert.get_pubkey().to_cryptography_key().public_numbers()
    if cakeypub != cacertpub:
        raise exceptions.InvalidUsage()

    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    with open(f"{cn}.key", "wb") as f:
        f.write(crypto.dump_privatekey(FILETYPE_PEM, key))

    req = crypto.X509Req()
    req.get_subject().CN = cn
    req.set_pubkey(key)
    req.sign(key, "sha256")

    cert = make_cert(cn)
    cert.set_issuer(cacert.get_subject())
    cert.set_pubkey(req.get_pubkey())

    altnames = [f"DNS:{n}" for n in names] + [f"IP:{i}" for i in ips]
    altnames = ",".join(altnames)
    cert.add_extensions([
        crypto.X509Extension(b'subjectAltName', False, altnames.encode()),
        crypto.X509Extension(b'extendedKeyUsage', False, b"serverAuth,clientAuth"),
    ])
    cert.sign(cakey, "sha256")
    with open(f"{cn}.crt", "wb") as f:
        f.write(crypto.dump_certificate(FILETYPE_PEM, cert))
