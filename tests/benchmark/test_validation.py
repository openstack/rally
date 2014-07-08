# Copyright 2014: Mirantis Inc.
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

from glanceclient import exc as glance_exc
import mock
from novaclient import exceptions as nova_exc

from rally.benchmark import validation
from rally import consts
from rally.openstack.common.gettextutils import _
from tests import fakes
from tests import test


TEMPEST = "rally.verification.verifiers.tempest.tempest"


class ValidationUtilsTestCase(test.TestCase):

    def _get_scenario_validators(self, func_, scenario_, reset=True):
        """Unwrap scenario validators created by validation.validator()."""
        if reset:
            if hasattr(func_, "permission"):
                del func_.permission
            if hasattr(scenario_, "validators"):
                del scenario_.validators
        scenario = validation.validator(func_)()(scenario_)
        return scenario.validators

    def test_validator(self):

        failure = validation.ValidationResult(False)
        func = lambda *args, **kv: kv
        scenario = lambda: None

        # Check arguments passed to validator
        wrap = validation.validator(func)
        wrap_args = ["foo", "bar"]
        wrap_kwargs = {"foo": "spam"}
        wrap_scenario = wrap(*wrap_args, **wrap_kwargs)
        wrap_validator = wrap_scenario(scenario)
        validators = wrap_validator.validators
        self.assertEqual(1, len(validators))
        validator, = validators
        self.assertEqual({"args": tuple(wrap_args), "kwargs": wrap_kwargs},
                         validator())
        self.assertEqual(wrap_validator, scenario)

        # Default permission
        validator, = self._get_scenario_validators(func, scenario)
        self.assertEqual(validator.permission,
                         validation.consts.EndpointPermission.USER)

        # Custom permission
        func.permission = "another_permission"
        del scenario.validators
        validator, = self._get_scenario_validators(func, scenario, reset=False)
        self.assertEqual(validator.permission, "another_permission")

        # Default result
        func_success = lambda *a, **kv: None
        validator, = self._get_scenario_validators(func_success, scenario)
        self.assertTrue(validator().is_valid)

        # Failure result
        func_failure = lambda *a, **kv: failure
        validator, = self._get_scenario_validators(func_failure, scenario)
        self.assertFalse(validator().is_valid)

    def test_required_services(self):
        available_services = {
            consts.ServiceType.IDENTITY: consts.Service.KEYSTONE,
            consts.ServiceType.COMPUTE: consts.Service.NOVA,
            consts.ServiceType.IMAGE: consts.Service.GLANCE}

        clients = mock.Mock(
            services=mock.Mock(return_value=available_services))

        # Unwrap
        required_services = lambda *services:\
            validation.required_services(*services)(lambda: None)\
            .validators.pop()(clients=clients)

        # Services are available
        result = required_services(consts.Service.KEYSTONE)
        self.assertTrue(result.is_valid)

        # Service is not available
        service = consts.Service.CEILOMETER
        result = required_services(consts.Service.KEYSTONE, service)
        self.assertFalse(result.is_valid)

        # Service is unknown
        service = "unknown_service"
        result = required_services(consts.Service.KEYSTONE, service)
        self.assertFalse(result.is_valid)

    def test_add(self):
        def test_validator():
            pass

        @validation.add(test_validator)
        def test_function():
            pass

        validators = getattr(test_function, "validators")
        self.assertEqual(len(validators), 1)
        self.assertEqual(validators[0], test_validator)

    def test_number_invalid(self):
        validator = validation.number('param', 0, 10, nullable=False)

        result = validator(param=-1)
        self.assertFalse(result.is_valid)

        result = validator(param=11)
        self.assertFalse(result.is_valid)

        result = validator(param="not an int")
        self.assertFalse(result.is_valid)

        result = validator(param=None)
        self.assertFalse(result.is_valid)

        result = validator()
        self.assertFalse(result.is_valid)

        result = validator(param=-0.1)
        self.assertFalse(result.is_valid)

    def test_number_integer_only(self):
        validator = validation.number('param', 0, 10, nullable=False,
                                      integer_only=True)
        result = validator(param="5.0")
        self.assertFalse(result.is_valid)

        validator = validation.number('param', 0, 10, nullable=False,
                                      integer_only=False)
        result = validator(param="5.0")
        self.assertTrue(result.is_valid)

    def test_number_valid(self):
        validator = validation.number('param', 0, 10, nullable=False)

        result = validator(param=0)
        self.assertTrue(result.is_valid)

        result = validator(param=10)
        self.assertTrue(result.is_valid)

        result = validator(param=10.0)
        self.assertTrue(result.is_valid)

        result = validator(param=5.6)
        self.assertTrue(result.is_valid)

    def test_number_nullable(self):
        validator = validation.number('param', 0, 10, nullable=True)

        result = validator(param=None)
        self.assertTrue(result.is_valid)

        result = validator()
        self.assertTrue(result.is_valid)

        result = validator(param=-1)
        self.assertFalse(result.is_valid)

        result = validator(param=0)
        self.assertTrue(result.is_valid)

    @mock.patch("os.access")
    def test_file_exists(self, mock_access):
        validator = validation.file_exists('param')
        result = validator(param='/tmp/foo')
        mock_access.assert_called_once_with('/tmp/foo', os.R_OK)
        self.assertTrue(result.is_valid)

    @mock.patch("os.access")
    def test_file_exists_negative(self, mock_access):
        validator = validation.file_exists('param')
        mock_access.return_value = False
        result = validator(param='/tmp/bah')
        mock_access.assert_called_with('/tmp/bah', os.R_OK)
        self.assertFalse(result.is_valid)

    @mock.patch("rally.osclients.Clients")
    def test_image_exists(self, mock_osclients):
        fakegclient = fakes.FakeGlanceClient()
        fakegclient.images.get = mock.MagicMock()
        mock_osclients.glance.return_value = fakegclient
        validator = validation.image_exists("image")
        test_img_id = "test_image_id"
        resource = {"id": test_img_id}
        result = validator(clients=mock_osclients,
                           image=resource)
        fakegclient.images.get.assert_called_once_with(image=test_img_id)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_image_exists_fail(self, mock_osclients):
        fakegclient = fakes.FakeGlanceClient()
        fakegclient.images.get = mock.MagicMock()
        fakegclient.images.get.side_effect = glance_exc.HTTPNotFound
        mock_osclients.glance.return_value = fakegclient
        validator = validation.image_exists("image")
        test_img_id = "test_image_id"
        resource = {"id": test_img_id}
        result = validator(clients=mock_osclients,
                           image=resource)
        fakegclient.images.get.assert_called_once_with(image=test_img_id)
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_flavor_exists(self, mock_osclients):
        fakenclient = fakes.FakeNovaClient()
        fakenclient.flavors = mock.MagicMock()
        mock_osclients.nova.return_value = fakenclient
        validator = validation.flavor_exists("flavor")
        test_flavor_id = 1
        resource = {"id": test_flavor_id}
        result = validator(clients=mock_osclients,
                           flavor=resource)
        fakenclient.flavors.get.assert_called_once_with(flavor=test_flavor_id)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_flavor_exists_fail(self, mock_osclients):
        fakenclient = fakes.FakeNovaClient()
        fakenclient.flavors = mock.MagicMock()
        fakenclient.flavors.get.side_effect = nova_exc.NotFound(code=404)
        mock_osclients.nova.return_value = fakenclient
        validator = validation.flavor_exists("flavor")
        test_flavor_id = 101
        resource = {"id": test_flavor_id}
        result = validator(clients=mock_osclients,
                           flavor=resource)
        fakenclient.flavors.get.assert_called_once_with(flavor=test_flavor_id)
        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_image_valid_on_flavor(self, mock_osclients):
        fakegclient = fakes.FakeGlanceClient()
        image = fakes.FakeImage()
        image.min_ram = 0
        image.size = 0
        image.min_disk = 0
        fakegclient.images.get = mock.MagicMock(return_value=image)
        mock_osclients.glance.return_value = fakegclient

        fakenclient = fakes.FakeNovaClient()
        flavor = fakes.FakeFlavor()
        flavor.ram = 1
        flavor.disk = 1
        fakenclient.flavors.get = mock.MagicMock(return_value=flavor)
        mock_osclients.nova.return_value = fakenclient

        validator = validation.image_valid_on_flavor("flavor", "image")

        result = validator(clients=mock_osclients,
                           flavor={"id": flavor.id},
                           image={"id": image.id})

        fakenclient.flavors.get.assert_called_once_with(flavor=flavor.id)
        fakegclient.images.get.assert_called_once_with(image=image.id)

        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_image_valid_on_flavor_fail(self, mock_osclients):
        fakegclient = fakes.FakeGlanceClient()
        image = fakes.FakeImage()
        image.min_ram = 1
        image.size = 1
        image.min_disk = 1
        fakegclient.images.get = mock.MagicMock(return_value=image)
        mock_osclients.glance.return_value = fakegclient

        fakenclient = fakes.FakeNovaClient()
        flavor = fakes.FakeFlavor()
        flavor.ram = 0
        flavor.disk = 0
        fakenclient.flavors.get = mock.MagicMock(return_value=flavor)
        mock_osclients.nova.return_value = fakenclient

        validator = validation.image_valid_on_flavor("flavor", "image")

        result = validator(clients=mock_osclients,
                           flavor={"id": flavor.id},
                           image={"id": image.id})

        fakenclient.flavors.get.assert_called_once_with(flavor=flavor.id)
        fakegclient.images.get.assert_called_once_with(image=image.id)

        self.assertFalse(result.is_valid)
        self.assertIsNotNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_image_valid_on_flavor_image_not_exist(self, mock_osclients):
        fakegclient = fakes.FakeGlanceClient()
        fakegclient.images.get = mock.MagicMock()
        fakegclient.images.get.side_effect = glance_exc.HTTPNotFound
        mock_osclients.glance.return_value = fakegclient

        fakenclient = fakes.FakeNovaClient()
        flavor = fakes.FakeFlavor()
        fakenclient.flavors.get = mock.MagicMock(return_value=flavor)
        mock_osclients.nova.return_value = fakenclient

        validator = validation.image_valid_on_flavor("flavor", "image")

        test_img_id = "test_image_id"

        result = validator(clients=mock_osclients,
                           flavor={"id": flavor.id},
                           image={"id": test_img_id})

        fakenclient.flavors.get.assert_called_once_with(flavor=flavor.id)
        fakegclient.images.get.assert_called_once_with(image=test_img_id)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.msg, "Image with id 'test_image_id' not found")

    @mock.patch("rally.osclients.Clients")
    def test_network_exists(self, mock_osclients):
        fakenclient = fakes.FakeNovaClient()
        fake_network = fakes.FakeNetwork()
        fake_network.label = "private"
        fake_network.id = "net_id_1234"

        fakenclient.networks.list = mock.MagicMock(
            return_value=[fake_network])
        mock_osclients.nova.return_value = fakenclient

        validator = validation.network_exists("fixed_network")

        network_name = "private"

        result = validator(clients=mock_osclients,
                           fixed_network=network_name)

        fakenclient.networks.list.assert_called_once_with()
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_network_exists_fail(self, mock_osclients):
        fakenclient = fakes.FakeNovaClient()
        fake_network = fakes.FakeNetwork()
        fake_network.label = "private"
        fake_network.id = "net_id_1234"

        fakenclient.networks.list = mock.MagicMock(
            return_value=[fake_network])
        mock_osclients.nova.return_value = fakenclient

        validator = validation.network_exists("fixed_network")

        network_name = "foo"

        result = validator(clients=mock_osclients,
                           fixed_network=network_name)

        fakenclient.networks.list.assert_called_once_with()
        self.assertFalse(result.is_valid)
        self.assertEqual(result.msg,
                         "Network with name foo not found. "
                         "Available networks: ['private']")

    @mock.patch("rally.osclients.Clients")
    def test_external_network_exists(self, mock_osclients):
        fakenclient = fakes.FakeNovaClient()
        fake_pool = fakes.FakeFloatingIPPool()
        fake_pool.name = "floating"
        fakenclient.floating_ip_pools.list = mock.MagicMock(
            return_value=[fake_pool])
        mock_osclients.nova.return_value = fakenclient

        validator = validation.external_network_exists("floating_network",
                                                       "use_floatingip")

        network_name = "floating"

        result = validator(clients=mock_osclients,
                           floating_network=network_name)

        fakenclient.floating_ip_pools.list.assert_called_once_with()
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_external_network_exists_ignored(self, mock_osclients):
        fakenclient = fakes.FakeNovaClient()
        fake_pool = fakes.FakeFloatingIPPool()
        fake_pool.name = "floating"
        fakenclient.floating_ip_pools.list = mock.MagicMock(
            return_value=[fake_pool])
        mock_osclients.nova.return_value = fakenclient

        validator = validation.external_network_exists("floating_network",
                                                       "use_floatingip")

        network_name = "not_used"

        result = validator(clients=mock_osclients,
                           floating_network=network_name,
                           use_floatingip=False)

        self.assertFalse(fakenclient.floating_ip_pools.list.called)
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.msg)

    @mock.patch("rally.osclients.Clients")
    def test_external_network_exists_fail(self, mock_osclients):
        fakenclient = fakes.FakeNovaClient()
        fake_pool = fakes.FakeFloatingIPPool()
        fake_pool.name = "floating"
        fakenclient.floating_ip_pools.list = mock.MagicMock(
            return_value=[fake_pool])
        mock_osclients.nova.return_value = fakenclient

        validator = validation.external_network_exists("floating_network",
                                                       "use_floatingip")

        network_name = "foo"

        result = validator(clients=mock_osclients,
                           floating_network=network_name)

        fakenclient.floating_ip_pools.list.assert_called_once_with()
        self.assertFalse(result.is_valid)
        self.assertEqual(result.msg, "External (floating) network with name "
                                     "foo not found. "
                                     "Available networks: ['floating']")

    @mock.patch("rally.osclients.Clients")
    def test_image_valid_on_flavor_flavor_not_exist(self, mock_osclients):
        fakegclient = fakes.FakeGlanceClient()
        mock_osclients.glance.return_value = fakegclient

        fakenclient = fakes.FakeNovaClient()
        fakenclient.flavors = mock.MagicMock()
        fakenclient.flavors.get.side_effect = nova_exc.NotFound(code=404)
        mock_osclients.nova.return_value = fakenclient

        validator = validation.image_valid_on_flavor("flavor", "image")

        test_img_id = "test_image_id"
        test_flavor_id = 101

        result = validator(clients=mock_osclients,
                           flavor={"id": test_flavor_id},
                           image={"id": test_img_id})

        fakenclient.flavors.get.assert_called_once_with(flavor=test_flavor_id)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.msg, "Flavor with id '101' not found")

    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.is_installed")
    @mock.patch(TEMPEST + ".subprocess")
    def test_tempest_test_name_not_valid(self, mock_sp, mock_install,
                                         mock_config):
        mock_sp.Popen().communicate.return_value = (
            "tempest.api.fake_test1[gate]\ntempest.api.fate_test2\n",)
        mock_install.return_value = True
        mock_config.return_value = True

        validator = validation.tempest_tests_exists()
        result = validator(test_name="no_valid_test_name",
                           task=mock.MagicMock())
        self.assertFalse(result.is_valid)
        self.assertEqual("One or more tests not found: 'no_valid_test_name'",
                         result.msg)

    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.is_installed")
    @mock.patch(TEMPEST + ".subprocess")
    def test_tempest_test_name_valid(self, mock_sp, mock_install, mock_config):
        mock_sp.Popen().communicate.return_value = (
            "tempest.api.compute.fake_test1[gate]\n"
            "tempest.api.image.fake_test2\n",)
        mock_install.return_value = True
        mock_config.return_value = True

        validator = validation.tempest_tests_exists()
        result = validator(test_name="image.fake_test2", task=mock.MagicMock())

        self.assertTrue(result.is_valid)

    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.is_installed")
    @mock.patch(TEMPEST + ".subprocess")
    def test_tempest_test_names_one_invalid(self, mock_sp, mock_install,
                                            mock_config):
        mock_sp.Popen().communicate.return_value = ('\n'.join([
            "tempest.api.fake_test1[gate]",
            "tempest.api.fake_test2",
            "tempest.api.fake_test3[gate,smoke]",
            "tempest.api.fate_test4[fake]"]),)
        mock_install.return_value = True
        mock_config.return_value = True

        validator = validation.tempest_tests_exists()
        result = validator(test_names=["tempest.api.fake_test2",
                                       "tempest.api.invalid.test"],
                           task=mock.MagicMock())

        self.assertFalse(result.is_valid)
        self.assertEqual(_("One or more tests not found: '%s'") %
                         "tempest.api.invalid.test", result.msg)

    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.is_installed")
    @mock.patch(TEMPEST + ".subprocess")
    def test_tempest_test_names_all_invalid(self, mock_sp, mock_install,
                                            mock_config):
        mock_sp.Popen().communicate.return_value = ("\n".join([
            "tempest.api.fake_test1[gate]",
            "tempest.api.fake_test2",
            "tempest.api.fake_test3[gate,smoke]",
            "tempest.api.fate_test4[fake]"]),)
        mock_install.return_value = True
        mock_config.return_value = True

        validator = validation.tempest_tests_exists()
        result = validator(test_names=["tempest.api.invalid.test1",
                                       "tempest.api.invalid.test2"],
                           task=mock.MagicMock())

        self.assertFalse(result.is_valid)
        self.assertEqual(
            _("One or more tests not found: '%s'") %
            "tempest.api.invalid.test1', 'tempest.api.invalid.test2",
            result.msg)

    @mock.patch(TEMPEST + ".Tempest.is_configured")
    @mock.patch(TEMPEST + ".Tempest.is_installed")
    @mock.patch(TEMPEST + '.subprocess')
    def test_tempest_test_names_all_valid(self, mock_sp, mock_install,
                                          mock_config):
        mock_sp.Popen().communicate.return_value = ("\n".join([
            "tempest.api.fake_test1[gate]",
            "tempest.api.fake_test2",
            "tempest.api.fake_test3[gate,smoke]",
            "tempest.api.fate_test4[fake]"]),)
        mock_install.return_value = True
        mock_config.return_value = True

        validator = validation.tempest_tests_exists()
        result = validator(test_names=["tempest.api.fake_test1",
                                       "tempest.api.fake_test2"],
                           task=mock.MagicMock())

        self.assertTrue(result.is_valid)
