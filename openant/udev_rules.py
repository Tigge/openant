#!/usr/bin/env python
#
# openant udev rules installer
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
from subprocess import call


def check_root():
    return os.geteuid() == 0


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
    if not platform.system() == "Linux":
        msg = "Udev rules are only supported on Linux"
        if raise_exception:
            raise OSError(msg)
        else:
            print(msg)

    if check_root():
        shutil.copy("resources/42-ant-usb-sticks.rules", "/etc/udev/rules.d")
        udev_reload_rules()
        udev_trigger()
    else:
        msg = 'You must have root privileges to install udev rules. Run "sudo python setup.py udev_rules"'
        if raise_exception:
            raise OSError(msg)
        else:
            print(msg)


if __name__ == "__main__":
    install_udev_rules(True)
