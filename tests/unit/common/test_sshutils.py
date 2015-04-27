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

from rally.common import sshutils
from tests.unit import test


class FakeParamikoException(Exception):
    pass


class SSHTestCase(test.TestCase):
    """Test all small SSH methods."""

    def setUp(self):
        super(SSHTestCase, self).setUp()
        self.ssh = sshutils.SSH("root", "example.net")

    @mock.patch("rally.common.sshutils.SSH._get_pkey")
    def test_construct(self, m_pkey):
        m_pkey.return_value = "pkey"
        ssh = sshutils.SSH("root", "example.net", port=33, pkey="key",
                           key_filename="kf", password="secret")
        m_pkey.assert_called_once_with("key")
        self.assertEqual("root", ssh.user)
        self.assertEqual("example.net", ssh.host)
        self.assertEqual(33, ssh.port)
        self.assertEqual("pkey", ssh.pkey)
        self.assertEqual("kf", ssh.key_filename)
        self.assertEqual("secret", ssh.password)

    def test_construct_default(self):
        self.assertEqual("root", self.ssh.user)
        self.assertEqual("example.net", self.ssh.host)
        self.assertEqual(22, self.ssh.port)
        self.assertIsNone(self.ssh.pkey)
        self.assertIsNone(self.ssh.key_filename)
        self.assertIsNone(self.ssh.password)

    @mock.patch("rally.common.sshutils.paramiko")
    def test__get_pkey_invalid(self, m_paramiko):
        m_paramiko.SSHException = FakeParamikoException
        rsa = m_paramiko.rsakey.RSAKey
        dss = m_paramiko.dsskey.DSSKey
        rsa.from_private_key.side_effect = m_paramiko.SSHException
        dss.from_private_key.side_effect = m_paramiko.SSHException
        self.assertRaises(sshutils.SSHError, self.ssh._get_pkey, "key")

    @mock.patch("rally.common.sshutils.six.moves")
    @mock.patch("rally.common.sshutils.paramiko")
    def test__get_pkey_dss(self, m_paramiko, m_stringio):
        m_paramiko.SSHException = FakeParamikoException
        m_stringio.StringIO.return_value = "string_key"
        m_paramiko.dsskey.DSSKey.from_private_key.return_value = "dss_key"
        rsa = m_paramiko.rsakey.RSAKey
        rsa.from_private_key.side_effect = m_paramiko.SSHException
        key = self.ssh._get_pkey("key")
        dss_calls = m_paramiko.dsskey.DSSKey.from_private_key.mock_calls
        self.assertEqual([mock.call("string_key")], dss_calls)
        self.assertEqual(key, "dss_key")
        m_stringio.StringIO.assert_called_once_with("key")

    @mock.patch("rally.common.sshutils.six.moves")
    @mock.patch("rally.common.sshutils.paramiko")
    def test__get_pkey_rsa(self, m_paramiko, m_stringio):
        m_paramiko.SSHException = FakeParamikoException
        m_stringio.StringIO.return_value = "string_key"
        m_paramiko.rsakey.RSAKey.from_private_key.return_value = "rsa_key"
        dss = m_paramiko.dsskey.DSSKey
        dss.from_private_key.side_effect = m_paramiko.SSHException
        key = self.ssh._get_pkey("key")
        rsa_calls = m_paramiko.rsakey.RSAKey.from_private_key.mock_calls
        self.assertEqual([mock.call("string_key")], rsa_calls)
        self.assertEqual(key, "rsa_key")
        m_stringio.StringIO.assert_called_once_with("key")

    @mock.patch("rally.common.sshutils.SSH._get_pkey")
    @mock.patch("rally.common.sshutils.paramiko")
    def test__get_client(self, m_paramiko, m_pkey):
        m_pkey.return_value = "key"
        fake_client = mock.Mock()
        m_paramiko.SSHClient.return_value = fake_client
        m_paramiko.AutoAddPolicy.return_value = "autoadd"

        ssh = sshutils.SSH("admin", "example.net", pkey="key")
        client = ssh._get_client()

        self.assertEqual(fake_client, client)
        client_calls = [
            mock.call.set_missing_host_key_policy("autoadd"),
            mock.call.connect("example.net", username="admin",
                              port=22, pkey="key", key_filename=None,
                              password=None, timeout=1),
        ]
        self.assertEqual(client_calls, client.mock_calls)

    def test_close(self):
        with mock.patch.object(self.ssh, "_client") as m_client:
            self.ssh.close()
        m_client.close.assert_called_once_with()
        self.assertFalse(self.ssh._client)

    @mock.patch("rally.common.sshutils.six.moves")
    def test_execute(self, m_stringio):
        m_stringio.StringIO.side_effect = stdio = [mock.Mock(), mock.Mock()]
        stdio[0].read.return_value = "stdout fake data"
        stdio[1].read.return_value = "stderr fake data"
        with mock.patch.object(self.ssh, "run", return_value=0) as m_run:
            status, stdout, stderr = self.ssh.execute("cmd",
                                                      stdin="fake_stdin",
                                                      timeout=43)
        m_run.assert_called_once_with("cmd", stdin="fake_stdin",
                                      stdout=stdio[0],
                                      stderr=stdio[1], timeout=43,
                                      raise_on_error=False)
        self.assertEqual(0, status)
        self.assertEqual("stdout fake data", stdout)
        self.assertEqual("stderr fake data", stderr)

    @mock.patch("rally.common.sshutils.time")
    def test_wait_timeout(self, m_time):
        m_time.time.side_effect = [1, 50, 150]
        self.ssh.execute = mock.Mock(side_effect=[sshutils.SSHError,
                                                  sshutils.SSHError,
                                                  0])
        self.assertRaises(sshutils.SSHTimeout, self.ssh.wait)
        self.assertEqual([mock.call("uname")] * 2, self.ssh.execute.mock_calls)

    @mock.patch("rally.common.sshutils.time")
    def test_wait(self, m_time):
        m_time.time.side_effect = [1, 50, 100]
        self.ssh.execute = mock.Mock(side_effect=[sshutils.SSHError,
                                                  sshutils.SSHError,
                                                  0])
        self.ssh.wait()
        self.assertEqual([mock.call("uname")] * 3, self.ssh.execute.mock_calls)


class SSHRunTestCase(test.TestCase):
    """Test SSH.run method in different aspects.

    Also tested method "execute".
    """

    def setUp(self):
        super(SSHRunTestCase, self).setUp()

        self.fake_client = mock.Mock()
        self.fake_session = mock.Mock()
        self.fake_transport = mock.Mock()

        self.fake_transport.open_session.return_value = self.fake_session
        self.fake_client.get_transport.return_value = self.fake_transport

        self.fake_session.recv_ready.return_value = False
        self.fake_session.recv_stderr_ready.return_value = False
        self.fake_session.send_ready.return_value = False
        self.fake_session.exit_status_ready.return_value = True
        self.fake_session.recv_exit_status.return_value = 0

        self.ssh = sshutils.SSH("admin", "example.net")
        self.ssh._get_client = mock.Mock(return_value=self.fake_client)

    @mock.patch("rally.common.sshutils.select")
    def test_execute(self, m_select):
        m_select.select.return_value = ([], [], [])
        self.fake_session.recv_ready.side_effect = [1, 0, 0]
        self.fake_session.recv_stderr_ready.side_effect = [1, 0]
        self.fake_session.recv.return_value = "ok"
        self.fake_session.recv_stderr.return_value = "error"
        self.fake_session.exit_status_ready.return_value = 1
        self.fake_session.recv_exit_status.return_value = 127
        self.assertEqual((127, "ok", "error"), self.ssh.execute("cmd"))
        self.fake_session.exec_command.assert_called_once_with("cmd")

    @mock.patch("rally.common.sshutils.select")
    def test_execute_args(self, m_select):
        m_select.select.return_value = ([], [], [])
        self.fake_session.recv_ready.side_effect = [1, 0, 0]
        self.fake_session.recv_stderr_ready.side_effect = [1, 0]
        self.fake_session.recv.return_value = "ok"
        self.fake_session.recv_stderr.return_value = "error"
        self.fake_session.exit_status_ready.return_value = 1
        self.fake_session.recv_exit_status.return_value = 127

        result = self.ssh.execute(["cmd", "arg1", "arg2 with space"])
        self.assertEqual((127, "ok", "error"), result)
        self.fake_session.exec_command.assert_called_once_with(
            "cmd arg1 'arg2 with space'")

    @mock.patch("rally.common.sshutils.select")
    def test_run(self, m_select):
        m_select.select.return_value = ([], [], [])
        self.assertEqual(0, self.ssh.run("cmd"))

    @mock.patch("rally.common.sshutils.select")
    def test_run_nonzero_status(self, m_select):
        m_select.select.return_value = ([], [], [])
        self.fake_session.recv_exit_status.return_value = 1
        self.assertRaises(sshutils.SSHError, self.ssh.run, "cmd")
        self.assertEqual(1, self.ssh.run("cmd", raise_on_error=False))

    @mock.patch("rally.common.sshutils.select")
    def test_run_stdout(self, m_select):
        m_select.select.return_value = ([], [], [])
        self.fake_session.recv_ready.side_effect = [True, True, False]
        self.fake_session.recv.side_effect = ["ok1", "ok2"]
        stdout = mock.Mock()
        self.ssh.run("cmd", stdout=stdout)
        self.assertEqual([mock.call("ok1"), mock.call("ok2")],
                         stdout.write.mock_calls)

    @mock.patch("rally.common.sshutils.select")
    def test_run_stderr(self, m_select):
        m_select.select.return_value = ([], [], [])
        self.fake_session.recv_stderr_ready.side_effect = [True, False]
        self.fake_session.recv_stderr.return_value = "error"
        stderr = mock.Mock()
        self.ssh.run("cmd", stderr=stderr)
        stderr.write.assert_called_once_with("error")

    @mock.patch("rally.common.sshutils.select")
    def test_run_stdin(self, m_select):
        """Test run method with stdin.

        Third send call was called with "e2" because only 3 bytes was sent
        by second call. So remainig 2 bytes of "line2" was sent by third call.
        """
        m_select.select.return_value = ([], [], [])
        self.fake_session.exit_status_ready.side_effect = [0, 0, 0, True]
        self.fake_session.send_ready.return_value = True
        self.fake_session.send.side_effect = [5, 3, 2]
        fake_stdin = mock.Mock()
        fake_stdin.read.side_effect = ["line1", "line2", ""]
        fake_stdin.closed = False

        def close():
            fake_stdin.closed = True
        fake_stdin.close = mock.Mock(side_effect=close)
        self.ssh.run("cmd", stdin=fake_stdin)
        call = mock.call
        send_calls = [call("line1"), call("line2"), call("e2")]
        self.assertEqual(send_calls, self.fake_session.send.mock_calls)

    @mock.patch("rally.common.sshutils.select")
    def test_run_select_error(self, m_select):
        self.fake_session.exit_status_ready.return_value = False
        m_select.select.return_value = ([], [], [True])
        self.assertRaises(sshutils.SSHError, self.ssh.run, "cmd")

    @mock.patch("rally.common.sshutils.time")
    @mock.patch("rally.common.sshutils.select")
    def test_run_timemout(self, m_select, m_time):
        m_time.time.side_effect = [1, 3700]
        m_select.select.return_value = ([], [], [])
        self.fake_session.exit_status_ready.return_value = False
        self.assertRaises(sshutils.SSHTimeout, self.ssh.run, "cmd")
