# Copyright 2015: Red Hat, Inc.
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

from rally import exceptions


class FunctionalMixin(object):
    """Functional assertions.

    The Rally core team deliberately decided not to use an existing framework
    for this such a `testtools`.

    Using 'testtools' would introduce the following problems:
    - Rally production code works with testing tools code that is not designed
      to be used in production.
    - Rally code depends on a bunch of new libs introduced by testtools and
      testtools itself, which means: more code on which Rally is dependent,
      more time required to install Rally, more disk space required by Rally.
    - Classes like Scenario & Context are inherited from testtools.TestCase
      that makes these classes really hard to learn (for instance:
      running dir(base.Scenario) you cannot see a ton of methods inside it)
    - It won't be clear for end users what exceptions are raised: unittest
      exception are going to be raised during production runs instead of
      Rally assertion exceptions.
    """

    def _concatenate_message(self, default, extended):
        if not extended:
            return default
        if default[-1] != ".":
            default += "."
        return default + " " + extended.capitalize()

    def assertEqual(self, first, second, err_msg=None):
        if first != second:
            msg = "%s != %s" % (repr(first),
                                repr(second))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertNotEqual(self, first, second, err_msg=None):
        if first == second:
            msg = "%s == %s" % (repr(first),
                                repr(second))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertTrue(self, value, err_msg=None):
        if not value:
            msg = "%s is not True" % repr(value)
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertFalse(self, value, err_msg=None):
        if value:
            msg = "%s is not False" % repr(value)
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertIs(self, first, second, err_msg=None):
        if first is not second:
            msg = "%s is not %s" % (repr(first),
                                    repr(second))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertIsNot(self, first, second, err_msg=None):
        if first is second:
            msg = "%s is %s" % (repr(first),
                                repr(second))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertIsNone(self, value, err_msg=None):
        if value is not None:
            msg = "%s is not None" % repr(value)
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertIsNotNone(self, value, err_msg=None):
        if value is None:
            msg = "%s is None" % repr(value)
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertIn(self, member, container, err_msg=None):
        if member not in container:
            msg = "%s not found in %s" % (repr(member),
                                          repr(container))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertNotIn(self, member, container, err_msg=None):
        if member in container:
            msg = "%s found in %s" % (repr(member),
                                      repr(container))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertIsInstance(self, first, second, err_msg=None):
        if not isinstance(first, second):
            msg = "%s is not instance of %s" % (repr(first),
                                                repr(second))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))

    def assertIsNotInstance(self, first, second, err_msg=None):
        if isinstance(first, second):
            msg = "%s is instance of %s" % (repr(first),
                                            repr(second))
            raise exceptions.RallyAssertionError(
                self._concatenate_message(msg, err_msg))
