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

import StringIO
import sys


class StdOutCapture(object):
    def __init__(self):
        self.stdout = sys.stdout

    def __enter__(self):
        sys.stdout = StringIO.StringIO()
        return sys.stdout

    def __exit__(self, type, value, traceback):
        sys.stdout = self.stdout


class StdErrCapture(object):
    def __init__(self):
        self.stderr = sys.stderr

    def __enter__(self):
        sys.stderr = StringIO.StringIO()
        return sys.stderr

    def __exit__(self, type, value, traceback):
        sys.stderr = self.stderr
