# Copyright 2014: Mirantis Inc.
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

from rally.common import validation
from rally import consts
from rally.plugins.openstack.cleanup import manager


@validation.configure("check_cleanup_resources")
class CheckCleanupResourcesValidator(validation.Validator):

    def __init__(self, admin_required):
        """Validates that openstack resource managers exist

        :param admin_required: describes access level to resource
        """
        super(CheckCleanupResourcesValidator, self).__init__()
        self.admin_required = admin_required

    def validate(self, context, config, plugin_cls, plugin_cfg):
        missing = set(plugin_cfg)
        missing -= manager.list_resource_names(
            admin_required=self.admin_required)
        missing = ", ".join(missing)
        if missing:
            return self.fail(
                "Couldn't find cleanup resource managers: %s" % missing)


class CleanupMixin(object):

    CONFIG_SCHEMA = {
        "type": "array",
        "$schema": consts.JSON_SCHEMA,
        "items": {
            "type": "string",
        }
    }

    def setup(self):
        pass
