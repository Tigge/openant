"""
Example shows how to use iPython backgroundjobs to run node runner in background whilst being able to interact with a device at the iPython prompt

Change the `device` to ones device of choice - a Dropper post here
"""
from IPython.lib import backgroundjobs as bg
import logging

from openant.devices import ANTPLUS_NETWORK_KEY
from openant.easy.node import Node
from openant.devices.power_meter import PowerMeter, PowerData
from openant.devices.lev import Lev
from openant.devices.shift import Shifting, ShiftData
from openant.devices.dropper_seatpost import (
    DropperSeatpost,
    DropperSeatpostData,
    ValveState,
)
from openant.devices.fitness_equipment import (
    FitnessEquipment,
    FitnessEquipmentData,
    Workout,
)
from openant.devices.controls_device import (
    GenericRemoteControl,
    ControlCommand
)

device = None


def node_runner(node, device):
    print(
        f"Starting {device}. Use `device.close_channel()` and `node.stop()` when done"
    )
    node.start()


def on_found():
    print(f"Device {device} found and receiving")


def on_device_data(page: int, page_name: str, data):
    if isinstance(data, DropperSeatpostData):
        print(f"Dropper seatpost state: {data.valve_state}")
    elif isinstance(data, FitnessEquipmentData):
        print(f"FitnessEquipmentData: {data}")
    elif isinstance(data, PowerData):
        print(f"PowerData: {data}")
    elif isinstance(data, ShiftData):
        print(f"ShiftData: {data}")
    else:
        print(f"DeviceData: {data}")


def begin(jobs, node, device):
    """Call this at iPython prompt to begin session"""
    jobs.new(node_runner, node, device)


def end(jobs, node, device):
    """Call to finish iPython session. If running `begin` following this, one must re-create the `node`"""
    device.close_channel()
    node.stop()
    jobs.flush()


# for verbose logging
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
jobs = bg.BackgroundJobManager()
node = Node()
node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)

# device = FitnessEquipment(node, device_id=0)
# device = DropperSeatpost(node, device_id=0)
# device = Lev(node, device_id=3)
device = GenericRemoteControl(node, device_id=0)

device.on_found = on_found
device.on_device_data = on_device_data
