from gstackutils import conf, fields, validators


# Config files
config_file = conf.File(path=".conf")
FILES = [config_file]


class EXAMPLE_CONFIG(conf.Section):
    STRING = fields.StringField(
        config_file,
        default="default value",
        hide=False,
        services=[],
    )
    SECRET = fields.StringField(
        config_file,
        hide=True,
        default="supersecret"
    )
    HOST_NAMES = fields.StringListField(
        config_file,
        default=["gstack.localhost"],
        min_items=3,
        validators=(validators.HostNameValidator(),),
        hide=False,
        services=[
            conf.Service("django", path="", user=0, group=0, mode=0o400),
            conf.Service("nginx", path="", user=0, group=0, mode=0o400),
            conf.Service("other", environ=True)
        ]
    )
