import random
import os
import datetime

from OpenSSL import crypto, SSL
import cryptography
import ssl


from . import exceptions


CERT_NOT_AFTER = 3 * 365 * 24 * 60 * 60


def consistent(key, cert):
    keypub = key.to_cryptography_key().public_key().public_numbers()
    certpub = cert.get_pubkey().to_cryptography_key().public_numbers()
    if keypub != certpub:
        return False
    return True


def get_alt_names(cert):
    crypt = cert.to_cryptography()
    sanlist = []
    for e in crypt.extensions:
        if isinstance(e.value, cryptography.x509.SubjectAlternativeName):
            for gn in e.value:
                if isinstance(gn, cryptography.x509.DNSName):
                    sanlist.append(("DNS", gn.value))
                elif isinstance(gn, cryptography.x509.IPAddress):
                    sanlist.append(("IP Address", str(gn.value)))
    return sanlist


def valid_for_name(name, cert):
    sanlist = get_alt_names(cert)
    try:
        ssl.match_hostname({"subjectAltName": sanlist}, name)
    except ssl.CertificateError:
        return False
    return True


def expiry(cert):
    return datetime.datetime.strptime(cert.get_notAfter().decode(), "%Y%m%d%H%M%SZ")


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
            cakey = crypto.load_privatekey(SSL.FILETYPE_PEM, buf)
    else:
        cakey = crypto.PKey()
        cakey.generate_key(crypto.TYPE_RSA, 2048)
        with open(f"{cn}_CA.key", "wb") as f:
            f.write(crypto.dump_privatekey(SSL.FILETYPE_PEM, cakey))

    if cacertfile:
        with open(cacertfile, "rb") as f:
            buf = f.read()
            cacert = crypto.load_certificate(SSL.FILETYPE_PEM, buf)
    else:
        # cacert = make_cert(f"{cn}_CA")
        cacert = make_cert(f"{cn}")
        cacert.set_issuer(cacert.get_subject())
        cacert.set_pubkey(cakey)
        cacert.add_extensions([
            crypto.X509Extension(b"basicConstraints", True, b"CA:TRUE, pathlen:0"),
            crypto.X509Extension(b"keyUsage", True, b"keyCertSign, cRLSign"),
            crypto.X509Extension(b"subjectKeyIdentifier", False, b"hash", subject=cacert),
        ])
        cacert.sign(cakey, "sha256")
        with open(f"{cn}_CA.crt", "wb") as f:
            f.write(crypto.dump_certificate(SSL.FILETYPE_PEM, cacert))

    if not consistent(cakey, cacert):
        raise exceptions.InvalidUsage("the CA private key and the certificate are not consistent")

    key = crypto.PKey()
    key.generate_key(crypto.TYPE_RSA, 2048)
    with open(f"{cn}.key", "wb") as f:
        f.write(crypto.dump_privatekey(SSL.FILETYPE_PEM, key))

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
        f.write(crypto.dump_certificate(SSL.FILETYPE_PEM, cert))
