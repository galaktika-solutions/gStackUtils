import hashlib


def md5(s):
    return hashlib.md5(s.encode()).hexdigest()


def pg_pass(user, password):
    return f"md5{md5(password + user)}"
