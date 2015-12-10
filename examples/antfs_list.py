# ANT - ANT-FS List Example
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

from __future__ import absolute_import, print_function
import logging
from ant.fs.manager import Application, AntFSAuthenticationException, AntFSTimeException, AntFSDownloadException, \
    AntFSUploadException


class Listener(Application):
    def __init__(self):
        Application.__init__(self)

    def setup_channel(self, channel):
        channel.set_period(4096)
        channel.set_search_timeout(255)
        channel.set_rf_freq(50)
        channel.set_search_waveform([0x53, 0x00])
        channel.set_id(0, 0x01, 0)

        channel.open()

        print("Lister: Searching for devices...")

    def on_link(self, beacon):
        print("Lister: Link", beacon.get_serial(), beacon.get_descriptor())
        self.link()
        return True

    def on_authentication(self, beacon):
        print("Lister: Auth", self.authentication_serial())
        try:
            self.authentication_pair("ANT-FS List")
            return True
        except AntFSAuthenticationException as e:
            return False

    def on_transport(self, beacon):
        try:
            self.set_time()
        except (AntFSTimeException, AntFSDownloadException, AntFSUploadException):
            print("Could not set time")

        print("Listener: Transport")
        directory = self.download_directory()
        print("Directory version:      ", directory.get_version())
        print("Directory time format:  ", directory.get_time_format())
        print("Directory system time:  ", directory.get_current_system_time())
        print("Directory last modified:", directory.get_last_modified())
        directory.print_list()


def main():
    logging.basicConfig()

    try:
        a = Listener()
        print("Start")
        a.start()
    except:
        print("Aborted")
        raise
    finally:
        print("Stop")
        # a.stop()


if __name__ == "__main__":
    main()
