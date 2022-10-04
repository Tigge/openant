# ANT+ - Open Rx Scan Mode Example
#
# Open Rx demo working with OpenAnt Library (https://github.com/Tigge/openant)
# For further details on Open Rx Mode ("Continious Scann Mode"), check out the thisisant.com webpage

from ant.easy.node import Node
from ant.easy.channel import Channel
from ant.base.commons import format_list

import logging
import time

# Definition of Variables
NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]


def main():
    print("ANT+ Open Rx Scan Mode Demo")
    logging.basicConfig(filename="example.log", level=logging.DEBUG)

    TimeProgramStart = time.time()  # get start time

    def on_data_scan(data):
        deviceNumber = data[10] * 256 + data[9]
        deviceType = data[11]
        ActualTime = time.time() - TimeProgramStart
        print(ActualTime, "RX:", deviceNumber, ", ", deviceType, ":", format_list(data))

    def on_data_ack_scan(data):
        deviceNumber = data[10] * 256 + data[9]
        deviceType = data[11]
        ActualTime = time.time() - TimeProgramStart
        print(ActualTime, "RX-Ack:", deviceNumber, ", ", deviceType, ":", format_list(data))

    node = Node()
    node.set_network_key(0x00, NETWORK_KEY)  # 1. Set Network Key
    # CHANNEL CONFIGURATION
    channel = node.new_channel(
        Channel.Type.BIDIRECTIONAL_RECEIVE, 0x00, 0x00
    )  # 2. Assign channel

    channel.on_broadcast_data = on_data_scan
    channel.on_burst_data = on_data_scan
    channel.on_acknowledge = on_data_scan
    channel.on_acknowledge_data = on_data_ack_scan  # von mir

    channel.set_id(0, 0, 0)  # 3. Set Channel ID
    channel.set_period(0)  # 4. Set Channel Period
    channel.set_rf_freq(57)  # 5. Set RadioFrequenzy
    channel.enable_extended_messages(
        1
    )  # 6. Enable Extended Messages, needed for OpenRxScanMode

    try:
        channel.open_rx_scan_mode()  #  7. OpenRxScanMode
        node.start()
    except KeyboardInterrupt:
        print("Closing ANT+ Channel")
        channel.close()
        node.stop()
    finally:
        node.stop()
        logging.shutdown()  # Shutdown Logger


if __name__ == "__main__":
    main()
