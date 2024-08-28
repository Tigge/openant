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
import argparse
import logging
import importlib
import pathlib
import os

from . import base
from . import easy
from . import fs
from . import devices

__all__ = ["base", "easy", "fs", "devices"]
__version__ = "1.3.2"


# subparser importer taken from cantools module
class _ErrorSubparser:
    def __init__(self, subparser_name, error_message):
        self.subparser_name = subparser_name
        self.error_message = error_message

    def add_subparser(self, subparser_list):
        err_parser = subparser_list.add_parser(
            self.subparser_name, description=self.error_message
        )
        err_parser.add_argument("args", nargs="*")

        err_parser.set_defaults(func=self._print_error)

    def _print_error(self, _):
        raise ImportError(self.error_message)


def _load_subparser(subparser_name, subparsers):
    """Load a subparser for a CLI command in a safe manner.

    i.e., if the subparser cannot be loaded due to an import error or
    similar, no exception is raised if another command was invoked on
    the CLI."""

    try:
        result = importlib.import_module(
            f".subparsers.{subparser_name}", package="openant"
        )
        result.add_subparser(subparsers)

    except ImportError as e:
        result = _ErrorSubparser(
            subparser_name, f'Command "{subparser_name}" is unavailable: "{e}"'
        )
        result.add_subparser(subparsers)


def _main(args=None):
    parser = argparse.ArgumentParser(description="ANT, ANT-FS and ANT+ Python Library")
    parser.add_argument(
        "--logging",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        title="command", dest="command", help="sub-command to run"
    )
    subparsers.required = True

    # module's 'subparsers' sub-directory
    subparsers_dir = pathlib.Path(__file__).parent / "subparsers"
    for cur_file_name in os.listdir(subparsers_dir):
        if cur_file_name.startswith("__"):
            continue

        if cur_file_name.endswith(".py"):
            subparser_name = cur_file_name[:-3]
            _load_subparser(subparser_name, subparsers)
        elif (subparsers_dir / cur_file_name / "__init__.py").is_file():
            subparser_name = cur_file_name
            _load_subparser(subparser_name, subparsers)

    # get the args
    args = parser.parse_args(args)

    # setup logging
    if args.logging:
        logging.basicConfig(level=logging.getLevelName(args.logging))

    # call the subparser run function
    args.func(args)


if __name__ == "__main__":
    _main()
