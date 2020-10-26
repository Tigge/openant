# from ant.base import Message
import array
import logging
import sys
import traceback

from ant.easy.node import Message
from ant.fs.manager import Application


class App(Application):
    def setup_channel(self, channel):
        print("on setup channel")
        channel.set_period(4096)
        channel.set_search_timeout(255)
        channel.set_rf_freq(50)
        channel.set_search_waveform([0x53, 0x00])
        channel.set_id(0, 0x01, 0)

        print("Open channel...")
        channel.open()
        channel.request_message(Message.ID.RESPONSE_CHANNEL_STATUS)

    def on_link(self, beacon):
        print("on link")
        self.link()

    def on_authentication(self, beacon):
        print("on authentication")
        serial = self.authentication_serial()
        # passkey = self.authentication_pair("Friendly little name")
        passkey = array.array("B", b"\xea\x55\xdf\xa6\x57\x30\x47\x99")
        self.authentication_passkey(passkey)
        # print "Link", serial, "-", info, "-", beacon

    def on_transport(self, beacon):
        print("on transport")
        d = self.download_directory()
        print(
            d, d.get_version(), d._time_format, d._current_system_time, d._last_modified
        )
        print(d._files)


def main():
    try:
        # Set up logging
        logger = logging.getLogger("ant")
        logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler("test.log", "w")
        # handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                fmt="%(threadName)-10s %(asctime)s  %(name)-15s  %(levelname)-8s  %(message)s"
            )
        )
        logger.addHandler(handler)

        app = App()
        app.start()
    except (Exception, KeyboardInterrupt):
        traceback.print_exc()
        print("Interrupted")
        app.stop()
        sys.exit(1)
