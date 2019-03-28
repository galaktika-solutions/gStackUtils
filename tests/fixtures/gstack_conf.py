from gstackutils.conf import Section, EnvString, SecretString


class First(Section):
    A = EnvString()
    C = EnvString()
    B = EnvString()


class Second(Section):
    X = EnvString()
    Y = EnvString()
    Z = SecretString()


class Third(Section):
    pass


class Fourth(Section):
    pass


class Fifth(Section):
    pass


class Sixth(Section):
    pass


class Seventh(Section):
    pass


class Eighth(Section):
    P = SecretString()
