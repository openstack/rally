# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""oslo.i18n integration module for rally.

See https://docs.openstack.org/oslo.i18n/latest/user/usage.html .

"""

from rally.common import logging

LOG = logging.getLogger(__name__)
LOG.warning("rally.common.i18n module is deprecated and is going to be "
            "removed. Please do not import it.")


def _do_nothing(msg):
    return msg


# The primary translation function using the well-known name "_"
_ = _do_nothing

# Translators for log levels.
#
# The abbreviated names are meant to reflect the usual use of a short
# name like '_'. The "L" is for "log" and the other letter comes from
# the level.
_LI = _do_nothing
_LW = _do_nothing
_LE = _do_nothing
_LC = _do_nothing
