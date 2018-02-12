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
    cfg.IntOpt("resource_deletion_timeout",
               default=600,
               deprecated_group="cleanup",
               help="A timeout in seconds for deleting resources"),
    cfg.IntOpt("cleanup_threads",
               default=20,
               deprecated_group="cleanup",
               help="Number of cleanup threads to run")
]}
