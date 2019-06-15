from gstackutils import conf
from gstackutils import fields


class COMPOSE_VARIABLES(conf.Section):
    COMPOSE_FILE = fields.StringField()
