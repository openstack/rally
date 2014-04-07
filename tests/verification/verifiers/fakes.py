# Copyright 2014: Mirantis Inc.
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


FAKE_CONFIG = {
    'DEFAULT': [
        ('lock_path', 'fake_lock_path'),
        ('debug', 'True'),
        ('log_file', 'tempest.log'),
        ('use_stderr', 'False')],
    'boto': [
        ('http_socket_timeout', '30'),
        ('build_timeout', '196'),
        ('build_interval', '1'),
        ('instance_type', 'm1.nano'),
        ('ssh_user', 'cirros')],
    'compute': [
        ('allow_tenant_isolation', 'False'),
        ('ip_version_for_ssh', '4'),
        ('image_ssh_user', 'cirros'),
        ('ssh_connect_method', 'floating'),
        ('flavor_ref', 'fake_flavor_ref'),
        ('image_ref_alt', 'fake_image_ref_alt'),
        ('build_interval', '1'),
        ('change_password_available', 'False'),
        ('use_block_migration_for_live_migration', 'False'),
        ('live_migration_available', 'False'),
        ('image_alt_ssh_user', 'cirros'),
        ('build_timeout', '196'),
        ('network_for_ssh', 'private'),
        ('ssh_user', 'cirros'),
        ('ssh_timeout', '196'),
        ('image_ref', 'fake_image_ref'),
        ('flavor_ref_alt', 'fake_flavor_ref_alt')],
    'cli': [('cli_dir', '/usr/local/bin')],
    'scenario': [('large_ops_number', '0')],
    'compute-admin': [('password', 'fake_password')],
    'volume': [
        ('build_interval', '1'),
        ('build_timeout', '196')],
    'network-feature-enabled': [('api_extensions', 'all')],
    'service_available': [
        ('heat', 'True'),
        ('ironic', 'False'),
        ('marconi', 'False'),
        ('swift', 'False'),
        ('glance', 'True'),
        ('ceilometer', 'False'),
        ('trove', 'False'),
        ('nova', 'True'),
        ('horizon', 'True'),
        ('debug', 'True'),
        ('cinder', 'True'),
        ('log_file', 'tempest.log'),
        ('neutron', 'True'),
        ('savanna', 'False')],
    'identity': [
        ('username', 'fake_username'),
        ('password', 'fake_password'),
        ('tenant_name', 'fake_tenant_name'),
        ('admin_tenant_name', 'fake_tenant_name'),
        ('uri', 'fake_uri'),
        ('uri_v3', 'fake_uri'),
        ('admin_username', 'fake_username'),
        ('admin_password', 'fake_password')],
    'network': [
        ('tenant_networks_reachable', 'false'),
        ('default_network', '10.0.0.0/24'),
        ('api_version', '2.0')]
}


def get_fake_test_case():
    return {
        'total': {
            'failures': 1,
            'tests': 2,
            'errors': 0,
            'time': 1.412},
        'test_cases': {
            'fake.failed.TestCase.with_StringException[gate,negative]': {
                'name':
                    'fake.failed.TestCase.with_StringException[gate,negative]',
                'failure': {
                    'type': 'testtools.testresult.real._StringException',
                    'log':
                        ('_StringException: Empty attachments:\nOops...There '
                         'was supposed to be fake traceback, but it is not.\n')
                },
                'time': 0.706,
                'status': 'FAIL'},
            'fake.successful.TestCase.fake_test[gate,negative]': {
                'name': 'fake.successful.TestCase.fake_test[gate,negative]',
                'time': 0.706,
                'status': 'OK'
            }
        }
    }
