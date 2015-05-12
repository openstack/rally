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


from rally import exceptions
from rally.plugins.common.context import dummy
from tests.unit import test


class DummyContextTestCase(test.TestCase):
    def test_setup(self):
        dummy.DummyContext({"task": "some_task"}).setup()
        config = {"dummy_context": {"fail_setup": True}}
        self.assertRaises(
            exceptions.RallyException,
            dummy.DummyContext({"task": "some_task", "config": config}).setup)

    def test_cleanup(self):
        dummy.DummyContext({"task": "some_task"}).cleanup()
        config = {"dummy_context": {"fail_cleanup": True}}
        self.assertRaises(
            exceptions.RallyException,
            dummy.DummyContext({"task": "some_task",
                                "config": config}).cleanup)
