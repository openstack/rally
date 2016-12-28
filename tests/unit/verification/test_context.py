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

import mock

from rally.verification import context
from tests.unit import test


@context.configure("fake_verifier_context", order=314)
class FakeContext(context.VerifierContext):
    def cleanup(self):
        pass

    def setup(self):
        pass


class VerifierContextTestCase(test.TestCase):
    def test__meta_get(self):

        data = {"key1": "value1", "key2": "value2", "hidden": False}

        for k, v in data.items():
            FakeContext._meta_set(k, v)

        for k, v in data.items():
            if k != "hidden":
                self.assertEqual(v, FakeContext._meta_get(k))

        self.assertTrue(FakeContext._meta_get("hidden"))
        self.assertNotEqual(data["hidden"], FakeContext._meta_get("hidden"))


class ContextManagerTestCase(test.TestCase):
    @mock.patch("rally.verification.context.VerifierContext")
    def test_validate(self, mock_verifier_context):
        config = {"ctx1": mock.Mock(), "ctx2": mock.Mock()}

        context.ContextManager.validate(config)

        self.assertEqual([mock.call(k) for k, v in config.items()],
                         mock_verifier_context.get.call_args_list)
        self.assertEqual(
            [mock.call(v, non_hidden=False) for k, v in config.items()],
            mock_verifier_context.get.return_value.validate.call_args_list)
