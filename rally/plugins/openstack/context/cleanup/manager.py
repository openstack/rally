#
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

# NOTE(stpierre): This module is left for backward compatibility.

import sys
import warnings

from rally.plugins.openstack.cleanup import manager

warnings.warn("Module rally.plugins.openstack.context.cleanup.manager has "
              "been moved to rally.plugins.openstack.cleanup.manager, and "
              "will be removed at some point in the future.")

sys.modules["rally.plugins.openstack.context.cleanup.manager"] = manager
