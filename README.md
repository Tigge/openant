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
 - ### a 4th lib ant.antplus - work in progress

 Work in progress
-----------------
### working so far: 
- a basic controller implementing background scanning of ANT+ devices
- FE-C device profile
- a sample test application

### modifications to openant main:
- driver.py : implemented a close() that returns the usb device, so the examples can be repeatedly restarted from the same running python kernel
- ant.py : removed the time.sleep(0.1) after every received broadcast. This line gave a lot of errors with multiple open ant channels. It prevents the reading from usb during 100ms, ( and thus max 10 broadcasts received per second), and resulted in continuous QUE_OVERFLOW and EVENT_QUE_OVERFLOW events, and thus loss of TX_COMPLETED events, etc. If this line was there for a reason with ANT-FS, this is incompatible with the ANT+ code.
- node.py : the fail events accumulate in de node._event deque and are never handled. this will lead to memory issues for long running apps. Some events will unavoidably happen, such as RX_FAIL or COLLISION, whenever multiple channel with different channel periods are open simultaneously. For the moment the fail events are simply deleted from the queue
- filter.py doesn't check the channel on which the TX_COMPLETED event arrived. this doesn't work on multiple open channels that send acknowledged messages : a TX_COMPLETED event from one channel can unblock the blocking wait on another channel. Or a TX_COMPLETED event that arrived beyond the timeout will remain in the event queue, and on a subsequent send_acknowledged_message, it will be mistaken for the ACK of this new message. Temporary solution implemented is to delete all TX_COMPLETED events for the channel before doing a send_acknowledged_message. this works for now as long as only 1 thread sends data per channel. Also temporarily disabled the check for EVENT_TRANSFER_TX_FAILED and EVENT_RX_FAIL_GO_TO_SEARCH events, until filter can check if it's on the correct channel. On the rare TX_FAILED event really happening, this will for now result in a timeout exception in wait_for_message (because no ack is received, and the TX_FAILED event is deleted from the event queue)

### open:
- filter.py : the timeout in wait_for_message is unpredictable, because 10 events (especially on another channel) can terminate the wait_for_message in a very short time. todo : replace "for _ in range(10): ..."
- filter.py : check on channel_id
- not clear why openant sends acknowledged messages via a separate queue instead of direct usb_write. The synchronisation on RF is done by the ANT+ stick anyway, there is no need to wait for the reception of a broadcast message on the python side. python code also doesn't check on which channel the broadcast arrived, and doesn't prevent sending a 2nd ack message from this queue before receiving the ACK from the master on the 1st (which is tested by filter.py on another thread)
- driver.py : add a workaround for the annoying usb timeout exceptions from pyusb when usb has no data (this happens as long as no ant channel is open)


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

- Install [PyUSB](https://github.com/walac/pyusb).

        pip install pyusb

    *(Or alternatively from [sources available on GitHub](https://github.com/walac/pyusb))*

- Install [udev](http://en.wikipedia.org/wiki/Udev) rules (Only required to avoid running the program as root).

        sudo python setup.py udev_rules

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
