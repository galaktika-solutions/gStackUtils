from gstackutils import conf
from gstackutils import fields

from gstackutils.config_module import *  # noqa


class PYPI_CREDENTIALS(conf.Section):
    PYPI_USERNAME = fields.StringField()
    PYPI_PASSWORD = fields.StringField(secret=True, min_length=12)

    main = conf.Service(PYPI_PASSWORD=1000)


class MAIL(conf.Section):
    SENDGRID_API_KEY = fields.StringField(secret=True)

    django = conf.Service(SENDGRID_API_KEY="django")
