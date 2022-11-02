Fork of [openant](https://github.com/Tigge/openant) that brings ANT+ device support, new CLI tools and generally brings upto date. There some major changes to bring this to 1.0.0:

* Python 2 support is dropped in favour of fully supporting Python 3.
* Module folder name changed to match module name 'ant' -> 'openant' in order to be more Pythonic. Symbolic link remains for legacy but should use `import openant`/`from openant.` from now on.

# Features

* ANT base interface.
* ANT-FS (with command pipe, file listings, downloading, uploading, etc).
* ANT+ device profiles and base class for custom ones (openant.devices).
* Four libs:
    * openant.base basic ANT library.
    * openant.easy blocking version using openant.base.
    * openant.fs ANT-FS library.
    * openant.device ANT+ like devices.
* Command-line tool `openant`:
    * `openant scan`: Scan for nearby devices and optionally print device data.
    * `openant influx`: Stream device data to InfluxDB instance.

## Roadmap

* [ ] Expand tests, maybe use some form of USB emulation like [umap2](https://github.com/nccgroup/umap2) or a loopback.
* [ ] Add ANT+ devices.
* [ ] Improve documentation and auto generate hosted pages.

# Installation

## Requirements

* Python >= 3.7
* libusb 1.0 (for pyusb)

Run `pip install openant` or `pip install git+https://github.com/tuna-f1sh/openant#egg=openant` for HEAD. A 'Pipfile' is also provided for use with `pipenv`.

If using on Linux, a udev rule for the Dynastream ANTUSB stick can be installed with `sudo python setup.py udev_rules`. Windows does not use udev_rules and therefore does not need to be installed. Follow libusb's driver installation [instructions](https://github.com/libusb/libusb/wiki/Windows#Driver_Installation) for Windows. macOS should work with just libusb installed.

### ANT USB Stick

A USB stick that provides a ANT node is probably required. Here are ones made by Dynastream (Garmin):

* [ANTUSB2 Stick](http://www.thisisant.com/developer/components/antusb2/) (0fcf:1008: Dynastream Innovations, Inc.)
* [ANTUSB-m Stick](http://www.thisisant.com/developer/components/antusb-m/) (0fcf:1009: Dynastream Innovations, Inc.)

See the note regarding Linux and the udev rule above to ensure the user has permission to run this module without elevated privileges.

## InfluxDB CLI Tool

Stream DeviceData from a ANT+ device to a InfluxDB instance. Useful for plotting real-time data and for post review.

Requires install with [influx] (`pip install openant[influx]`) or influxdb-client module installed manually and InfluxDB server >= 2.0. See `openant influx --help` for the server setup. To quickly get a local instance running with Docker:

```
docker run --rm -p 8086:8086 \
      -v $PWD:/var/lib/influxdb2 \
      influxdb:latest
```

Navigate to 'http://localhost:8086' and setup a user/org (default org used is 'my-org'). Then setup a bucket to use (default 'my-bucket') and a API access token (Load Data > API Tokens).

# Supported ANT-FS Devices

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
