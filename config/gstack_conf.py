from gstackutils.conf import Section, EnvString, SecretString


class PYPI_CREDENTIALS(Section):
    PYPI_USERNAME = EnvString()
    PYPI_PASSWORD = SecretString(min_length=8)


class POSTGRES(Section):
    DB_PASSWORD_POSTGRES = SecretString(min_length=8)
    DB_PASSWORD_DJANGO = SecretString(min_length=8)
