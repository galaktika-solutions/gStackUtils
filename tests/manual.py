# import os
# import pick

# from gstackutils import conf


# os.environ["GSTACK_CONFIG_MODULE"] = "tests.fixtures.gstack_conf"

# config = conf.Config()

# # config.set("PYPI_USERNAME", "username")
# config.set("STRING", "Something")
# # config.set("FILE", open("tests/fixtures/duck.jpeg", "rb").read())
# # print(f"|{config.get('FILE')}|")
# config.inspect()

# print(pick.pick([str(i) for i in range(10)], title="Select one"))
# print(pick.pick([str(i) for i in range(100)], title="Select one", indicator="->"))
# print(pick.pick([str(i) for i in range(100)], title="Select more", multi_select=True))
