# Copyright 2017: Mirantis Inc.
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


import re

from glanceclient import exc as glance_exc

from rally.common import validation
from rally import exceptions
from rally.plugins.openstack import types as openstack_types


@validation.add("required_platform", platform="openstack", users=True)
@validation.configure(name="image_exists", namespace="openstack")
class ImageExistsValidator(validation.Validator):

    def __init__(self, param_name, nullable):
        """Validator checks existed image or not

        :param param_name: defines which variable should be used
                           to get image id value.
        :param nullable: defines image id param is required
        """
        super(ImageExistsValidator, self).__init__()
        self.param_name = param_name
        self.nullable = nullable

    def validate(self, config, credentials, plugin_cls,
                 plugin_cfg):

        image_args = config.get("args", {}).get(self.param_name)

        if not image_args and self.nullable:
            return

        image_context = config.get("context", {}).get("images", {})
        image_ctx_name = image_context.get("image_name")

        if not image_args:
            message = ("Parameter %s is not specified.") % self.param_name
            return self.fail(message)

        if "image_name" in image_context:
            # NOTE(rvasilets) check string is "exactly equal to" a regex
            # or image name from context equal to image name from args
            if "regex" in image_args:
                match = re.match(image_args.get("regex"), image_ctx_name)
            if image_ctx_name == image_args.get("name") or (
                    "regex" in image_args and match):
                return
        try:
            for user in credentials["openstack"]["users"]:
                clients = user.get("credential", {}).clients()
                image_id = openstack_types.GlanceImage.transform(
                    clients=clients, resource_config=image_args)
                clients.glance().images.get(image_id)
        except (glance_exc.HTTPNotFound, exceptions.InvalidScenarioArgument):
            message = ("Image '%s' not found") % image_args
            return self.fail(message)
