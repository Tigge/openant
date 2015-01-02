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

from distutils.core import setup
from distutils.command.install import install
from distutils.util import execute
from subprocess import call

def udev_reload_rules():
    call(["udevadm", "control", "--reload-rules"])

def udev_trigger():
    call(["udevadm", "trigger", "--subsystem-match=usb", 
          "--attr-match=idVendor=0fcf", "--action=add"])


class CustomInstall(install):
    def run(self):
        install.run(self)

        execute(udev_reload_rules, [], "Reloading udev rules")
        execute(udev_trigger, [], "Triggering udev rules")

setup(name='openant',
      version='0.2',

      description='ANT and ANT-FS Python Library',
      long_description=open('README.md').read(),

      author='Gustav Tiger',
      author_email='gustav@tiger.name',

      url='http://www.github.com/Tigge/openant',

      classifiers=['Development Status :: 4 - Beta',
                   'Intended Audience :: Developers',
                   'Intended Audience :: Healthcare Industry',
                   'License :: OSI Approved :: MIT License',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.3',
                   'Programming Language :: Python :: 3.4',
                   'Topic :: Software Development :: Libraries :: Python Modules'
                   ],

      packages=['ant', 'ant.base', 'ant.easy', 'ant.fs'],
      
      requires=['pyusb (>1.0a2)'],
      
      data_files=[('/etc/udev/rules.d', ['resources/ant-usb-sticks.rules'])],

      cmdclass={'install': CustomInstall}
      )

