# Copyright 2014: Mirantis Inc.
# Copyright 2014: Catalyst IT Ltd.
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

import os
import re
import traceback
import unittest

from tests.functional import utils


class TestTaskSamples(unittest.TestCase):

    def _skip(self, validation_output):
        """Help to decide do we want to skip this result or not.

        :param validation_output: string representation of the
        error that we want to check
        :return: True if we want to skip this error
        of task sample validation, otherwise False.
        """

        skip_lst = ["[Ss]ervice is not available",
                    "is not installed. To install it run"]
        for check_str in skip_lst:
            if re.search(check_str, validation_output) is not None:
                return True
        return False

    def test_task_samples_is_valid(self):
        rally = utils.Rally()
        samples_path = os.path.join(
            os.path.dirname(__file__), os.pardir, os.pardir,
            "samples", "tasks")
        matcher = re.compile("\.json$")

        for dirname, dirnames, filenames in os.walk(samples_path):
            # NOTE(rvasilets): Skip by suggest of boris-42 because in
            # future we don't what to maintain this dir
            if dirname.find("tempest-do-not-run-against-production") != -1:
                continue
            for filename in filenames:
                full_path = os.path.join(dirname, filename)

                # NOTE(hughsaunders): Skip non config files
                # (bug https://bugs.launchpad.net/rally/+bug/1314369)
                if not matcher.search(filename):
                    continue
                try:
                    rally("task validate --task %s" % full_path)
                except utils.RallyCliError as e:
                    if not self._skip(e.output):
                        raise e
                except Exception:
                    print(traceback.format_exc())
                    self.assertTrue(False,
                                    "Wrong task config %s" % full_path)
