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

from unittest import mock

from rally.common import opts
from tests.unit import test


def fake_list_opts():
    return {"fake_group": ["option1"]}


class RegisterOptsTestCase(test.TestCase):
    @mock.patch("rally.common.opts.register_opts")
    def test_register_options_from_path(self, mock_register_opts):

        opts.register_options_from_path("unexisting.path.without.method.name")
        self.assertFalse(mock_register_opts.called)
        self.assertIsEmpty(opts._registered_paths)

        opts.register_options_from_path("unexisting.path:method_name")
        self.assertFalse(mock_register_opts.called)
        self.assertIsEmpty(opts._registered_paths)

        opts.register_options_from_path(
            "tests.unit.common.test_opts:fake_list_opts")
        mock_register_opts.assert_called_once_with(fake_list_opts().items())
        self.assertIn("tests.unit.common.test_opts:fake_list_opts",
                      opts._registered_paths)
