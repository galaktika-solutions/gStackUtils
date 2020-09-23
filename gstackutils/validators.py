# import subprocess
# import os
import re
import datetime

from . import exceptions
from . import cert


class MinLengthValidator:
    def __init__(self, min=0):
        self.min = min

    def __call__(self, value):
        if len(value) < self.min:
            raise exceptions.ValidationError(
                f"value should not be shorter than {self.min}"
            )


class MaxLengthValidator:
    def __init__(self, max=0):
        self.max = max

    def __call__(self, value):
        if len(value) > self.max:
            raise exceptions.ValidationError(
                f"value should not be longer than {self.max}"
            )


class MinValueValidator:
    def __init__(self, min=0):
        self.min = min

    def __call__(self, value):
        if value < self.min:
            raise exceptions.ValidationError(
                f"value should not be lower than {self.min}"
            )


class MaxValueValidator:
    def __init__(self, max=0):
        self.max = max

    def __call__(self, value):
        if value > self.min:
            raise exceptions.ValidationError(
                f"value should not be greater than {self.min}"
            )


class LowercaseOnly:
    def __call__(self, value):
        if value.lower() != value:
            raise exceptions.ValidationError(
                f"only lowercase characters allowed"
            )


class HostNameValidator:
    host_re = (
        r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*"
        r"([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$"
    )

    def __init__(self, ip_ok=False):
        self.ip_ok = ip_ok

    def __call__(self, value):
        m = re.match(self.host_re, value)
        if not m:
            if self.ip_ok:
                try:
                    IPValidator()(value)
                except exceptions.ValidationError:
                    raise exceptions.ValidationError("invalid host name or IP")
            else:
                raise exceptions.ValidationError("invalid host name")


class IPValidator:
    ip_re = (
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}"
        r"([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$"
    )

    def __init__(self, range=False):
        self.range = range
        if range:
            self.ip_re = self.ip_re[:-1] + r"/(.+)$"

    def __call__(self, value):
        m = re.match(self.ip_re, value)
        if not m:
            raise exceptions.ValidationError(f"invalid IP{' range' if self.range else ''}")
        if self.range:
            try:
                r = int(m.group(4))
            except ValueError:
                raise exceptions.ValidationError("invalid IP range")
            if r < 1 or r > 32:
                raise exceptions.ValidationError("invalid IP range")


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

    def __call__(self, value):
        msg = "invalid e-mail address"
        if not re.match(self.VALID_ADDRESS_REGEXP, value[1]):
            raise exceptions.ValidationError(msg)


class CertificateExpiryValidator:
    def __call__(self, value):
        if cert.expiry(value) < datetime.datetime.utcnow():
            raise exceptions.ValidationError("certificate expired")
