from gstackutils import conf, fields, validators, exceptions


# Config files
config_file = conf.File(path=".conf")
FILES = [config_file]


class EXAMPLE_CONFIG(conf.Section):
    """
    This is just an example of a config section.
    Keep it simple.
    """
    STRING = fields.StringField(
        config_file,
        default="default value",
        hide=False,
        services=[],
    )
    SECRET = fields.StringField(
        config_file,
        hide=True
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

def not_5(value):
    if str(value) and str(value)[0] == "5":
        raise exceptions.ValidationError("should not start with 5")


class ANOTHER(conf.Section):
    """
    Another section
    """
    B = fields.IntegerField(
        config_file,
        default=42,
        max_value=50,
        validators=(not_5,),
        help_text="An example number that should not be too big."
    )
    A = fields.StringField(
        config_file,
        b64=True,
        default="supersecret"
    )
    C = fields.StringListField(
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
    bool = fields.BooleanField(config_file)
    file = fields.FileField(config_file)
    email = fields.EmailField(config_file)
    iplist = fields.IPListField(config_file)
