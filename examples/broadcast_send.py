# ANT+ - Stride Based Speed and Distance Sensor Example
#
# SDM demo working with OpenAnt Library (https://github.com/Tigge/openant)
# using feature of:
# - acting as Transmitting Device (TX-Broadcast)
# - gracefully close ANT-Channels
#
# For further details on Speed & Distance Sensor, check out the thisisant.com webpage

import logging
import time

from openant.easy.node import Node
from openant.easy.channel import Channel
from openant.base.commons import format_list

# Definition of Variables
NETWORK_KEY = [0xB9, 0xA5, 0x21, 0xFB, 0xBD, 0x72, 0xC3, 0x45]
Device_Type = 124  # 124 = Stride & Distance Sensor
Device_Number = 12345  # Change if you need.
Channel_Period = 8134
Channel_Frequency = 57

# Fictive Config of Treadmill
TreadmillSpeed = 2.777  # m/s => 10km/h
TreadmillCadence = 160

##########################################################################


class AntSendDemo:
    def __init__(self):

        self.ANTMessageCount = 0
        self.ANTMessagePayload = [0, 0, 0, 0, 0, 0, 0, 0]

        # Init Variables, needed
        self.LastStrideTime = 0
        self.StridesDone = 0
        self.DistanceAccu = 0
        self.Speed_Last = 0
        self.TimeRollover = 0

        self.TimeProgramStart = time.time()
        self.LastTimeEvent = time.time()

        # Building up the Datapages
        # This is just for demo purpose and can/will look diverent for every implementation

    def Create_Next_DataPage(self):
        # Define Variables
        UpdateLatency_7 = 0

        self.ANTMessageCount += 1

        # Time Calculations
        self.ElapsedSseconds = time.time() - self.LastTimeEvent
        self.LastTimeEvent = time.time()
        UpdateLatency_7 += self.ElapsedSseconds  # 1Second / 32 = 0,03125
        UL_7 = int(UpdateLatency_7 / 0.03125)

        # Stride Count, Accumulated strides.
        # This value is incremented once for every two footfalls.
        StrideCountUpValue = 60.0 / (TreadmillCadence / 2.0)  # In our Example 0,75
        while self.LastStrideTime > StrideCountUpValue:
            self.StridesDone += 1
            self.LastStrideTime -= StrideCountUpValue
        self.LastStrideTime += self.ElapsedSseconds
        if self.StridesDone > 255:
            self.StridesDone -= 255

        # DISTANCE
        # Accumulated distance, in m-Meters, Rollover = 256
        self.DistanceBetween = self.ElapsedSseconds * TreadmillSpeed
        self.DistanceAccu += (
            self.DistanceBetween
        )  # Add Distance beetween 2 ANT+ Ticks to Accumulated Distance
        if self.DistanceAccu > 255:
            self.DistanceAccu -= 255

        self.distance_H = int(self.DistanceAccu)  # just round it to INT
        self.DistanceLow_HEX = int((self.DistanceAccu - self.distance_H) * 16)

        # SPEED - Berechnung
        self.var_speed_ms_H = int(TreadmillSpeed)  # INT-Value
        self.var_speed_ms_L = int(TreadmillSpeed * 1000) - (self.var_speed_ms_H * 1000)
        self.var_speed_ms_L_HEX = int((TreadmillSpeed - self.var_speed_ms_H) * 256)

        # TIME (chnages to Distance or speed will effect if This byte needs to be calculated (<= check Specifikation)
        if self.Speed_Last != TreadmillSpeed or self.Distance_Last != self.DistanceAccu:
            self.TimeRollover += self.ElapsedSseconds
            if self.TimeRollover > 255:
                self.TimeRollover -= 255

        self.TimeRollover_H = int(self.TimeRollover)
        # only integer
        if self.TimeRollover_H > 255:
            self.TimeRollover_H = 255
        self.TimeRollover_L_HEX = int((self.TimeRollover - self.TimeRollover_H) * 200)
        if self.TimeRollover_L_HEX > 255:
            self.TimeRollover_L_HEX -= 255
        self.Speed_Last = TreadmillSpeed
        self.Distance_Last = self.DistanceAccu

        if self.ANTMessageCount < 3:
            self.ANTMessagePayload[0] = 80  # DataPage 80
            self.ANTMessagePayload[1] = 0xFF
            self.ANTMessagePayload[2] = 0xFF  # Reserved
            self.ANTMessagePayload[3] = 1  # HW Revision
            self.ANTMessagePayload[4] = 1
            self.ANTMessagePayload[5] = 1  # Manufacturer ID
            self.ANTMessagePayload[6] = 1
            self.ANTMessagePayload[7] = 1  # Model Number

        elif self.ANTMessageCount > 64 and self.ANTMessageCount < 67:
            self.ANTMessagePayload[0] = 81  # DataPage 81
            self.ANTMessagePayload[1] = 0xFF
            self.ANTMessagePayload[2] = 0xFF  # Reserved
            self.ANTMessagePayload[3] = 1  # SW Revision
            self.ANTMessagePayload[4] = 0xFF
            self.ANTMessagePayload[5] = 0xFF  # Serial Number
            self.ANTMessagePayload[6] = 0xFF
            self.ANTMessagePayload[7] = 0xFF  # Serial Number

        else:
            self.ANTMessagePayload[0] = 0x01  # Data Page 1
            self.ANTMessagePayload[1] = self.TimeRollover_L_HEX
            self.ANTMessagePayload[2] = self.TimeRollover_H  # Reserved
            self.ANTMessagePayload[3] = self.distance_H  # Distance Accumulated INTEGER
            # BYTE 4 - Speed-Integer & Distance-Fractional
            self.ANTMessagePayload[4] = (
                self.DistanceLow_HEX * 16 + self.var_speed_ms_H
            )  # Instaneus Speed, Note: INTEGER
            self.ANTMessagePayload[
                5
            ] = self.var_speed_ms_L_HEX  # Instaneus Speed, Fractional
            self.ANTMessagePayload[6] = self.StridesDone  # Stride Count
            self.ANTMessagePayload[7] = UL_7  # Update Latency

            # ANTMessageCount reset
            if self.ANTMessageCount > 131:
                self.ANTMessageCount = 0

        return self.ANTMessagePayload

    # TX Event
    def on_event_tx(self, data):
        ANTMessagePayload = self.Create_Next_DataPage()
        self.ActualTime = time.time() - self.TimeProgramStart

        # ANTMessagePayload = array.array('B', [1, 255, 133, 128, 8, 0, 128, 0])    # just for Debuggung pourpose

        self.channel.send_broadcast_data(
            self.ANTMessagePayload
        )  # Final call for broadcasting data
        print(
            self.ActualTime,
            "TX:",
            Device_Number,
            ",",
            Device_Type,
            ":",
            format_list(ANTMessagePayload),
        )

    # Open Channel
    def OpenChannel(self):

        self.node = Node()  # initialize the ANT+ device as node

        # CHANNEL CONFIGURATION
        self.node.set_network_key(0x00, NETWORK_KEY)  # set network key
        self.channel = self.node.new_channel(
            Channel.Type.BIDIRECTIONAL_TRANSMIT, 0x00, 0x00
        )  # Set Channel, Master TX
        self.channel.set_id(
            Device_Number, Device_Type, 5
        )  # set channel id as <Device Number, Device Type, Transmission Type>
        self.channel.set_period(Channel_Period)  # set Channel Period
        self.channel.set_rf_freq(Channel_Frequency)  # set Channel Frequency

        # Callback function for each TX event
        self.channel.on_broadcast_tx_data = self.on_event_tx

        try:
            self.channel.open()  # Open the ANT-Channel with given configuration
            self.node.start()
        except KeyboardInterrupt:
            print("Closing ANT+ Channel...")
            self.channel.close()
            self.node.stop()
        finally:
            print("Final checking...")
            # not sure if there is anything else we should check?! :)


###########################################################################################################################
def main():
    print("ANT+ Send Broadcast Demo")
    logging.basicConfig(
        filename="example.log", level=logging.DEBUG
    )  # just for Debugging purpose, outcomment this in live version

    ant_senddemo = AntSendDemo()

    try:
        ant_senddemo.OpenChannel()  # start
    except KeyboardInterrupt:
        print("Closing ANT+ Channel!")
    finally:
        print("Finally...")
        logging.shutdown()  # Shutdown Logger

    print("Close demo...")


if __name__ == "__main__":
    main()
