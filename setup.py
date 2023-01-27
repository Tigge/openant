#!/usr/bin/env python
#
# openant distutils setup script
#
# Copyright (c) 2012, Gustav Tiger <gustav@tiger.name>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import os
import shutil
import platform
import codecs

from distutils.util import execute
from distutils.cmd import Command
from subprocess import call
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools import setup, find_packages


def udev_reload_rules():
    call(["udevadm", "control", "--reload-rules"])


def udev_trigger():
    call(
        [
            "udevadm",
            "trigger",
            "--subsystem-match=usb",
            "--attr-match=idVendor=0fcf",
            "--action=add",
        ]
    )


def install_udev_rules(raise_exception):
    if check_root():
        shutil.copy("resources/42-ant-usb-sticks.rules", "/etc/udev/rules.d")
        execute(udev_reload_rules, (), "Reloading udev rules")
        execute(udev_trigger, (), "Triggering udev rules")
    else:
        msg = 'You must have root privileges to install udev rules. Run "sudo python setup.py udev_rules"'
        if raise_exception:
            raise OSError(msg)
        else:
            print(msg)


def check_root():
    return os.geteuid() == 0


def is_linux():
    return platform.system() == "Linux"


class InstallUdevRules(Command):
    description = "install udev rules (requires root privileges)"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        install_udev_rules(True)


class CustomInstall(install):
    def run(self):
        install.run(self)


class CustomDevelop(develop):
    def run(self):
        develop.run(self)


def read(rel_path):
    here = os.path.abspath(os.path.dirname(__file__))
    with codecs.open(os.path.join(here, rel_path), "r") as fp:
        return fp.read()


def get_version(rel_path):
    for line in read(rel_path).splitlines():
        if line.startswith("__version__"):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setup(
    name="openant",
    version=get_version("openant/__init__.py"),
    description="ANT, ANT-FS and ANT+ Python Library",
    long_description=open("README.md", "r").read(),
    long_description_content_type="text/markdown",
    author="Gustav Tiger, John Whittington",
    url="https://github.com/Tigge/openant",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Healthcare Industry",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Embedded Systems",
        "Environment :: Console",
    ],
    entry_points={"console_scripts": ["openant=openant.__init__:_main"]},
    packages=find_packages(exclude=["*test.*", "*tests"]),
    python_requires=">=3.7",
    install_requires=["pyusb>=1.0a2"],
    extras_require={
        "serial": ["pyserial"],
        "influx": ["influxdb-client"],
    },
    cmdclass={
        "udev_rules": InstallUdevRules,
        "install": CustomInstall,
        "develop": CustomDevelop,
    },
    test_suite="openant.tests",
)
