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

import dataclasses
from unittest import mock
import uuid

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

    @mock.patch("%s.os.path.isfile" % DISCOVER, return_value=True)
    @mock.patch("%s.os.path.isdir" % DISCOVER)
    @mock.patch("%s.importlib.util.module_from_spec" % DISCOVER)
    @mock.patch("%s.importlib.util.spec_from_file_location" % DISCOVER)
    @mock.patch("%s.os.walk" % DISCOVER)
    def test_load_plugins_from_dir_successful(self, mock_os_walk,
                                              mock_spec_from_file_location,
                                              mock_module_from_spec,
                                              mock_isdir, mock_isfile):
        mock_os_walk.return_value = [
            ("/somewhere", ("/subdir", ), ("plugin1.py", )),
            ("/somewhere/subdir", ("/subsubdir", ), ("plugin2.py",
                                                     "withoutextension")),
            ("/somewhere/subdir/subsubdir", [], ("plugin3.py", ))
        ]

        def fake_isdir(p):
            return not (p.endswith(".py") or p.endswith("withoutextension"))

        mock_isdir.side_effect = fake_isdir

        test_path = "/somewhere"
        discover.load_plugins(test_path)
        expected = [
            mock.call(p.rsplit("/", 1)[1][:-3], p)
            for p in ("/somewhere/plugin1.py", "/somewhere/subdir/plugin2.py",
                      "/somewhere/subdir/subsubdir/plugin3.py")
        ]
        self.assertEqual(expected, mock_spec_from_file_location.call_args_list)
        self.assertEqual(3, len(mock_module_from_spec.mock_calls))

    @mock.patch("%s.os.path.isfile" % DISCOVER, return_value=True)
    @mock.patch("%s.importlib.util.module_from_spec" % DISCOVER)
    @mock.patch("%s.importlib.util.spec_from_file_location" % DISCOVER)
    def test_load_plugins_from_file_successful(
            self, mock_spec_from_file_location, mock_module_from_spec,
            mock_isfile):
        path = "/somewhere/plugin.py"
        discover.load_plugins(path)

        mock_spec_from_file_location.assert_called_once_with("plugin", path)
        mock_module_from_spec.assert_called_once_with(
            mock_spec_from_file_location.return_value)

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

    @mock.patch("%s.importlib.util.module_from_spec" % DISCOVER)
    @mock.patch("%s.importlib.util.spec_from_file_location" % DISCOVER)
    @mock.patch("%s.os.path.isfile" % DISCOVER, return_value=True)
    def test_load_plugins_fails(self, mock_isfile,
                                mock_spec_from_file_location,
                                mock_module_from_spec):
        mock_spec_from_file_location.side_effect = Exception()
        # test no fails if module is broken
        # TODO(olkonami): check exception is handled correct
        discover.load_plugins("/somewhere/foo.py")

    @mock.patch("%s.importlib.import_module" % DISCOVER)
    @mock.patch("%s.importlib.metadata.entry_points" % DISCOVER)
    @mock.patch("%s.pkgutil.walk_packages" % DISCOVER)
    def test_import_modules_by_entry_point(
        self, mock_walk_packages, mock_entry_points, mock_import_module
    ):

        @dataclasses.dataclass
        class Dist:
            name: str
            version: str

        @dataclasses.dataclass
        class EntryPoint:
            name: str
            value: str
            dist: Dist
            load: mock.Mock

        class LoadedPackage(object):
            def __init__(self, name, path=None, file=None):
                self.__name__ = name
                if path is not None:
                    self.__path__ = path
                if file is not None:
                    self.__file__ = file

        package1 = Dist(name="plugin1", version="1.2.3")
        package2 = Dist(name="plugin2", version="1.2.4")
        package3 = Dist(name="plugin3", version="1.2.5")
        package4 = Dist(name="plugin4", version="1.2.6")

        mock_entry_points.return_value = [
            EntryPoint(
                name="redundant",
                dist=package1,
                value="xxx",
                load=mock.Mock()
            ),
            EntryPoint(
                dist=package1,
                name="path",
                value="some.module",
                load=mock.Mock(return_value=LoadedPackage(name=package1.name,
                                                          path="/foo"))
            ),
            EntryPoint(
                dist=package2,
                name="path",
                value="another.module",
                load=mock.Mock(return_value=LoadedPackage(name=package2.name,
                                                          file="/bar"))
            ),
            EntryPoint(
                dist=package3,
                name="path",
                value="yet_another.module",
                load=mock.Mock(return_value=LoadedPackage(name=package3.name,
                                                          path="/xxx",
                                                          file="/yyy"))
            ),
            EntryPoint(
                dist=package4,
                name="path",
                value="error",
                load=mock.Mock(return_value=LoadedPackage(name=package4.name))
            )
        ]

        # use random uuid to not have conflicts in sys.modules
        packages = [[(mock.Mock(), str(uuid.uuid4()), None)] for i in range(3)]
        mock_walk_packages.side_effect = packages

        data = dict((p["name"], p)
                    for p in discover.import_modules_by_entry_point())

        mock_entry_points.assert_called_once_with(group="rally_plugins")
        for ep in mock_entry_points.return_value:
            if ep.name != "path":
                self.assertFalse(ep.load.called)
            else:
                self.assertIn(ep.dist.name, data)
                self.assertEqual(ep.dist.version,
                                 data[ep.dist.name]["version"])

        self.assertEqual([mock.call("/foo", prefix="plugin1."),
                          mock.call(["/bar"], prefix="plugin2."),
                          mock.call("/xxx", prefix="plugin3.")],
                         mock_walk_packages.call_args_list)
