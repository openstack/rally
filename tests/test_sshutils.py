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

import mock
import os

from rally import exceptions
from rally import sshutils
from rally import test


class SSHTestCase(test.TestCase):

    def setUp(self):
        super(SSHTestCase, self).setUp()
        self.ssh = sshutils.SSH('example.net', 'root')
        self.channel = mock.Mock()
        self.channel.recv.return_value = 'ok'
        self.channel.recv_stderr.return_value = 'error'
        self.channel.recv_exit_status.return_value = 0
        self.transport = mock.Mock()
        self.transport.open_session = mock.MagicMock(return_value=self.channel)
        self.policy = mock.Mock()
        self.client = mock.Mock()
        self.client.get_transport = mock.MagicMock(return_value=self.transport)

        self.channel.exit_status_ready.return_value = True
        self.channel.recv_ready.side_effect = [True, False, False]
        self.channel.recv_stderr_ready.side_effect = [True, False, False]

    @mock.patch('rally.sshutils.paramiko')
    @mock.patch('rally.sshutils.select')
    def test_generator(self, st, pk):
        pk.SSHClient.return_value = self.client
        st.select.return_value = ([], [], [])

        chunks = list(self.ssh.execute_generator('ps ax'))
        self.assertEqual([(1, 'ok'), (2, 'error')], chunks)

    @mock.patch('rally.sshutils.paramiko')
    @mock.patch('rally.sshutils.select')
    def test_execute(self, st, pk):
        pk.SSHClient.return_value = self.client
        st.select.return_value = ([], [], [])
        stdout, stderr = self.ssh.execute('uname')

        self.assertEqual('', stdout)
        self.assertEqual('', stderr)
        expected = [mock.call.exec_command('uname'),
                    mock.call.recv_ready(),
                    mock.call.recv(4096),
                    mock.call.recv_ready(),
                    mock.call.recv_stderr_ready(),
                    mock.call.recv_stderr(4096),
                    mock.call.recv_ready(),
                    mock.call.recv_stderr_ready(),
                    mock.call.exit_status_ready(),
                    mock.call.recv_exit_status()]

        self.assertEqual(expected, self.channel.mock_calls)

    @mock.patch('rally.sshutils.paramiko')
    def test_upload_file(self, pk):
        pk.AutoAddPolicy.return_value = self.policy
        self.ssh.upload('/tmp/s', '/tmp/d')

        expected = [mock.call.set_missing_host_key_policy(self.policy),
                    mock.call.connect('example.net', username='root',
                                      key_filename=os.path.expanduser(
                                          '~/.ssh/id_rsa'), port=22),
                    mock.call.open_sftp(),
                    mock.call.open_sftp().put('/tmp/s', '/tmp/d'),
                    mock.call.open_sftp().close()]

        self.assertEqual(pk.SSHClient().mock_calls, expected)

    @mock.patch('rally.sshutils.SSH.execute')
    @mock.patch('rally.sshutils.SSH.upload')
    @mock.patch('rally.sshutils.random.choice')
    def test_execute_script_new(self, rc, up, ex):
        rc.return_value = 'a'
        self.ssh.execute_script('/bin/script')

        up.assert_called_once_with('/bin/script', '/tmp/aaaaaaaaaaaaaaaa')
        ex.assert_has_calls([mock.call('/bin/sh /tmp/aaaaaaaaaaaaaaaa'),
                             mock.call('rm /tmp/aaaaaaaaaaaaaaaa')])

    @mock.patch('rally.sshutils.SSH.execute')
    def test_wait(self, ex):
        self.ssh.wait()

    @mock.patch('rally.sshutils.SSH.execute')
    def test_wait_timeout(self, ex):
        ex.side_effect = exceptions.SSHError
        self.assertRaises(exceptions.TimeoutException,
                          self.ssh.wait, 1, 1)
