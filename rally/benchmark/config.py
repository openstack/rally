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

import ConfigParser
import os


class CloudConfigManager(ConfigParser.RawConfigParser, object):

    _DEFAULT_CLOUD_CONFIG = {
        'identity': {
            'url': 'http://localhost/',
            'uri': 'http://localhost:5000/v2.0/',
            'admin_username': 'admin',
            'admin_password': 'admin',
            'admin_tenant_name': 'service',
            'region': 'RegionOne',
            'strategy': 'keystone',
            'catalog_type': 'identity',
            'disable_ssl_certificate_validation': False
        },
        'compute': {
            'controller_nodes': 'localhost',
            'controller_nodes_name': 'localhost',
            'controller_node_ssh_user': 'root',
            'controller_node_ssh_password': 'r00tme',
            'compute_nodes': 'localhost',
            'path_to_private_key': os.path.expanduser('~/.ssh/id_rsa'),
            'image_name': 'cirros-0.3.1-x86_64-uec',
            'image_ssh_user': 'cirros',
            'image_alt_ssh_user': 'cirros',
            'flavor_ref': 1,
            'allow_tenant_isolation': True,
            'ssh_timeout': 300,
            'ssh_channel_timeout': 60,
            'build_interval': 3,
            'build_timeout': 300,
            'enabled_services': 'nova-cert, nova-consoleauth, ' +
                                'nova-scheduler, nova-conductor, ' +
                                'nova-compute, nova-network, ' +
                                'nova-compute, nova-network',
            'run_ssh': False,
            'catalog_type': 'compute',
            'allow_tenant_reuse': True,
            'create_image_enabled': True
        },
        'network': {
            'api_version': '2.0',
            'tenant_network_mask_bits': 28,
            'tenant_network_cidr': '10.0.0.0/24',
            'tenant_networks_reachable': True,
            'neutron_available': False,
            'catalog_type': 'network'
        },
        'image': {
            'api_version': '1',
            'http_image': 'http://download.cirros-cloud.net/0.3.1/' +
                          'cirros-0.3.1-x86_64-uec.tar.gz',
            'catalog_type': 'image'
        },
        'volume': {
            'multi_backend_enabled': 'false',
            'backend1_name': 'BACKEND_1',
            'backend2_name': 'BACKEND_2',
            'build_timeout': 300,
            'build_interval': 3,
            'catalog_type': 'volume'
        },
        'object-storage': {
            'container_sync_interval': 5,
            'container_sync_timeout': 120,
            'catalog_type': 'object-store'
        }
    }

    def __init__(self, config=None):
        """Initializes the cloud config manager with the default values and
        (if given) with a config.

        :param config: Path to the config file or a two-level dictionary
                       containing the config contents
        """
        super(CloudConfigManager, self).__init__()
        self.read_from_dict(self._DEFAULT_CLOUD_CONFIG)
        if config:
            if isinstance(config, basestring):
                self.read(config)
            elif isinstance(config, dict):
                self.read_from_dict(config)

    def read_from_dict(self, dct, replace=True):
        """Reads the config from a dictionary.

        :param dct: The config represented as a two-level dictionary: the
                    top-level keys should be section names while the keys on
                    the second level should represent option names
        :param replace: True to replace already existing options while reading
                        the config; False to keep old values
        """
        for section_name, section in dct.iteritems():
            if not self.has_section(section_name):
                self.add_section(section_name)
            for opt in section:
                if not self.has_option(section_name, opt) or replace:
                    self.set(section_name, opt, section[opt])

    def to_dict(self):
        res = {}
        for section in self.sections():
            res[section] = dict(self.items(section))
        return res


test_config_schema = {
    "type": "object",
    "$schema": "http://json-schema.org/draft-03/schema",
    "properties": {
        "verify": {
            "type": "array"
        },
        "benchmark": {
            "type": "object",
            "patternProperties": {
                ".*": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "args": {"type": "object"},
                            "init": {"type": "object"},
                            "execution": {"enum": ["continuous"]},
                            "config": {
                                "type": "object",
                                "properties": {
                                    "times": {"type": "number"},
                                    "duration": {"type": "number"},
                                    "active_users": {"type": "number"},
                                    "tenants": {"type": "number"},
                                    "users_per_tenant": {"type": "number"},
                                    "timeout": {"type": "number"}
                                },
                                "additionalProperties": False
                            }
                        },
                        "additionalProperties": False
                    }
                }
            }
        }
    },
    "additionalProperties": False
}
