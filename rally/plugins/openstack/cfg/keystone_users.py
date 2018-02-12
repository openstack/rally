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

from rally.common import cfg


OPTS = {"openstack": [
    cfg.IntOpt("users_context_resource_management_workers",
               default=20,
               deprecated_name="resource_management_workers",
               deprecated_group="users_context",
               help="The number of concurrent threads to use for serving "
                    "users context."),
    cfg.StrOpt("project_domain",
               default="default",
               deprecated_group="users_context",
               help="ID of domain in which projects will be created."),
    cfg.StrOpt("user_domain",
               default="default",
               deprecated_group="users_context",
               help="ID of domain in which users will be created."),
    cfg.StrOpt("keystone_default_role",
               default="member",
               deprecated_group="users_context",
               help="The default role name of the keystone to assign to "
                    "users.")
]}
