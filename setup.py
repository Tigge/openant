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

from __future__ import absolute_import, print_function

import os
import shutil

from distutils.util import execute
from distutils.cmd import Command
from subprocess import call
from setuptools.command.install import install
from setuptools.command.develop import develop
from setuptools import setup, find_packages


def udev_reload_rules():
    call(["udevadm", "control", "--reload-rules"])


def udev_trigger():
    call(["udevadm", "trigger", "--subsystem-match=usb",
          "--attr-match=idVendor=0fcf", "--action=add"])

def install_udev_rules(raise_exception):
    if check_root():
        shutil.copy('resources/ant-usb-sticks.rules', '/etc/udev/rules.d')
        execute(udev_reload_rules, [], "Reloading udev rules")
        execute(udev_trigger, [], "Triggering udev rules")
    else:
        msg = "You must have root privileges to install udev rules. Run \"sudo python setup.py udev_rules\""
        if raise_exception:
            raise OSError(msg)
        else:
            print(msg)


def check_root():
    return os.geteuid() == 0


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
        install_udev_rules(True)


class CustomDevelop(develop):
    def run(self):
        develop.run(self)
        install_udev_rules(False)

try:
    with open('README.md') as file:
        long_description = file.read()
except IOError:
    long_description = ''

setup(name='openant',
      version='0.3',

      description='ANT and ANT-FS Python Library',
      long_description=long_description,

      author='Gustav Tiger',
      author_email='gustav@tiger.name',

      url='https://github.com/Tigge/openant',

      classifiers=['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Healthcare Industry',
                   'License :: OSI Approved :: MIT License',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.3',
                   'Programming Language :: Python :: 3.4',
                   'Programming Language :: Python :: 3.5',
                   'Topic :: Software Development :: Libraries :: Python Modules'
                  ],

      packages=find_packages(),

      install_requires=['pyusb>=1.0a2'],

      cmdclass={'udev_rules': InstallUdevRules, 'install': CustomInstall, 'develop': CustomDevelop},

      test_suite='ant.tests'
     )
