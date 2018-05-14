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

import uuid

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

    def test_itersubclasses_with_multiple_inheritance(self):
        class A(object):
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D(B, C):
            pass

        self.assertEqual([B, D, C], list(discover.itersubclasses(A)))

    def test_itersubclasses_with_type(self):
        class A(type):
            pass

        class B(A):
            pass

        class C(B):
            pass

        self.assertEqual([B, C], list(discover.itersubclasses(A)))


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

    @mock.patch("%s.importlib" % DISCOVER)
    @mock.patch("%s.pkgutil.walk_packages" % DISCOVER)
    @mock.patch("%s.pkg_resources" % DISCOVER)
    def test_import_modules_by_entry_point(self, mock_pkg_resources,
                                           mock_walk_packages, mock_importlib):

        class Package(object):
            def __init__(self, name, version, entry_map):
                self.get_entry_map_called = False
                self.project_name = name
                self.version = version
                self.entry_map = entry_map

            def get_entry_map(self, group):
                if self.get_entry_map_called is not False:
                    raise Exception("`get_entry_map` should be called once.")
                self.get_entry_map_called = group
                return self.entry_map.get(group, {})

        class LoadedPackage(object):
            def __init__(self, name, path=None, file=None):
                self.__name__ = name
                if path is not None:
                    self.__path__ = path
                if file is not None:
                    self.__file__ = file

        class FakeEntryPoint(object):
            def __init__(self, package_name=None, package_path=None,
                         package_file=None, module_name=None, attrs=None):
                self.load = mock.Mock(return_value=LoadedPackage(
                    package_name, package_path, package_file))
                self.module_name = module_name or str(uuid.uuid4())
                self.attrs = attrs or tuple()

        mock_pkg_resources.working_set = [
            Package("foo", "0.1", entry_map={}),
            Package("plugin1", "0.2",
                    entry_map={"rally_plugins": {
                        "path": FakeEntryPoint("plugin1", package_path="/foo"),
                        "foo": FakeEntryPoint("plugin1", package_path="/foo"),
                        "options": FakeEntryPoint(module_name="foo.bar",
                                                  attrs=("list_opts",))
                    }}),
            Package("plugin2", "0.2.1",
                    entry_map={"rally_plugins": {
                        "path": FakeEntryPoint("plugin2",
                                               package_path=None,
                                               package_file="/bar")
                    }}),
            Package("plugin3", "0.3",
                    entry_map={"rally_plugins": {
                        "path": FakeEntryPoint("plugin3",
                                               package_path="/xxx",
                                               package_file="/yyy")
                    }}),
            Package("error", "6.6.6",
                    entry_map={"rally_plugins": {
                        "path": FakeEntryPoint("error")
                    }})
        ]

        def mock_get_entry_map(name, group=None):
            self.assertIsNone(group)
            for p in mock_pkg_resources.working_set:
                if p.project_name == name:
                    return p.entry_map

        mock_pkg_resources.get_entry_map.side_effect = mock_get_entry_map

        # use random uuid to not have conflicts in sys.modules
        packages = [[(mock.Mock(), str(uuid.uuid4()), None)] for i in range(3)]
        mock_walk_packages.side_effect = packages

        data = dict((p["name"], p)
                    for p in discover.import_modules_by_entry_point())
        for package in mock_pkg_resources.working_set:
            self.assertEqual("rally_plugins", package.get_entry_map_called)
            entry_map = package.entry_map.get("rally_plugins", {})
            for ep_name, ep in entry_map.items():
                if ep_name == "path":
                    ep.load.assert_called_once_with()
                    self.assertIn(package.project_name, data)
                    self.assertEqual(package.version,
                                     data[package.project_name]["version"])
                else:
                    self.assertFalse(ep.load.called)
                    if ep_name == "options":
                        self.assertIn(package.project_name, data)
                        self.assertEqual(
                            "%s:%s" % (ep.module_name, ep.attrs[0]),
                            data[package.project_name]["options"])

        self.assertEqual([mock.call("/foo", prefix="plugin1."),
                          mock.call(["/bar"], prefix="plugin2."),
                          mock.call("/xxx", prefix="plugin3.")],
                         mock_walk_packages.call_args_list)
