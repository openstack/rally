# Copyright 2015: Mirantis Inc.
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

import mock

from rally.common.plugin import discover
from tests.unit import test


DISCOVER = "rally.common.plugin.discover"


class IterSubclassesTestCase(test.TestCase):

    def test_itersubclasses(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D(C):
            pass

        self.assertEqual([B, C, D], list(discover.itersubclasses(A)))


class LoadExtraModulesTestCase(test.TestCase):

    @mock.patch("%s.os.path.isdir" % DISCOVER, return_value=True)
    @mock.patch("%s.imp.load_module" % DISCOVER)
    @mock.patch("%s.imp.find_module" % DISCOVER,
                return_value=(mock.MagicMock(), None, None))
    @mock.patch("%s.os.walk" % DISCOVER, return_value=[
        ("/somewhere", ("/subdir", ), ("plugin1.py", )),
        ("/somewhere/subdir", ("/subsubdir", ), ("plugin2.py",
                                                 "withoutextension")),
        ("/somewhere/subdir/subsubdir", [], ("plugin3.py", ))])
    def test_load_plugins_from_dir_successful(self, mock_os_walk,
                                              mock_find_module,
                                              mock_load_module, mock_isdir):
        test_path = "/somewhere"
        discover.load_plugins(test_path)
        expected = [
            mock.call("plugin1", ["/somewhere"]),
            mock.call("plugin2", ["/somewhere/subdir"]),
            mock.call("plugin3", ["/somewhere/subdir/subsubdir"])
        ]
        self.assertEqual(expected, mock_find_module.mock_calls)
        self.assertEqual(3, len(mock_load_module.mock_calls))

    @mock.patch("%s.os.path.isfile" % DISCOVER, return_value=True)
    @mock.patch("%s.imp.load_source" % DISCOVER)
    def test_load_plugins_from_file_successful(self, mock_load_source,
                                               mock_isfile):
        discover.load_plugins("/somewhere/plugin.py")
        expected = [mock.call("plugin", "/somewhere/plugin.py")]
        self.assertEqual(expected, mock_load_source.mock_calls)

    @mock.patch("%s.os" % DISCOVER)
    def test_load_plugins_from_nonexisting_and_empty_dir(self, mock_os):
        # test no fails for nonexisting directory
        mock_os.path.isdir.return_value = False
        discover.load_plugins("/somewhere")
        # test no fails for empty directory
        mock_os.path.isdir.return_value = True
        mock_os.walk.return_value = []
        discover.load_plugins("/somewhere")

    @mock.patch("%s.os.path.isfile" % DISCOVER, return_value=True)
    def test_load_plugins_from_file_fails(self, mock_isfile):
        discover.load_plugins("/somewhere/plugin.py")

    @mock.patch("%s.os.path.isfile" % DISCOVER, return_value=False)
    def test_load_plugins_from_nonexisting_file(self, mock_isfile):
        # test no fails for nonexisting file
        discover.load_plugins("/somewhere/plugin.py")

    @mock.patch("%s.imp.load_module" % DISCOVER, side_effect=Exception())
    @mock.patch("%s.imp.find_module" % DISCOVER)
    @mock.patch("%s.os.path" % DISCOVER, return_value=True)
    @mock.patch("%s.os.walk" % DISCOVER,
                return_value=[("/etc/.rally/plugins", [], ("load_it.py", ))])
    def test_load_plugins_fails(self, mock_os_walk, mock_os_path,
                                mock_find_module, mock_load_module):
        # test no fails if module is broken
        # TODO(olkonami): check exception is handled correct
        discover.load_plugins("/somewhere")
