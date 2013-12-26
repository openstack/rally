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

import eventlet
import os
import paramiko
import random
import select
import socket
import string
import time

from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class SSH(object):
    """SSH common functions."""

    def __init__(self, ip, user, port=22, key=None, timeout=1800):
        """Initialize SSH client with ip, username and the default values.

        timeout - the timeout for execution of the command
        """
        self.ip = ip
        self.port = port
        self.user = user
        self.timeout = timeout
        self.client = None
        if key:
            self.key = key
        else:
            self.key = os.path.expanduser('~/.ssh/id_rsa')

    def _get_ssh_connection(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(self.ip, username=self.user,
                            key_filename=self.key, port=self.port)

    def _is_timed_out(self, start_time):
        return (time.time() - self.timeout) > start_time

    def execute(self, *cmd, **kwargs):
        """Execute the specified command on the server.

        Return tuple (stdout, stderr).

        :param *cmd:       Command and arguments to be executed.
        :param get_stdout: Collect stdout data. Boolean.
        :param get_stderr: Collect stderr data. Boolean.

        """
        get_stdout = kwargs.get("get_stdout", False)
        get_stderr = kwargs.get("get_stderr", False)
        stdout = ''
        stderr = ''
        for chunk in self.execute_generator(*cmd, get_stdout=get_stdout,
                                            get_stderr=get_stderr):
            if chunk[0] == 1:
                stdout += chunk[1]
            elif chunk[0] == 2:
                stderr += chunk[1]
        return (stdout, stderr)

    def execute_generator(self, *cmd, **kwargs):
        """Execute the specified command on the server.

        Return generator. Stdout and stderr data can be collected by chunks.

        :param *cmd:       Command and arguments to be executed.
        :param get_stdout: Collect stdout data. Boolean.
        :param get_stderr: Collect stderr data. Boolean.

        """
        get_stdout = kwargs.get("get_stdout", True)
        get_stderr = kwargs.get("get_stderr", True)
        self._get_ssh_connection()
        cmd = ' '.join(cmd)
        transport = self.client.get_transport()
        channel = transport.open_session()
        channel.fileno()
        channel.exec_command(cmd)
        channel.shutdown_write()
        poll = select.poll()
        poll.register(channel, select.POLLIN)
        start_time = time.time()
        while True:
            ready = poll.poll(16)
            if not any(ready):
                if not self._is_timed_out(start_time):
                    continue
                raise exceptions.TimeoutException('SSH Timeout')
            if not ready[0]:
                continue
            out_chunk = err_chunk = None
            if channel.recv_ready():
                out_chunk = channel.recv(4096)
                if get_stdout:
                    yield (1, out_chunk)
                LOG.debug("stdout: %s" % out_chunk)
            if channel.recv_stderr_ready():
                err_chunk = channel.recv_stderr(4096)
                if get_stderr:
                    yield (2, err_chunk)
                LOG.debug("stderr: %s" % err_chunk)
            if channel.closed and not err_chunk and not out_chunk:
                break
        exit_status = channel.recv_exit_status()
        if 0 != exit_status:
            raise exceptions.SSHError(
                'SSHExecCommandFailed with exit_status %s'
                % exit_status)
        self.client.close()

    def upload(self, source, destination):
        """Upload the specified file to the server."""
        if destination.startswith('~'):
            destination = '/home/' + self.user + destination[1:]
        self._get_ssh_connection()
        ftp = self.client.open_sftp()
        ftp.put(os.path.expanduser(source), destination)
        ftp.close()

    def execute_script(self, script, enterpreter='/bin/sh'):
        """Execute the specified local script on the remote server."""
        destination = '/tmp/' + ''.join(
            random.choice(string.lowercase) for i in range(16))

        self.upload(script, destination)
        self.execute('%s %s' % (enterpreter, destination))
        self.execute('rm %s' % destination)

    def wait(self, timeout=120, interval=1):
        """Wait for the host will be available via ssh."""
        with eventlet.timeout.Timeout(timeout, exceptions.TimeoutException):
            while True:
                try:
                    return self.execute('uname')
                except (socket.error, exceptions.SSHError) as e:
                    LOG.debug(
                        _('Ssh is still unavailable. (Exception was: %r)') % e)
                    eventlet.sleep(interval)
