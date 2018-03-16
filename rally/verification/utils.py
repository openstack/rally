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
import subprocess

import six
from six.moves import configparser

from rally.common import logging
from rally.utils import encodeutils


LOG = logging.getLogger(__name__)


def check_output(*args, **kwargs):
    """Run command with arguments and return its output.

    If the exit code was non-zero it raises a CalledProcessError. The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The difference between check_output from subprocess package and this
    function:

      * Additional arguments:
        - "msg_on_err" argument. It is a message that should be written in case
          of error. Reduces a number of try...except blocks
        - "debug_output" argument(Defaults to True). Print or not output to
          LOG.debug
      * stderr is hardcoded to stdout
      * In case of error, prints failed command and output to LOG.error
      * Prints output to LOG.debug

    """
    msg_on_err = kwargs.pop("msg_on_err", None)
    debug_output = kwargs.pop("debug_output", True)

    kwargs["stderr"] = subprocess.STDOUT
    try:
        output = subprocess.check_output(*args, **kwargs)
    except subprocess.CalledProcessError as exc:
        if msg_on_err:
            LOG.error(msg_on_err)
        LOG.error("Failed cmd: '%s'" % exc.cmd)
        LOG.error("Error output: '%s'" % encodeutils.safe_decode(exc.output))
        raise

    if output and debug_output:
        LOG.debug("Subprocess output: '%s'" % encodeutils.safe_decode(output))

    return output


def create_dir(dir_path):
    if not os.path.isdir(dir_path):
        os.makedirs(dir_path)

    return dir_path


def extend_configfile(extra_options, conf_path):
    conf_object = configparser.ConfigParser()
    conf_object.read(conf_path)

    conf_object = add_extra_options(extra_options, conf_object)
    with open(conf_path, "w") as configfile:
        conf_object.write(configfile)

    raw_conf = six.StringIO()
    conf_object.write(raw_conf)

    return raw_conf.getvalue()


def add_extra_options(extra_options, conf_object):
    for section in extra_options:
        if section not in (conf_object.sections() + ["DEFAULT"]):
            conf_object.add_section(section)
        for option, value in extra_options[section].items():
            conf_object.set(section, option, value)

    return conf_object
