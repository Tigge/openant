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
    * `openant mqtt`: Stream device data to MQTT server.

A note on ANT/ANT-FS/ANT+: this module is for development and testing of devices and not intended to be used as a reference. Refer to the [thisisant.com website](https://www.thisisant.com/) for full ANT documentation and ANT+ device profiles. The intention of this module is for quick R&D of ANT capable devices. In case non-obvious, this module is not an official tool.

# Installation

## Requirements

* Python >= 3.8

Run `pip install openant` or `pip install git+https://github.com/Tigge/openant#egg=openant` for HEAD.

If using on Linux, a udev rule for the Dynastream ANTUSB stick can be installed with `sudo python -m openant.udev_rules`. macOS/Windows does not use udev_rules and therefore does not need to be installed. Follow libusb's driver installation [instructions](https://github.com/libusb/libusb/wiki/Windows#Driver_Installation) for Windows. macOS should work with just libusb installed.

### ANT USB Stick

A USB stick that provides a ANT node is probably required. Here are ones made by Dynastream (Garmin):

* [ANTUSB2 Stick](http://www.thisisant.com/developer/components/antusb2/) (0fcf:1008: Dynastream Innovations, Inc.)
* [ANTUSB-m Stick](http://www.thisisant.com/developer/components/antusb-m/) (0fcf:1009: Dynastream Innovations, Inc.)

See the note regarding Linux and the udev rule above to ensure the user has permission to run this module without elevated privileges.

## InfluxDB CLI Tool

Requires install with [influx] (`pip install openant[influx]`) or influxdb-client module installed manually and InfluxDB server >= 2.0. See `openant influx --help` for the server setup. To quickly get a local instance running with Docker:

```
docker run --rm -p 8086:8086 -v $PWD:/var/lib/influxdb2 influxdb:latest
```

Navigate to 'http://localhost:8086' and setup a user/org (default org used is 'my-org'). Then setup a bucket to use (default 'my-bucket') and a API access token (Load Data > API Tokens).

## MQTT CLI Tool

Requires install with [mqtt] (`pip install openant[mqtt]`) or paho-mqtt module installed manually and MQTT 
server. See `openant mqtt --help` for the server setup.

To setup an open MQTT server for testing, use the following in `mosquitto.conf`:

```
listener 1883 0.0.0.0
allow_anonymous true
```

To start the server with docker:

```
docker run --rm -p 1883:1883 -v "$PWD/mosquitto.conf:/mosquitto/config/mosquitto.conf" eclipse-mosquitto:latest
```

# Module Usage

Explore the examples in './examples', and docstrings within module code. Further documentation to be developed in './docs'.

# CLI Tools

Accessed from module binary `openant`. Logging output can be enabled using the `--logging` flag.

# Scan

Scan for nearby devices, for example to obtain device IDs. Can search for specific devices `--device_type` or all. Found devices can be saved to file with `--outfile`.

### Example Usage

```
# print devices found to terminal
openant scan
# capture devices found to devices.json for use with antinflux
openant scan --outfile devices.json
# instantiate object when found so that device data is also printed
openant scan --auto_create
```

## ANT+ to InfluxDB

Stream DeviceData from a ANT+ device to a InfluxDB instance. Useful for plotting real-time data and for post review. See `openant influx --help`. See the notes on installation for this tool. Refer to the InfluxDB documentation for the required flags.

### Example Usage

```
# attach to first trainer found and push data to localhost InfluxDB
openant influx --verbose FitnessDevice
# attach to power meter with device id 12345 and push to localhost InfluxDB
openant influx --id 12345 --verbose PowerMeter
# attach to devices in 'devices.json' - allows connection to multiple devices
openant influx --verbose --config devices.json config
```

## ANT+ to MQTT

Stream DeviceData from a ANT+ device to an MQTT server. Useful for integration with a wide range of systems. See 
`openant influx --help`. See the notes on installation for this tool. Refer to MQTT server documentation for the 
required flags.

### Changing publish behaviour

Two flags control how data is published:

The flag `--topic-per-field` instructs the application to publish data to individual topics for each data field (e.g.
one for `heart_rate`, and another for `battery_percentage`). The default is to publish all received data as a single 
JSON-encoded string.

The flag `--device-topic` allows over-riding the topic used for posting a device's data. By default, data will be 
posted to `openant/<DeviceType>/<DeviceId>` (or a child thereof, if `--topic-per-field` is set).

### Example Usage

```
# attach to first trainer found and push data to localhost MQTT
openant mqtt --verbose FitnessDevice
# attach to power meter with device id 12345 and push to localhost MQTT
openant mqtt --id 12345 --verbose PowerMeter
# attach to devices in 'devices.json' - allows connection to multiple devices
openant mqtt --verbose --config devices.json config
# attach to devices in 'devices.json' and post a specific device's data to the topic my/heartrate
openant mqtt --config devices.json --device-topic 120:54368:my/heartrate config
```

# Supported ANT-FS Devices

Any compliant ANT-FS device should in theory work, but those specific devices have been reported as working:

## Garmin

 - Garmin Forerunner 60
 - Garmin Forerunner 405CX
 - Garmin Forerunner 310XT
 - Garmin Forerunner 610
 - Garmin Forerunner 910XT
 - Garmin FR70
 - Garmin Swim
 - Garmin vívoactive HR

## Wahoo

 - Wahoo Tickr 2 - Heart Rate data
 - Wahoo Kickr Core - Power data
 
Please let me know if you have any success with devices that are not listed here.

# Develop

## Create Documentation

Install requirements from './docs'. From './docs' run `make html`. To auto-generate any new module content run `make rst` or `sphinx-apidoc -f -o docs/src openant` in root directory.
