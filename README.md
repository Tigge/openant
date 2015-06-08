openant
=======

[![Build Status](https://img.shields.io/travis/Tigge/openant.svg?style=flat)](http://travis-ci.org/Tigge/openant)
[![Coverage Status](http://img.shields.io/coveralls/Tigge/openant.svg?style=flat)](https://coveralls.io/r/Tigge/openant)

A python library to download and upload files from ANT-FS compliant devices (Garmin products).

Features
--------

 - ANT
 - ANT-FS (with command pipe, file listings, downloading, uploading, etc)
 - Three libs (ant.base basic ANT library, ant.easy blocking version using ant.base, ant.fs ANT-FS library)

Requirements
------------

- Python 2.7+
- PyUSB > 1.0a2 (seems to be a bug which makes it segfaults on version before Alpha 2)
- Root access (for installation only)

Automatic install
-----------------

- Install [setuptools](https://pypi.python.org/pypi/setuptools):
 
        apt-get install python-setuptools
or

        wget https://bootstrap.pypa.io/ez_setup.py -O - | sudo python

- Run the following command:

        sudo python setup.py install

This will install everything required on your active python installation.


Manual install
--------------

These should only be necessary to install manually, if you don't want to use the Automatic installation script.

- Install [PyUSB](https://github.com/walac/pyusb).

        pip install pyusb

    *(Or alternatively from [sources available on GitHub](https://github.com/walac/pyusb))*

- Install [udev](http://en.wikipedia.org/wiki/Udev) rules (Only required to avoid running the program as root).

        sudo cp resources/ant-usb-sticks.rules /etc/udev/rules.d
        sudo udevadm control --reload-rules
        sudo udevadm trigger --subsystem-match=usb --attr-match=idVendor=0fcf --action=add

Supported devices
-----------------

### ANT USB Sticks

 - [ANTUSB2 Stick](http://www.thisisant.com/developer/components/antusb2/)
 (0fcf:1008: Dynastream Innovations, Inc.)
 - [ANTUSB-m Stick](http://www.thisisant.com/developer/components/antusb-m/)
 (0fcf:1009: Dynastream Innovations, Inc.)

### ANT-FS Devices

Any compliant ANT-FS device should in theory work, but those specific devices have been reported as working:

 - Garmin Forerunner 60
 - Garmin Forerunner 405CX
 - Garmin Forerunner 310XT
 - Garmin Forerunner 610
 - Garmin Forerunner 910XT
 - Garmin FR70
 - Garmin Swim

Please let me know if you have any success with devices that are not listed here.
