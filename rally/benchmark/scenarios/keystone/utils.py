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

import random
import string

from rally.benchmark.scenarios import base
from rally.benchmark.scenarios import utils as scenario_utils

# TODO(boris-42): Bind name to the uuid of benchmark.
TEMP_TEMPLATE = "rally_k_"


def is_temporary(resource):
    return resource.name.startswith(TEMP_TEMPLATE)


def generate_keystone_name(length=10):
    """Generate random name for keystone resources."""
    rand_part = ''.join(random.choice(string.lowercase) for i in range(length))
    return TEMP_TEMPLATE + rand_part


class KeystoneScenario(base.Scenario):
    """This class should contain base operations for benchmarking keystone,
       most of them are creating/deleting resources.
    """

    @scenario_utils.atomic_action_timer('keystone.create_user')
    def _user_create(self, name_length=10, password=None, email=None,
                     **kwargs):
        """Creates keystone user with random name.

        :param name_length: length of generated (ranodm) part of name
        :param **kwargs: Other optional parameters to create users like
                        "tenant_id", "enabled".
        :return: keystone user instance
        """
        name = generate_keystone_name(length=name_length)
        # NOTE(boris-42): password and email parameters are required by
        #                 keystone client v2.0. This should be cleanuped
        #                 when we switch to v3.
        password = password or name
        email = email or (name + "@rally.me")
        return self.admin_clients("keystone").users.create(name, password,
                                                           email, **kwargs)

    @scenario_utils.atomic_action_timer('keystone.delete_resource')
    def _resource_delete(self, resource):
        """"Delete keystone resource."""
        resource.delete()
