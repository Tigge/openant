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
from . import base
from . import easy
from . import fs

import argparse, logging

__all__ = ["base", "easy", "fs"]
__version__ = "1.0.0"

def _main(args=None):
    parser = argparse.ArgumentParser(
        description="ANT, ANT-FS and ANT+ Python Library"
    )
    parser.add_argument(
        "--logging",
        dest="logLevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    subparsers = parser.add_subparsers(
        title="command", dest="command", help="sub-command to run"
    )
    subparsers.required = True

    from .subparsers import scan

    # add subparsers
    scan.add_subparser(subparsers)

    # get the args
    args = parser.parse_args(args)

    # setup logging
    if args.logLevel:
        logging.basicConfig(level=logging.getLevelName(args.logLevel))

    # call the subparser run function
    args.func(args)


if __name__ == "__main__":
    _main()
