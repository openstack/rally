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

from rally.openstack.common import test
from rally import sshutils


class SshutilsTestCase(test.BaseTestCase):

    def setUp(self):
        super(SshutilsTestCase, self).setUp()
        self.pipe = mock.MagicMock()
        self.pipe.communicate = mock.MagicMock(return_value=(mock.MagicMock(),
                                               mock.MagicMock()))
        self.pipe.returncode = 0
        self.new = mock.MagicMock()
        self.new.PIPE = self.pipe
        self.new.Popen = mock.MagicMock(return_value=self.pipe)

    def test_upload_file(self):
        with mock.patch('rally.sshutils.subprocess', new=self.new) as sp:
            sshutils.upload_file('root', 'example.com', '/tmp/s', '/tmp/d')

        expected = [mock.call.Popen(['scp', '-o',
                                     'StrictHostKeyChecking=no',
                                     '/tmp/s', 'root@example.com:/tmp/d'],
                    stderr=self.pipe),
                    mock.call.PIPE.communicate()]
        self.assertEqual(sp.mock_calls, expected)

    def test_execute_script_no_file(self):
        self.assertRaises(IOError, sshutils.execute_script, 'user', 'host',
                          '/ioerror')

    def test_execute_script(self):
        with mock.patch('rally.sshutils.subprocess', new=self.new) as sp:
            with mock.patch('rally.sshutils.open', create=True) as op:
                sshutils.execute_script('user', 'example.com', '/tmp/s')
        expected = [
            mock.call.check_call(['ssh', '-o', 'StrictHostKeyChecking=no',
                                  'user@example.com', '/bin/sh'], stdin=op())]
        self.assertEqual(sp.mock_calls, expected)

    def test_execute_command(self):
        with mock.patch('rally.sshutils.subprocess', new=self.new) as sp:
            sshutils.execute_command('user', 'host', ['command', 'arg'])
        expected = [
            mock.call.Popen(['ssh', '-o', 'StrictHostKeyChecking=no',
                             'user@host', 'command', 'arg'], stderr=self.pipe),
            mock.call.PIPE.communicate()]
        self.assertEqual(sp.mock_calls, expected)
