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

import uuid

import six


def _format_uuid_string(string):
    return (string.replace("urn:", "")
                  .replace("uuid:", "")
                  .strip("{}")
                  .replace("-", "")
                  .lower())


def is_uuid_like(val):
    """Returns validation of a value as a UUID.

    :param val: Value to verify
    :type val: string
    :returns: bool

    .. versionchanged:: 1.1.1
       Support non-lowercase UUIDs.
    """
    try:
        return str(uuid.UUID(val)).replace("-", "") == _format_uuid_string(val)
    except (TypeError, ValueError, AttributeError):
        return False


TRUE_STRINGS = ("1", "t", "true", "on", "y", "yes")
FALSE_STRINGS = ("0", "f", "false", "off", "n", "no")


def bool_from_string(subject, strict=False, default=False):
    """Interpret a subject as a boolean.

    A subject can be a boolean, a string or an integer. Boolean type value
    will be returned directly, otherwise the subject will be converted to
    a string. A case-insensitive match is performed such that strings
    matching 't','true', 'on', 'y', 'yes', or '1' are considered True and,
    when `strict=False`, anything else returns the value specified by
    'default'.

    Useful for JSON-decoded stuff and config file parsing.

    If `strict=True`, unrecognized values, including None, will raise a
    ValueError which is useful when parsing values passed in from an API call.
    Strings yielding False are 'f', 'false', 'off', 'n', 'no', or '0'.
    """
    if isinstance(subject, bool):
        return subject
    if not isinstance(subject, six.string_types):
        subject = six.text_type(subject)

    lowered = subject.strip().lower()

    if lowered in TRUE_STRINGS:
        return True
    elif lowered in FALSE_STRINGS:
        return False
    elif strict:
        acceptable = ", ".join(
            "'%s'" % s for s in sorted(TRUE_STRINGS + FALSE_STRINGS))
        msg = ("Unrecognized value '%(val)s', acceptable values are:"
               " %(acceptable)s") % {"val": subject,
                                     "acceptable": acceptable}
        raise ValueError(msg)
    else:
        return default


def format_float_to_str(num):
    """Format number into human-readable float format.

     More precise it convert float into the string and remove redundant
     zeros from the floating part.
     It will format the number by the following examples:
     0.0000001 -> 0.0
     0.000000 -> 0.0
     37 -> 37.0
     1.0000001 -> 1.0
     1.0000011 -> 1.000001
     1.0000019 -> 1.000002

    :param num: Number to be formatted
    :return: string representation of the number
    """

    num_str = "%f" % num
    float_part = num_str.split(".")[1].rstrip("0") or "0"
    return num_str.split(".")[0] + "." + float_part
