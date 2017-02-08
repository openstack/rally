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

import os
import tempfile
import zipfile


def _read_env_file(path, except_env=None):
    """Read the environment variable file.

    :param path: the path of the file
    :param except_env: the environment variable to avoid in the output

    :returns: the content of the original file except the line starting with
    the except_env parameter
    """
    output = []
    if os.path.exists(path):
        with open(path, "r") as env_file:
            content = env_file.readlines()
            for line in content:
                if except_env is None or not line.startswith("%s=" %
                                                             except_env):
                    output.append(line)
    return output


def load_env_file(path):
    """Load the environment variable file into os.environ.

    :param path: the path of the file
    """
    if os.path.exists(path):
        content = _read_env_file(path)
        for line in content:
            (key, sep, value) = line.partition("=")
            os.environ[key] = value.rstrip()


def _rewrite_env_file(path, initial_content):
    """Rewrite the environment variable file.

    :param path: the path of the file
    :param initial_content: the original content of the file
    """
    with open(path, "w+") as env_file:
        for line in initial_content:
            env_file.write(line)


def update_env_file(path, env_key, env_value):
    """Update the environment variable file.

    :param path: the path of the file
    :param env_key: the key to update
    :param env_value: the value of the property to update
    """
    output = _read_env_file(path, env_key)
    output.append("%s=%s" % (env_key, env_value))
    _rewrite_env_file(path, output)


def update_globals_file(key, value):
    """Update the globals variables file.

    :param key: the key to update
    :param value: the value to update
    """
    dir = os.path.expanduser("~/.rally/")
    if not os.path.exists(dir):
        os.makedirs(dir)
    expanded_path = os.path.join(dir, "globals")
    update_env_file(expanded_path, key, "%s\n" % value)


def pack_dir(source_directory, zip_name=None):
    """Archive content of the directory into .zip

    Zip content of the source folder excluding root directory
    into zip archive. When zip_name is specified, it would be used
    as a destination for the archive. Otherwise method would
    try to use temporary file as a destination for the archive.

    :param source_directory: root of the newly created archive.
        Directory is added recursively.
    :param zip_name: destination zip file name.
    :raises IOError: whenever there are IO issues.
    :returns: path to the newly created zip archive either specified via
        zip_name or a temporary one.
    """

    if not zip_name:
        fp = tempfile.NamedTemporaryFile(delete=False)
        zip_name = fp.name
    zipf = zipfile.ZipFile(zip_name, mode="w")
    try:
        for root, dirs, files in os.walk(source_directory):
            for f in files:
                abspath = os.path.join(root, f)
                relpath = os.path.relpath(abspath, source_directory)
                zipf.write(abspath, relpath)
    finally:
        zipf.close()
    return zip_name
