openant
=======

[![Build Status](https://github.com/Tigge/openant/workflows/Build/badge.svg?branch=master)](https://github.com/Tigge/openant/actions)
[![Coverage Status](http://img.shields.io/coveralls/Tigge/openant.svg?style=flat)](https://coveralls.io/r/Tigge/openant)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A python library to download and upload files from ANT-FS compliant devices (Garmin products).

Features
--------

 - ANT
 - ANT-FS (with command pipe, file listings, downloading, uploading, etc)
 - Three libs (ant.base basic ANT library, ant.easy blocking version using ant.base, ant.fs ANT-FS library)

Requirements
------------

- Python >= 3.6
- PyUSB >= 1.1.0
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

- Install [PyUSB](https://github.com/pyusb/pyusb).

        pip install pyusb

    *(Or alternatively from [sources available on GitHub](https://github.com/pyusb/pyusb))*

- Install [udev](http://en.wikipedia.org/wiki/Udev) rules (Only required to avoid running the program as root).

        sudo python setup.py udev_rules


Windows install
--------------
Windows does not use udev_rules and therefore does not need to be installed. The installation of udev_rules is
bypassed for Windows. libusb is supported by Windows. Follow libusb's driver installation [instructions](https://github.com/libusb/libusb/wiki/Windows#Driver_Installation) for Windows. 

- Install [PyUSB](https://github.com/pyusb/pyusb).

        pip install pyusb

    *(Or alternatively from [sources available on GitHub](https://github.com/pyusb/pyusb))*

- Install [libusb](https://github.com/karpierz/libusb).

        pip install libusb

    *(Or alternatively from [sources available on GitHub](https://github.com/karpierz/libusb))*

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
 - Garmin vívoactive HR

Please let me know if you have any success with devices that are not listed here.
