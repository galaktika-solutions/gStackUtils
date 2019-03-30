from gstackutils.conf import Section, EnvString


class First(Section):
    ANIMAL = EnvString(default="duck")


class Empty(Section):
    ANIMAL = EnvString()
