from gstackutils import conf, fields, validators


# Config files
config_file = conf.File(path=".conf")
FILES = [config_file]


class EXAMPLE_CONFIG(conf.Section):
    STRING = fields.StringField(
        default="default value",
        file=config_file,
        hide=False,
        services=[],
    )
    HOST_NAMES = fields.StringListField(
        default=["gstack.localhost"],
        validators=(lambda x: [validators.HostNameValidator()(h) for h in x],),
        file=config_file,
        hide=False,
        services=[
            conf.Service("django", path="", user=0, group=0, mode=0o400),
            conf.Service("nginx", path="", user=0, group=0, mode=0o400),
            conf.Service("other", environ=True)
        ]
    )
