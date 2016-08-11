# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from rally.plugins.openstack.context.senlin import profiles
from tests.unit import test


BASE_CTX = "rally.task.context"
CTX = "rally.plugins.openstack.context"
BASE_SCN = "rally.task.scenarios"
SCN = "rally.plugins.openstack.scenarios"


class ProfilesGeneratorTestCase(test.ScenarioTestCase):
    """Generate tenants."""
    def _gen_tenants(self, count):
        tenants = {}
        for _id in range(count):
            tenants[str(_id)] = {"id": str(_id)}
        return tenants

    def setUp(self):
        super(ProfilesGeneratorTestCase, self).setUp()
        self.tenants_count = 2
        self.users_per_tenant = 3
        tenants = self._gen_tenants(self.tenants_count)
        users = []
        for tenant in tenants:
            for i in range(self.users_per_tenant):
                users.append({"id": i, "tenant_id": tenant,
                              "credential": mock.MagicMock()})

        self.context = {
            "config": {
                "users": {
                    "tenants": self.tenants_count,
                    "users_per_tenant": self.users_per_tenant
                },
                "profiles": {
                    "type": "profile_type_name",
                    "version": "1.0",
                    "properties": {"k1": "v1", "k2": "v2"}
                },
            },
            "users": users,
            "tenants": tenants,
            "task": mock.MagicMock()
        }

    @mock.patch("%s.senlin.utils.SenlinScenario._create_profile" % SCN,
                return_value=mock.MagicMock(id="TEST_PROFILE_ID"))
    def test_setup(self, mock_senlin_scenario__create_profile):
        profile_ctx = profiles.ProfilesGenerator(self.context)
        profile_ctx.setup()
        spec = self.context["config"]["profiles"]

        mock_calls = [mock.call(spec) for i in range(self.tenants_count)]
        mock_senlin_scenario__create_profile.assert_has_calls(mock_calls)

        for tenant in self.context["tenants"]:
            self.assertEqual("TEST_PROFILE_ID",
                             self.context["tenants"][tenant]["profile"])

    @mock.patch("%s.senlin.utils.SenlinScenario._delete_profile" % SCN)
    def test_cleanup(self, mock_senlin_scenario__delete_profile):
        for tenant in self.context["tenants"]:
            self.context["tenants"][tenant].update(
                {"profile": "TEST_PROFILE_ID"})
        profile_ctx = profiles.ProfilesGenerator(self.context)
        profile_ctx.cleanup()
        mock_calls = [mock.call("TEST_PROFILE_ID") for i in range(
            self.tenants_count)]
        mock_senlin_scenario__delete_profile.assert_has_calls(mock_calls)
