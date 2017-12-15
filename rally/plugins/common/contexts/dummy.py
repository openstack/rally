# Copyright 2015: Mirantis Inc.
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

from rally import consts
from rally import exceptions
from rally.task import context


@context.configure(name="dummy_context", order=750)
class DummyContext(context.Context):
    """Dummy context."""
    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "properties": {
            "fail_setup": {"type": "boolean"},
            "fail_cleanup": {"type": "boolean"}
        },
    }

    def setup(self):
        if self.config.get("fail_setup", False):
            raise exceptions.RallyException("Oops...setup is failed")

    def cleanup(self):
        if self.config.get("fail_cleanup", False):
            raise exceptions.RallyException("Oops...cleanup is failed")
