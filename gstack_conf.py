from gstackutils.conf import Section, EnvString, SecretString


class PYPI_CREDENTIALS(Section):
    PYPI_USERNAME = EnvString()
    PYPI_PASSWORD = SecretString(min_length=8)
