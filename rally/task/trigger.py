# Copyright 2016: Mirantis Inc.
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

from rally.common import logging
from rally.task import hook

LOG = logging.getLogger(__name__)


class Trigger(hook.HookTrigger):
    """DEPRECATED!!! USE `rally.task.hook.HookTrigger` instead."""

    def __init__(self, *args, **kwargs):
        super(Trigger, self).__init__(*args, **kwargs)
        LOG.warning("Please contact Rally plugin maintainer. The plugin '%s' "
                    "inherits the deprecated base class(Trigger), "
                    "`rally.task.hook.HookTrigger` should be used instead."
                    % self.get_name())

    @property
    def context(self):
        action_name, action_cfg = self.hook_cfg["action"]
        trigger_name, trigger_cfg = self.hook_cfg["trigger"]
        return {"description": self.hook_cfg["description"],
                "name": action_name,
                "args": action_cfg,
                "trigger": {"name": trigger_name,
                            "args": trigger_cfg}}
