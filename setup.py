from setuptools import setup
import os
import io


here = os.path.abspath(os.path.dirname(__file__))

with io.open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = "\n" + f.read()

VERSION = "1.0.dev3"

setup(
    name="gstackutils",
    description="gstack - Docker Utilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    version=VERSION,
    url="https://github.com/galaktika-solutions/gstackutils",
    author="Richard Bann",
    author_email="richardbann@gmail.com",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Development Status :: 1 - Planning",
    ],
    license="MIT",
    packages=["gstackutils"],
    install_requires=[
        "click >= 7.0",
        "psycopg2-binary >= 2.8",
    ],
    extras_require={
        "dev": [
            "coverage >= 4.5.2",
            "sphinx >= 1.8.4",
            "sphinx_rtd_theme >= 0.4.2",
            "twine >= 1.12.1",
            "wheel >= 0.32.3",
            "django >= 2.2",
        ]
    },
    entry_points={
        "console_scripts": [
            "gstack=gstackutils.cli:cli",
        ]
    },
)
