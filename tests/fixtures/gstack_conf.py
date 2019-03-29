from gstackutils.conf import Section, EnvString, SecretString


class First(Section):
    ANIMAL = EnvString(default="duck")
    SAIS = SecretString(default="quack")
    TIMES = EnvString(min_length=5)
