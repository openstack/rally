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

from oslo_config import cfg

OPTS = {"tempest": [
    cfg.StrOpt("img_url",
               default="http://download.cirros-cloud.net/"
                       "0.3.5/cirros-0.3.5-x86_64-disk.img",
               help="image URL"),
    cfg.StrOpt("img_disk_format",
               default="qcow2",
               help="Image disk format to use when creating the image"),
    cfg.StrOpt("img_container_format",
               default="bare",
               help="Image container format to use when creating the image"),
    cfg.StrOpt("img_name_regex",
               default="^.*(cirros|testvm).*$",
               help="Regular expression for name of a public image to "
                    "discover it in the cloud and use it for the tests. "
                    "Note that when Rally is searching for the image, case "
                    "insensitive matching is performed. Specify nothing "
                    "('img_name_regex =') if you want to disable discovering. "
                    "In this case Rally will create needed resources by "
                    "itself if the values for the corresponding config "
                    "options are not specified in the Tempest config file"),
    cfg.StrOpt("swift_operator_role",
               default="Member",
               help="Role required for users "
                    "to be able to create Swift containers"),
    cfg.StrOpt("swift_reseller_admin_role",
               default="ResellerAdmin",
               help="User role that has reseller admin"),
    cfg.StrOpt("heat_stack_owner_role",
               default="heat_stack_owner",
               help="Role required for users "
                    "to be able to manage Heat stacks"),
    cfg.StrOpt("heat_stack_user_role",
               default="heat_stack_user",
               help="Role for Heat template-defined users"),
    cfg.IntOpt("flavor_ref_ram",
               default="64",
               help="Primary flavor RAM size used by most of the test cases"),
    cfg.IntOpt("flavor_ref_alt_ram",
               default="128",
               help="Alternate reference flavor RAM size used by test that"
               "need two flavors, like those that resize an instance"),
    cfg.IntOpt("heat_instance_type_ram",
               default="64",
               help="RAM size flavor used for orchestration test cases")
]}
