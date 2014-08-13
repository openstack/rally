# Copyright 2014: Kylin Cloud
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

import random

from rally.benchmark.scenarios import base


class QuotasScenario(base.Scenario):

    @base.atomic_action_timer('quotas.update_quotas')
    def _update_quotas(self, component, tenant_id, max_quota=1024):
        """Updates quotas.

        :param component: Component for the quotas.
        :param tenant_id: The project_id for the quotas to be updated.
        :param max_quota: Max value to be updated for quota.

        :returns: Updated quotas dictionary.
        """
        quotas = self._generate_quota_values(max_quota, component)
        return self.admin_clients(component).quotas.update(tenant_id, **quotas)

    @base.atomic_action_timer('quotas.delete_quotas')
    def _delete_quotas(self, component, tenant_id):
        """Deletes quotas.

        :param component: Component for the quotas.
        :param tenant_id: The project_id for the quotas to be updated.
        """
        self.admin_clients(component).quotas.delete(tenant_id)

    def _generate_quota_values(self, max_quota, component):
        quotas = {}
        if component == "nova":
            quotas = {
                'metadata_items': random.randint(-1, max_quota),
                'key_pairs': random.randint(-1, max_quota),
                'injected_file_content_bytes': random.randint(-1, max_quota),
                'injected_file_path_bytes': random.randint(-1, max_quota),
                'ram': random.randint(-1, max_quota),
                'instances': random.randint(-1, max_quota),
                'injected_files': random.randint(-1, max_quota),
                'cores': random.randint(-1, max_quota)
            }
        elif component == "cinder":
            quotas = {
                'volumes': random.randint(-1, max_quota),
                'snapshots': random.randint(-1, max_quota),
                'gigabytes': random.randint(-1, max_quota),
            }
        return quotas
