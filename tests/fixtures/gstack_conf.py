from gstackutils.conf import Section, EnvString, SecretString


class First(Section):
    ANIMAL = EnvString(default="duck")
    SAIS = SecretString(default="quack", min_length=3, services={"test": []})
    TIMES = EnvString(min_length=5)
    AFTER = EnvString()


class Empty(Section):
    pass
