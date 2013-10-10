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

import mock

from rally.benchmark.scenarios.nova import servers
from rally import test
from tests.benchmark.scenarios.nova import test_utils


class NovaServersTestCase(test.NoDBTestCase):

    def test_boot_and_delete_server(self):

        fake_server = object()

        scenario = "rally.benchmark.scenarios.nova.servers.NovaServers"
        boot = "%s._boot_server" % scenario
        delete = "%s._delete_server" % scenario
        random_name = "%s._generate_random_name" % scenario
        with mock.patch(boot) as mock_boot:
            with mock.patch(delete) as mock_delete:
                with mock.patch(random_name) as mock_random_name:
                    mock_boot.return_value = fake_server
                    mock_random_name.return_value = "random_name"
                    servers.NovaServers.boot_and_delete_server({}, "img", 0,
                                                               fakearg="f")

        mock_boot.assert_called_once_with("random_name", "img", 0, fakearg="f")
        mock_delete.assert_called_once_with(fake_server)

    def test_snapshot_server(self):

        fake_server = object()
        fake_image = test_utils.FakeImageManager().create()
        fake_image.id = "image_id"

        scenario = "rally.benchmark.scenarios.nova.servers.NovaServers"
        boot = "%s._boot_server" % scenario
        suspend = "%s._suspend_server" % scenario
        create_image = "%s._create_image" % scenario
        delete_server = "%s._delete_server" % scenario
        delete_image = "%s._delete_image" % scenario
        random_name = "%s._generate_random_name" % scenario
        with mock.patch(boot) as mock_boot:
            with mock.patch(suspend) as mock_suspend:
                with mock.patch(create_image) as mock_create_image:
                    with mock.patch(delete_server) as mock_delete_server:
                        with mock.patch(delete_image) as mock_delete_image:
                            with mock.patch(random_name) as mock_random_name:
                                mock_random_name.return_value = "random_name"
                                mock_boot.return_value = fake_server
                                mock_create_image.return_value = fake_image
                                servers.NovaServers.snapshot_server({}, "i", 0,
                                                                    fakearg=2)

        mock_boot.assert_has_calls([
            mock.call("random_name", "i", 0, fakearg=2),
            mock.call("random_name", "image_id", 0, fakearg=2)])
        mock_suspend.assert_called_once_with(fake_server)
        mock_create_image.assert_called_once_with(fake_server)
        mock_delete_server.assert_has_calls([
            mock.call(fake_server),
            mock.call(fake_server)])
        mock_delete_image.assert_called_once_with(fake_image)
