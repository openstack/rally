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

"""
Guidelines for writing new hacking checks

 - Use only for Rally specific tests. OpenStack general tests
   should be submitted to the common 'hacking' module.
 - Pick numbers in the range N3xx. Find the current test with
   the highest allocated number and then pick the next value.
 - Keep the test method code in the source file ordered based
   on the N3xx value.
 - List the new rule in the top level HACKING.rst file
 - Add test cases for each new rule to tests/test_hacking.py

"""


def _parse_assert_mock_str(line):
    point = line.find('.assert_')

    if point != -1:
        end_pos = line[point:].find('(') + point
        return point, line[point + 1: end_pos], line[: point]
    else:
        return None, None, None


def check_assert_methods_from_mock(logical_line, filename):
    """Ensure that ``assert_*`` methods from ``mock`` library is used correctly

    N301 - base error number
    N302 - related to nonexistent "assert_called"
    N303 - related to nonexistent "assert_called_once"
    """

    correct_names = ["assert_any_call", "assert_called_once_with",
                     "assert_called_with", "assert_has_calls"]

    if 'tests/' in filename:
        pos, method_name, obj_name = _parse_assert_mock_str(logical_line)

        if pos:
            if method_name not in correct_names:
                error_number = "N301"
                msg = ("%(error_number)s:'%(method)s' is not present in `mock`"
                       " library. %(custom_msg)s For more details, visit "
                       "http://www.voidspace.org.uk/python/mock/ .")

                if method_name == "assert_called":
                    error_number = "N302"
                    custom_msg = ("Maybe, you should try to use "
                                  "'assertTrue(%s.called)' instead." %
                                  obj_name)
                elif method_name == "assert_called_once":
                    # For more details, see a bug in Rally:
                    #    https://bugs.launchpad.net/rally/+bug/1305991
                    error_number = "N303"
                    custom_msg = ("Maybe, you should try to use "
                                  "'assertEqual(1, %(obj_name)s.call_count)' "
                                  "or '%(obj_name)s.assert_called_once_with()'"
                                  " instead." % {"obj_name": obj_name})
                else:
                    custom_msg = ("Correct 'assert_*' methods: '%s'."
                                  % "', '".join(correct_names))

                yield (pos, msg % {
                    "error_number": error_number,
                    "method": method_name,
                    "custom_msg": custom_msg})


def factory(register):
    register(check_assert_methods_from_mock)
