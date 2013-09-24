# vim: tabstop=4 shiftwidth=4 softtabstop=4

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

"""Test for Rally utils."""

from __future__ import print_function

import sys

from rally import test
from rally import utils


class StdIOCaptureTestCase(test.NoDBTestCase):

    def test_stdout_capture(self):
        stdout = sys.stdout
        messages = ['abcdef', 'defgaga']
        with utils.StdOutCapture() as out:
            for msg in messages:
                print(msg)

        self.assertEqual(out.getvalue().rstrip('\n').split('\n'), messages)
        self.assertEqual(stdout, sys.stdout)

    def test_stderr_capture(self):
        stderr = sys.stderr
        messages = ['abcdef', 'defgaga']
        with utils.StdErrCapture() as err:
            for msg in messages:
                print(msg, file=sys.stderr)

        self.assertEqual(err.getvalue().rstrip('\n').split('\n'), messages)
        self.assertEqual(stderr, sys.stderr)


class IterSubclassesTestCase(test.NoDBTestCase):

    def test_itersubclasses(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D(C):
            pass

        self.assertEqual([B, C, D], list(utils.itersubclasses(A)))


class ImportModulesTestCase(test.NoDBTestCase):
    def test_try_append_module_into_sys_modules(self):
        modules = {}
        utils.try_append_module('rally.version', modules)
        self.assertTrue('rally.version' in modules)

    def test_try_append_broken_module(self):
        modules = {}
        self.assertRaises(ImportError,
                          utils.try_append_module,
                          'tests.fixtures.import.broken',
                          modules)

    def test_import_modules_from_package(self):
        utils.import_modules_from_package('tests.fixtures.import.package')
        self.assertTrue('tests.fixtures.import.package.a' in sys.modules)
        self.assertTrue('tests.fixtures.import.package.b' in sys.modules)
