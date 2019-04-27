import subprocess
import os

from .exceptions import ValidationError


class MinLengthValidator:
    def __init__(self, min_length):
        self.min_length = min_length

    def validate(self, config, value):
        if isinstance(value, (str, bytes)):
            if len(value) < self.min_length:
                raise ValidationError(
                    f"Too short ({len(value)} < {self.min_length})"
                )


class MaxLengthValidator:
    def __init__(self, max_length):
        self.max_length = max_length

    def validate(self, config, value):
        if isinstance(value, (str, bytes)):
            if len(value) > self.max_length:
                raise ValidationError(
                    f"Too long ({len(value)} > {self.max_length})."
                )


class TypeValidator:
    def __init__(self, typ):
        self.typ = typ

    def validate(self, config, value):
        if not isinstance(value, self.typ):
            raise ValidationError(
                f"Not of type {self.typ}"
            )


class PrivateKeyValidator:
    def validate(self, config, value):
        if not isinstance(value, bytes):
            return
        try:
            subprocess.run(
                ("openssl", "rsa", "-check"),
                input=value, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            raise ValidationError("Invalid private key")


class CertificateValidator:
    def __init__(self, getnamefor=None, getCA=None):
        self.getnamefor = getnamefor
        self.getCA = getCA

    def validate(self, config, value):
        if not isinstance(value, bytes):
            return

        namefor = None if self.getnamefor is None else self.getnamefor(config)
        CA = None if self.getCA is None else self.getCA(config)
        if CA:
            with open("/tmp/CA", "wb") as f:
                f.write(CA)

        cmd = ["openssl", "verify"]
        if CA:
            cmd += ["-CAfile", "/tmp/CA"]
        if namefor:
            cmd += ["-verify_hostname", namefor]

        try:
            subprocess.run(
                cmd,
                input=value, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            raise ValidationError("Invalid certificate")
        finally:
            try:
                os.remove("/tmp/CA")
            except FileNotFoundError:
                pass
