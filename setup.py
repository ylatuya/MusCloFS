import shutil
import shlex, subprocess

from setuptools import setup, find_packages
from setuptools.command.install import install as _install

setup(
    name = "MusCloFS",
    version = "0.1",
    packages = find_packages(),

    entry_points = {
        'console_scripts': [
            'musclofs = musclofs.musclofs:main',
        ],
    },

    # metadata for upload to PyPI
    author = "Andoni Morales",
    author_email = "ylatuya@gmail.com",
    description = "File System for Cloud Music",
    license = "MIT",
    url = "http://blog.ylatuya.es",
)
