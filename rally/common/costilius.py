#
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
#

"""
This module is a storage for different types of workarounds.
"""

from distutils import spawn
import os
import subprocess
import sys

from rally.common.i18n import _LE
from rally import exceptions


try:
    from collections import OrderedDict  # noqa
except ImportError:
    # NOTE(andreykurilin): Python 2.6 issue. OrderedDict is not
    # present in `collections` library.
    from ordereddict import OrderedDict  # noqa


def is_py26():
    return sys.version_info[:2] == (2, 6)


if is_py26():
    import simplejson as json
else:
    import json


def json_loads(*args, **kwargs):
    """Deserialize a str or unicode instance to a Python object.

    'simplejson' is used in Python 2.6 environment, because standard 'json'
    library not include several important features(for example
    'object_pairs_hook', which allows to deserialize input object to
    OrderedDict)
    """

    return json.loads(*args, **kwargs)


def sp_check_output(*popenargs, **kwargs):
    """Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.
    """

    if is_py26():
        # NOTE(andreykurilin): as I said before, support python 26 env is hard
        # task. Subprocess supports check_output function from Python 2.7, so
        # let's copy-paste code of this function from it.
        if "stdout" in kwargs:
            raise ValueError("stdout argument not allowed, "
                             "it will be overridden.")
        process = subprocess.Popen(stdout=subprocess.PIPE,
                                   *popenargs, **kwargs)
        output, unused_err = process.communicate()
        retcode = process.poll()
        if retcode:
            cmd = kwargs.get("args")
            if cmd is None:
                cmd = popenargs[0]
            raise subprocess.CalledProcessError(retcode, cmd, output=output)
        return output
    return subprocess.check_output(*popenargs, **kwargs)


def get_interpreter(python_version):
    """Discovers PATH to find proper python interpreter

    :param python_version: (major, minor) version numbers
    :type python_version: tuple
    """

    if not isinstance(python_version, tuple):
        msg = (_LE("given format of python version `%s` is invalid") %
               python_version)
        raise exceptions.InvalidArgumentsException(msg)

    interpreter_name = "python%s.%s" % python_version
    interpreter = spawn.find_executable(interpreter_name)
    if interpreter:
        return interpreter
    else:
        interpreters = filter(
            os.path.isfile, [os.path.join(p, interpreter_name)
                             for p in os.environ.get("PATH", "").split(":")])
        cmd = "%s -c 'import sys; print(sys.version_info[:2])'"
        for interpreter in interpreters:
            try:
                out = sp_check_output(cmd % interpreter, shell=True)
            except subprocess.CalledProcessError:
                pass
            else:
                if out.strip() == str(python_version):
                    return interpreter
