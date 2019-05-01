from gstackutils.config import Section
from gstackutils.fields import EnvString


class First(Section):
    ANIMAL = EnvString(default="duck")


class Empty(Section):
    ANIMAL = EnvString()
