# Ant
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


import array
import logging

try:
    from functools import reduce
except ImportError:
    pass

from .commons import format_list

_logger = logging.getLogger("ant.base.message")


class Message:
    class ID:
        INVALID = 0x00

        # Configuration messages
        UNASSIGN_CHANNEL = 0x41
        ASSIGN_CHANNEL = 0x42
        SET_CHANNEL_ID = 0x51
        SET_CHANNEL_PERIOD = 0x43
        SET_CHANNEL_SEARCH_TIMEOUT = 0x44
        SET_CHANNEL_RF_FREQ = 0x45
        SET_NETWORK_KEY = 0x46
        SET_TRANSMIT_POWER = 0x47
        SET_SEARCH_WAVEFORM = 0x49
        ADD_CHANNEL_ID = 0x59  # Only used for slave channels
        ADD_ENCRYPTION_ID = 0x59  # Only used for encrypted ANT master channels
        CONFIG_LIST = 0x5A  # Only used for slave channels
        CONFIG_ENCRYPTION_LIST = 0x5A  # Only used for encrypted ANT master channels
        SET_CHANNEL_TX_POWER = 0x60
        LOW_PRIORITY_CHANNEL_SEARCH_TIMEOUT = 0x63
        SERIAL_NUMBER_SET_CHANNEL = 0x65
        ENABLE_EXT_RX_MESGS = 0x66
        ENABLE_LED = 0x68
        ENABLE_CRYSTAL = 0x6D
        LIB_CONFIG = 0x6E
        FREQUENCY_AGILITY = 0x70
        PROXIMITY_SEARCH = 0x71
        CONFIG_EVENT_BUFFER = 0x74
        CHANNEL_SEARCH_PRIORITY = 0x75
        SET_128_NETWORK_KEY = 0x76
        HIGH_DUTY_SEARCH = 0x77
        CONFIG_ADVANCED_BURST = 0x78
        CONFIG_EVENT_FILTER = 0x79
        CONFIG_SELECTIVE_DATA_UPDATE = 0x7A
        SET_SDU_MASK = 0x7B
        CONFIG_USER_NVM = 0x7C
        ENABLE_SINGLE_CHANNEL_ENCRYPTION = 0x7D
        SET_ENCRYPTION_KEY = 0x7E
        SET_ENCRYPTION_INFO = 0x7F
        CHANNEL_SEARCH_SHARING = 0x81
        LOAD_STORE_ENCRYPTION_KEY = 0x83
        SET_USB_DESCRIPTOR_STRING = 0xC7
        # SET_USB_INFO = 0xff

        # Notifications
        STARTUP_MESSAGE = 0x6F
        SERIAL_ERROR_MESSAGE = 0xAE

        # Control messags
        RESET_SYSTEM = 0x4A
        OPEN_CHANNEL = 0x4B
        CLOSE_CHANNEL = 0x4C
        REQUEST_MESSAGE = 0x4D
        OPEN_RX_SCAN_MODE = 0x5B
        SLEEP_MESSAGE = 0xC5

        # Data messages
        BROADCAST_DATA = 0x4E
        ACKNOWLEDGED_DATA = 0x4F
        BURST_TRANSFER_DATA = 0x50
        ADVANCED_BURST_TRANSFER_DATA = 0x72

        # Responses (from channel)
        # CHANNEL_EVENT = 0x40
        RESPONSE_CHANNEL = 0x40

        # Responses (from REQUEST_MESSAGE, 0x4d)
        RESPONSE_CHANNEL_STATUS = 0x52
        RESPONSE_CHANNEL_ID = 0x51
        RESPONSE_ANT_VERSION = 0x3E
        RESPONSE_CAPABILITIES = 0x54
        RESPONSE_SERIAL_NUMBER = 0x61
        RESPONSE_EVENT_BUFFER_CONFIG = 0x74  # dupe
        RESPONSE_ADVANCED_BURST_CAPABILITIES = 0x78  # dupe
        # RESPONSE_ADVANCED_BURST_CURRENT_CONFIG = 0x78 # dupe
        RESPONSE_EVENT_FILTER = 0x79  # dupe

        # Test mode
        TEST_MODE_CW_INIT = 0x53
        TEST_MODE_CW_TEST = 0x48

        # Extended data messages (legacy)
        LEGACY_EXTENDED_BROADCAST_DATA = 0x5D
        LEGACY_EXTENDED_ACKNOWLEDGED_DATA = 0x5E
        LEGACY_EXTENDED_BURST_DATA = 0x5F

    class Code:
        RESPONSE_NO_ERROR = 0

        EVENT_RX_SEARCH_TIMEOUT = 1
        EVENT_RX_FAIL = 2
        EVENT_TX = 3
        EVENT_TRANSFER_RX_FAILED = 4
        EVENT_TRANSFER_TX_COMPLETED = 5
        EVENT_TRANSFER_TX_FAILED = 6
        EVENT_CHANNEL_CLOSED = 7
        EVENT_RX_FAIL_GO_TO_SEARCH = 8
        EVENT_CHANNEL_COLLISION = 9
        EVENT_TRANSFER_TX_START = 10

        EVENT_TRANSFER_NEXT_DATA_BLOCK = 17

        CHANNEL_IN_WRONG_STATE = 21
        CHANNEL_NOT_OPENED = 22
        CHANNEL_ID_NOT_SET = 24
        CLOSE_ALL_CHANNELS = 25

        TRANSFER_IN_PROGRESS = 31
        TRANSFER_SEQUENCE_NUMBER_ERROR = 32
        TRANSFER_IN_ERROR = 33

        MESSAGE_SIZE_EXCEEDS_LIMIT = 39
        INVALID_MESSAGE = 40
        INVALID_NETWORK_NUMBER = 41
        INVALID_LIST_ID = 48
        INVALID_SCAN_TX_CHANNEL = 49
        INVALID_PARAMETER_PROVIDED = 51
        EVENT_SERIAL_QUE_OVERFLOW = 52
        EVENT_QUE_OVERFLOW = 53
        ENCRYPT_NEGOTIATION_FAIL = 57
        NVM_FULL_ERROR = 64
        NVM_WRITE_ERROR = 65
        USB_STRING_WRITE_FAIL = 112
        MESG_SERIAL_ERROR_ID = 174

        EVENT_RX_BROADCAST = 1000
        EVENT_RX_FLAG_BROADCAST = 1001
        EVENT_RX_ACKNOWLEDGED = 2000
        EVENT_RX_FLAG_ACKNOWLEDGED = 2001
        EVENT_RX_BURST_PACKET = 3000
        EVENT_RX_FLAG_BURST_PACKET = 3001

        @staticmethod
        def lookup(event):
            for key, value in Message.Code.__dict__.items():
                if type(value) == int and value == event:
                    return key

    def __init__(self, mId, data):
        self._sync = 0xA4
        self._length = len(data)
        self._id = mId
        self._data = data
        self._checksum = (
            self._sync ^ self._length ^ self._id ^ reduce(lambda x, y: x ^ y, data)
        )

    def __repr__(self):
        return str.format(
            "<ant.base.Message {0:02x}:{1} (s:{2:02x}, l:{3}, c:{4:02x})>",
            self._id,
            format_list(self._data),
            self._sync,
            self._length,
            self._checksum,
        )

    def get(self):
        result = array.array("B", [self._sync, self._length, self._id])
        result.extend(self._data)
        result.append(self._checksum)
        return result

    @staticmethod
    def parse(buf):
        """
        Parse a message from an array
        """
        sync = buf[0]
        length = buf[1]
        mId = buf[2]
        data = buf[3:-1]
        checksum = buf[-1]

        assert sync == 0xA4
        assert length == len(data)
        assert checksum == reduce(lambda x, y: x ^ y, buf[:-1])

        return Message(mId, data)
