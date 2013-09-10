# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

""" CLI interface for Rally. """

from __future__ import print_function

import sys

from rally.cmd import cliutils
from rally import db
from rally.openstack.common.gettextutils import _   # noqa


class DBCommands(object):
    """Commands for DB management."""

    def recreate(self):
        try:
            db.db_drop()
            db.db_create()
        except Exception as e:
            print(_("Something went wrong %s") % e)


def main(argv):
    categories = {'db': DBCommands}
    cliutils.run(argv, categories)


if __name__ == '__main__':
    main(sys.argv)
