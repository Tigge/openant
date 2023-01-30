"""
ANT+ - Open Rx Scan Mode Example

Open Rx demo working with OpenAnt Library (https://github.com/Tigge/openant)

The continuous scanning mode allows an ANT node to asynchronously receive transmissions from multiple devices, regardless of their respective message rates. In scanning mode, the radio is active full time, so it is able to receive messages from transmitting nodes at any time.
All channels on a Node must be closed prior to enabling continous scanning mode and only one channel can be used.

TODO: the Node() should probably manage this.

For further details on Open Rx Mode ("Continious Scann Mode"), check out the thisisant.com webpage, ANT AN14.
"""
from openant.easy.node import Node
from openant.easy.channel import Channel
from openant.base.commons import format_list
from openant.devices import ANTPLUS_NETWORK_KEY

import logging
import time

"""
Ref ANT AN14:
A node in continuous scanning mode can be configured for bidirectional or receive-only communication.
Even though the continuous scanning mode makes full use of the radio, receiving 100% of the time; if a scanning node is configured for bidirectional communication, it is still possible to transmit data in response to a message from a master. In this case, it will also automatically send acknowledgements when receiving acknowledged and burst data. This could be a problem if the scanning device is not the intended destination of the data.
"""
# See above and only use BIDIRECTIONAL_RECEIVE if wishing to TX and ACK
RX_MODE = Channel.Type.UNIDIRECTIONAL_RECEIVE_ONLY
# RX_MODE = Channel.Type.BIDIRECTIONAL_RECEIVE

def main():
    print("ANT+ Open Rx Scan Mode Demo")
    logging.basicConfig(level=logging.DEBUG)

    TimeProgramStart = time.time()  # get start time

    def on_data_scan(data):
        deviceNumber = data[10] * 256 + data[9]
        deviceType = data[11]
        ActualTime = time.time() - TimeProgramStart
        print(f"{ActualTime:.3f} RX: {deviceNumber:05}, {deviceType:03}: {format_list(data)}")

    def on_data_ack_scan(data):
        deviceNumber = data[10] * 256 + data[9]
        deviceType = data[11]
        ActualTime = time.time() - TimeProgramStart
        print(f"{ActualTime:.3f} RX: {deviceNumber:05}, {deviceType:03}: {format_list(data)}")

    node = Node()
    node.set_network_key(0x00, ANTPLUS_NETWORK_KEY)  # 1. Set Network Key
    # CHANNEL CONFIGURATION
    channel = node.new_channel(
        RX_MODE, 0x00, 0x00
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
        channel.close()
        node.stop()
        logging.shutdown()  # Shutdown Logger


if __name__ == "__main__":
    main()
