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

from rally.deploy import engine


class FakeEngine(engine.EngineFactory):
    """FakeEngine doesn't deploy OpenStack it just use existing.

       To use FakeEngine you should put in task deploy config `cloud_config`:
       {'deploy': {'cloud_config': {/* here you should specify endpoints */}}}

       E.g.
       cloud_config: {
           'identity': {
               'url': 'http://localhost/',
               'admin_user': 'amdin'
               ....
           }
       }
    """

    def __init__(self, task, config):
        self.task = task
        self.config = config.get('cloud_config', {})
        # TODO(boris-42): We should verify endpoints here.

    def deploy(self):
        return self.config

    def cleanup(self):
        pass
