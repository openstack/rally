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
from StringIO import StringIO
import time

from rally import exceptions
from rally.openstack.common.gettextutils import _
from rally.openstack.common import log as logging

LOG = logging.getLogger(__name__)


class SSH(object):
    """SSH common functions."""
    STDOUT_INDEX = 0
    STDERR_INDEX = 1

    def __init__(self, ip, user, port=22, key=None, key_type="file",
                 timeout=1800):
        """Initialize SSH client with ip, username and the default values.

        timeout - the timeout for execution of the command
        key - path to private key file, or string containing actual key
        key_type - "file" for key path, "string" for actual key
        """
        self.ip = ip
        self.port = port
        self.user = user
        self.timeout = timeout
        self.client = None
        self.key = key
        self.key_type = key_type
        if not self.key:
            #Guess location of user's private key if no key is specified.
            self.key = os.path.expanduser('~/.ssh/id_rsa')

    def _get_ssh_connection(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connect_params = {
            'hostname': self.ip,
            'port': self.port,
            'username': self.user
        }

        # NOTE(hughsaunders): Set correct paramiko parameter names for each
        # method of supplying a key.
        if self.key_type == 'file':
            connect_params['key_filename'] = self.key
        else:
            connect_params['pkey'] = paramiko.RSAKey(
                    file_obj=StringIO(self.key))

        self.client.connect(**connect_params)

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
        session = transport.open_session()
        session.exec_command(cmd)
        start_time = time.time()

        while True:
            errors = select.select([session], [], [], 4)[2]

            if session.recv_ready():
                data = session.recv(4096)
                LOG.debug(data)
                if get_stdout:
                    yield (1, data)
                continue

            if session.recv_stderr_ready():
                data = session.recv_stderr(4096)
                LOG.debug(data)
                if get_stderr:
                    yield (2, data)
                continue

            if errors or session.exit_status_ready():
                break

            if self._is_timed_out(start_time):
                raise exceptions.TimeoutException('SSH Timeout')

        exit_status = session.recv_exit_status()
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

    def execute_script(self, script, interpreter='/bin/sh',
                       get_stdout=False, get_stderr=False):
        """Execute the specified local script on the remote server."""
        destination = '/tmp/' + ''.join(
            random.choice(string.lowercase) for i in range(16))

        self.upload(script, destination)
        streams = self.execute('%s %s' % (interpreter, destination),
                               get_stdout=get_stdout, get_stderr=get_stderr)
        self.execute('rm %s' % destination)
        return streams

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
