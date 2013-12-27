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


class DummyEngine(engine.EngineFactory):
    """DummyEngine doesn't deploy OpenStack it just use existing.

       To use DummyEngine you should put in task deploy config `cloud_config`:
       {'deploy': {'cloud_config': {/* here you should specify endpoints */}}}

       E.g.
       cloud_config: {
           'identity': {
               'url': 'http://localhost/',
               'admin_username': 'admin'
               ....
           }
       }
    """

    IDENTITY_SCHEMA = {
        'type': 'object',
        'properties': {
            'uri': {'type': 'string'},
            'admin_username': {'type': 'string'},
            'admin_password': {'type': 'string'},
            'admin_tenant_name': {'type': 'string'},
        },
        'required': ['uri', 'admin_username', 'admin_password',
                     'admin_tenant_name'],
    }

    CONFIG_SCHEMA = {
        'type': 'object',
        'properties': {
            'cloud_config': {
                'type': 'object',
                'properties': {
                    'identity': IDENTITY_SCHEMA,
                },
                'required': ['identity'],
            },
        },
        'required': ['cloud_config'],
    }

    def deploy(self):
        return self.deployment['config'].get('cloud_config', {})

    def cleanup(self):
        pass
