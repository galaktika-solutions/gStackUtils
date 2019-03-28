import re
import os
import base64


class BaseEnvFileStorage:
    ENV_REGEX = re.compile(r"^\s*([^#].*?)=(.*)$")

    def __init__(self, filepath):
        self.filepath = filepath

    def _set_delete(self, name, value: str=None):
        newlines = []
        done = False
        with open(self.filepath, "r") as f:
            lines = f.readlines()
        for l in lines:
            if done:  # if we are done, just append remaining lines
                newlines.append(l)
                continue
            m = self.ENV_REGEX.match(l)
            if m and m.group(1) == name:
                done = True
                if value is not None:  # if we delete, leave this line alone
                    newlines.append("{}={}\n".format(name, value))
            else:
                newlines.append(l)
        if not done and value is not None:
            newlines.append("{}={}\n".format(name, value))
        with open(self.filepath, "w") as f:
            f.writelines(newlines)

    def _read(self, name):
        with open(self.filepath, "r") as f:
            for l in f.readlines():
                m = self.ENV_REGEX.match(l)
                if m and m.group(1) == name:
                    return m.group(2)
        return None

    def delete(self, name: str) -> None:
        self._set_delete(name)


class EnvFileStorage(BaseEnvFileStorage):
    def read(self, name):
        ret = super()._read(name)
        return None if ret is None else ret.encode()

    def write(self, name, value):
        self._set_delete(name, value.decode())


class SecretFileStorage(BaseEnvFileStorage):
    def read(self, name):
        ret = super()._read(name)
        return None if ret is None else base64.b64decode(ret)

    def write(self, name, value):
        v = base64.b64encode(value)
        self._set_delete(name, v.decode())


class EnvVarStorage:
    def read(self, name):
        ret = os.environ.get(name)
        return None if ret is None else ret.encode()

    def write(self, name, value):
        os.environ[name] = value.decode()

    def delete(self, name: str) -> None:
        del os.environ[name]


class SecretStorage:
    def __init__(self, dir):
        self.dir = dir

    def read(self, name):
        fn = os.path.join(self.dir, name)
        try:
            with open(fn, "rb") as f:
                return f.read()
        except (FileNotFoundError, PermissionError):
            return None

    def write(self, name, value, uid=0, gid=0, mode=0o400):
        fn = os.path.join(self.dir, name)
        with open(fn, "wb") as f:
            f.write(value)
        os.chown(fn, uid, gid)
        os.chmod(fn, mode)

    def delete(self, name: str) -> None:
        fn = os.path.join(self.dir, name)
        os.remove(fn)
