import subprocess
import os
import re

from .exceptions import ValidationError


class MinMaxLengthValidator:
    def __call__(self, field, value):
        if field.min_length and len(value) < field.min_length:
            raise ValidationError(
                f"Too short ({len(value)} < {field.min_length})"
            )
        if field.max_length and len(value) > field.max_length:
            raise ValidationError(
                f"Too long ({len(value)} > {field.max_length})."
            )


class MinMaxValueValidator:
    def __call__(self, field, value):
        if field.min_value is not None and value < field.min_value:
            raise ValidationError(
                f"Too small ({value} < {field.min_value})"
            )
        if field.max_value is not None and value > field.max_value:
            raise ValidationError(
                f"Too large ({value} > {field.max_value})."
            )


class TypeValidator:
    def __call__(self, field, value):
        if not isinstance(value, field.validate_type):
            raise ValidationError(
                f"Not of type {field.validate_type}"
            )


class HostNameValidator:
    host_re = (
        r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*"
        r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"
    )

    def __init__(self, ip_ok=False):
        self.ip_ok = ip_ok

    def __call__(self, field, value):
        m = re.match(self.host_re, value)
        if not m:
            if self.ip_ok:
                try:
                    IPValidator()(value)
                except ValidationError:
                    raise ValidationError("Invalid host name or IP.")
            else:
                raise ValidationError("Invalid host name.")


class IPValidator:
    ip_re = (
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}"
        r"([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
    )

    def __init__(self, range=False):
        self.range = range
        if range:
            self.ip_re = self.ip_re[:-1] + r"/(.+)$"

    def __call__(self, field, value):
        m = re.match(self.ip_re, value)
        if not m:
            raise ValidationError(f"Invalid IP{' range' if self.range else ''}.")
        if self.range:
            try:
                r = int(m.group(4))
            except ValueError:
                raise ValidationError("Invalid IP range.")
            if r < 1 or r > 32:
                raise ValidationError("Invalid IP range.")


class EmailValidator:
    # see 2.2.2. Structured Header Field Bodies
    WSP = r'[\s]'
    # see 2.2.3. Long Header Fields
    CRLF = r'(?:\r\n)'
    # see 3.2.1. Primitive Tokens
    NO_WS_CTL = r'\x01-\x08\x0b\x0c\x0f-\x1f\x7f'
    # see 3.2.2. Quoted characters
    QUOTED_PAIR = r'(?:\\.)'
    # see 3.2.3. Folding white space and comments
    FWS = r'(?:(?:' + WSP + r'*' + CRLF + r')?' + WSP + r'+)'
    # see 3.2.3
    CTEXT = r'[' + NO_WS_CTL + r'\x21-\x27\x2a-\x5b\x5d-\x7e]'
    # see 3.2.3 (NB: The RFC includes COMMENT here
    CCONTENT = r'(?:' + CTEXT + r'|' + QUOTED_PAIR + r')'
    # see 3.2.3
    COMMENT = r'\((?:' + FWS + r'?' + CCONTENT + r')*' + FWS + r'?\)'
    # see 3.2.3
    CFWS = r'(?:' + FWS + r'?' + COMMENT + ')*(?:' + FWS + '?' + COMMENT + '|' + FWS + ')'
    # see 3.2.4. Atom
    ATEXT = r'[\w!#$%&\'\*\+\-/=\?\^`\{\|\}~]'
    ATOM = CFWS + r'?' + ATEXT + r'+' + CFWS + r'?'       # see 3.2.4
    DOT_ATOM_TEXT = ATEXT + r'+(?:\.' + ATEXT + r'+)*'    # see 3.2.4
    DOT_ATOM = CFWS + r'?' + DOT_ATOM_TEXT + CFWS + r'?'  # see 3.2.4
    # see 3.2.5. Quoted strings
    QTEXT = r'[' + NO_WS_CTL + r'\x21\x23-\x5b\x5d-\x7e]'
    QCONTENT = r'(?:' + QTEXT + r'|' + QUOTED_PAIR + r')'  # see 3.2.5
    QUOTED_STRING = (
        CFWS + r'?' + r'"(?:' + FWS + r'?' + QCONTENT + r')*' +
        FWS + r'?' + r'"' + CFWS + r'?'
    )
    # see 3.4.1. Addr-spec specification
    LOCAL_PART = r'(?:' + DOT_ATOM + r'|' + QUOTED_STRING + r')'
    DTEXT = r'[' + NO_WS_CTL + r'\x21-\x5a\x5e-\x7e]'    # see 3.4.1
    DCONTENT = r'(?:' + DTEXT + r'|' + QUOTED_PAIR + r')'  # see 3.4.1
    # see 3.4.1
    DOMAIN_LITERAL = (
        CFWS + r'?' + r'\[' + r'(?:' + FWS + r'?' + DCONTENT + r')*' +
        FWS + r'?\]' + CFWS + r'?'
    )
    DOMAIN = r'(?:' + DOT_ATOM + r'|' + DOMAIN_LITERAL + r')'   # see 3.4.1
    ADDR_SPEC = LOCAL_PART + r'@' + DOMAIN               # see 3.4.1
    # A valid address will match exactly the 3.4.1 addr-spec.
    VALID_ADDRESS_REGEXP = '^' + ADDR_SPEC + '$'

    def __call__(self, field, value):
        msg = "Invalid e-mail address"
        if not re.match(self.VALID_ADDRESS_REGEXP, value[1]):
            raise ValidationError(msg)


class PrivateKeyValidator:
    def __call__(self, field, value):
        try:
            subprocess.run(
                ("openssl", "rsa", "-check"),
                input=value, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        except subprocess.CalledProcessError:
            raise ValidationError("Invalid private key")


class CertificateValidator:
    pk = "\n".join([
        "-----BEGIN RSA PRIVATE KEY-----",
        "MIIEoQIBAAKCAQEApccLW73hr+fG7TS8jcXHN6Z63Y2HTFzZiD82KcsLqTVOo7FI",
        "3yKJic5WUsS2F2/kvf653DygUnSGgT0n59zVZVeHjWI364Z8RrPobHH4m6vkeIKc",
        "pjkvQHzFCnY28/iOgjEHpiE/YuEuHvyQdqFyDaefettV2oygyPBIDe9+GKJTSNpt",
        "IzpjvocWR9poDpAE7BqhKygULGBxe43bolSEKuU8po2PZylmUw56+pT002bs2LNo",
        "uTd0PV9tM0I+4O8nFSvbkTqEYUAFzl/fMByWZmPmS9EWwcvUxg/0cUlMjfHzGeBK",
        "UlUHT/pT2MUp/ieoNqC6llJA3fKGAbczn8TkdwIDAQABAoIBAE1mpNf9zQz7c7a2",
        "475x9HT4Ru+AsAYoZ+ykTt6ujdBAMmpdUP/VuU/dRhK5A6fnt246K38300cMXuyi",
        "qCoqwnvhpUmO7TsLfKTqRP+1KvVMCY12tjsqAfTjDIC49ylsCOWijMa1SUoahxUy",
        "qSSqdn0HoX+UPv6eoEeRYKMZCc/n4gPP/6JOdk5s4E6FPnZLUTxab3i2+k/E7xN+",
        "fumfLYXD0i+09x7CEQUSqzJ4tz3RrhkKIq6hcH3OiVy5jWLqZgEmzcFQc6QhFDVa",
        "7hGtu5LgZP3psKbve+h2VjRgTmjq0JzC2TRO0iinJcQdGbx2/CD+xldGDzwt71BR",
        "6QJ2ifkCgYEA0UOUL0MkoVhaLLuz0CjKUEeOgWoDNhc86QVxm150FZa5SA2LPeG+",
        "L6Zk/Ln4C8b+67TGApTIxTxja21TWDGaEGgWIK5ENNyyiH3j1SqBkBhuMf9NIXyj",
        "FsRU+/w0i5UsseKbSahmO/2F0Q/3tMpYHiTqljhT/hx2Rvytf0sqwbsCgYEAys0t",
        "pkJJpFcKD4KmgXJAoIZMMLp46j2r4TUVMeHsZyRC6beUBM38hWZpuRuo5tGM0z7H",
        "+pqhVyfhCFjN2FDpimcAifwRUT6nmzH0bSyNYq4SayIVldbMXxEMBqHaaLsM8Ocx",
        "JC1opTFluWFuCqUGjzbxONKD92x7gXzZgOQ0bnUCf0CTmib7kVI48ZrcUaDq9YPQ",
        "kSlejZ8jjKhcBbLscuY2nPafN1jhUM9jicZznRgFUKVsI66oO0yiVgvQsOeGZwSp",
        "Gir7nBC0CmQUdTpS46iT4W2MW0D6NVnRPGiGa7CnWCOMyl7wmJvqoGDjjI094/Np",
        "cPrqZwEDx3wgfWnKyGcCgYAJEeIPxHksq2Pcy7gMpAJ162uu5jgQKc/tE4WuJG+B",
        "MWL4tugcyuWXRbxGthD4ubh1niIteArtLfBngik6mmvHb9HbWfWgT5AJZdOLqmls",
        "V2KlffG/MMsVGVsTVNvCwVLT11MgThOXB72H6+6S9Ux0zT0+kFOsliJz6RSFKi+a",
        "HQKBgQCW2nS3yXutQPj1Q3Tl7YgcoIWmuLevuSfeFTIkyLTznLL0T0xJYeM75l8T",
        "Psbb120r6qDFLfD0hxL+WooZMGDSLwGCAhQ/bV5Mx0LKgaoG8bqXsKvav2PQz4Xx",
        "+ZKtMQoi71RvdWjOPwQDGx8091xBhMGPmTm4T09s1Ztg71kkVg==",
        "-----END RSA PRIVATE KEY-----",
    ])

    def __call__(self, field, value):
        try:
            name = None if field.getname is None else field.getname(field.config)
        except Exception:
            raise ValidationError("Unable to get name for validation.")
        if name:
            with open("/tmp/pk", "w") as f:
                f.write(self.pk)
            cmd = ("openssl", "x509", "-out", "/tmp/selfsigned", "-signkey", "/tmp/pk")
            subprocess.run(
                cmd,
                input=value, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            try:
                cmd = (
                    "openssl", "verify", "-verify_hostname", name,
                    "-CAfile", "/tmp/selfsigned", "/tmp/selfsigned"
                )
                subprocess.run(
                    cmd,
                    input=value, check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError:
                raise ValidationError(f"Certificate not valid for name {name}")
            finally:
                for f in ["/tmp/pk", "/tmp/selfsigned"]:
                    try:
                        os.remove(f)
                    except FileNotFoundError:
                        pass

        try:
            ca = None if field.getca is None else field.getca(field.config)
        except Exception:
            raise ValidationError("Unable to get CA for validation.")
        if ca:
            with open("/tmp/ca", "wb") as f:
                f.write(ca)
            cmd = ["openssl", "verify"]
            if field.getca:
                cmd += ["-CAfile", "/tmp/ca"]
            try:
                subprocess.run(
                    cmd,
                    input=value, check=True,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            except subprocess.CalledProcessError:
                raise ValidationError("Certificate not trusted")
            finally:
                try:
                    os.remove("/tmp/ca")
                except FileNotFoundError:
                    pass
