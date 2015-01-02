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

from glanceclient import exc as glance_exc
import mock
from novaclient import exceptions as nova_exc

from rally.benchmark import validation
from rally import consts
from rally import exceptions
from rally.verification.tempest import tempest
from tests.unit import test


class ValidationUtilsTestCase(test.TestCase):

    def _get_scenario_validators(self, func_, scenario_, reset=True):
        """Unwrap scenario validators created by validation.validator()."""
        if reset:
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
        self.assertEqual(wrap_kwargs, validator(None, None, None))
        self.assertEqual(wrap_validator, scenario)

        # Default result
        func_success = lambda *a, **kv: None
        validator, = self._get_scenario_validators(func_success, scenario)
        self.assertTrue(validator(None, None, None).is_valid)

        # Failure result
        func_failure = lambda *a, **kv: failure
        validator, = self._get_scenario_validators(func_failure, scenario)
        self.assertFalse(validator(None, None, None).is_valid)


class ValidatorsTestCase(test.TestCase):

    def _unwrap_validator(self, validator, *args, **kwargs):

        @validator(*args, **kwargs)
        def func():
            pass

        return func.validators[0]

    def test_number_not_nullable(self):
        validator = self._unwrap_validator(validation.number, param_name="n")
        self.assertFalse(validator({}, None, None).is_valid)

    def test_number_nullable(self):
        validator = self._unwrap_validator(validation.number, param_name="n",
                                           nullable=True)
        self.assertTrue(validator({}, None, None).is_valid)

    def test_number_min_max_value(self):
        validator = self._unwrap_validator(validation.number,
                                           param_name="a", minval=4, maxval=10)
        result = validator({"args": {"a": 3.9}}, None, None)
        self.assertFalse(result.is_valid, result.msg)
        result = validator({"args": {"a": 4.1}}, None, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"a": 11}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_number_integer_only(self):
        validator = self._unwrap_validator(validation.number,
                                           param_name="b", integer_only=True)
        result = validator({"args": {"b": 3.9}}, None, None)
        self.assertFalse(result.is_valid, result.msg)
        result = validator({"args": {"b": 3}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

    @mock.patch("rally.benchmark.validation.os.access")
    def test_file_exists(self, mock_access):
        mock_access.return_value = True
        validator = self._unwrap_validator(validation.file_exists,
                                           param_name="p")
        result = validator({"args": {"p": "test_file"}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

    @mock.patch("rally.benchmark.validation.os.access")
    def test_file_exists_not_found(self, mock_access):
        mock_access.return_value = False
        validator = self._unwrap_validator(validation.file_exists,
                                           param_name="p")
        result = validator({"args": {"p": "test_file"}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test__get_validated_image_no_value_in_config(self):
        result = validation._get_validated_image({}, None, "non_existing")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch("rally.benchmark.validation.types.ImageResourceType.transform")
    def test__get_validated_image(self, mock_transform):
        mock_transform.return_value = "image_id"
        clients = mock.MagicMock()
        clients.glance().images.get.return_value = "image"

        result = validation._get_validated_image({"args": {"a": "test"}},
                                                 clients, "a")
        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual(result[1], "image")
        mock_transform.assert_called_once_with(clients=clients,
                                               resource_config="test")
        clients.glance().images.get.assert_called_once_with(image="image_id")

    @mock.patch("rally.benchmark.validation.types.ImageResourceType.transform")
    def test__get_validated_image_transform_error(self, mock_transform):
        mock_transform.side_effect = exceptions.InvalidScenarioArgument
        result = validation._get_validated_image({"args": {"a": "test"}},
                                                 None, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch("rally.benchmark.validation.types.ImageResourceType.transform")
    def test__get_validated_image_not_found(self, mock_transform):
        clients = mock.MagicMock()
        clients.glance().images.get.side_effect = glance_exc.HTTPNotFound("")
        result = validation._get_validated_image({"args": {"a": "test"}},
                                                 clients, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

    def test__get_validated_flavor_no_value_in_config(self):
        result = validation._get_validated_flavor({}, None, "non_existing")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch("rally.benchmark.validation.types.FlavorResourceType."
                "transform")
    def test__get_validated_flavor(self, mock_transform):
        mock_transform.return_value = "flavor_id"
        clients = mock.MagicMock()
        clients.nova().flavors.get.return_value = "flavor"

        result = validation._get_validated_flavor({"args": {"a": "test"}},
                                                  clients, "a")
        self.assertTrue(result[0].is_valid, result[0].msg)
        self.assertEqual(result[1], "flavor")
        mock_transform.assert_called_once_with(clients=clients,
                                               resource_config="test")
        clients.nova().flavors.get.assert_called_once_with(flavor="flavor_id")

    @mock.patch("rally.benchmark.validation.types.FlavorResourceType."
                "transform")
    def test__get_validated_flavor_transform_error(self, mock_transform):
        mock_transform.side_effect = exceptions.InvalidScenarioArgument
        result = validation._get_validated_flavor({"args": {"a": "test"}},
                                                  None, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

    @mock.patch("rally.benchmark.validation.types.FlavorResourceType."
                "transform")
    def test__get_validated_flavor_not_found(self, mock_transform):
        clients = mock.MagicMock()
        clients.nova().flavors.get.side_effect = nova_exc.NotFound("")
        result = validation._get_validated_flavor({"args": {"a": "test"}},
                                                  clients, "a")
        self.assertFalse(result[0].is_valid, result[0].msg)

    def test_image_exists(self):
        validator = self._unwrap_validator(validation.image_exists, "param")
        result = validator({}, "clients", "deployment")
        self.assertFalse(result.is_valid, result.msg)

    def test_flavor_exists(self):
        validator = self._unwrap_validator(validation.flavor_exists, "param")
        result = validator({}, "clients", "deployment")
        self.assertFalse(result.is_valid, result.msg)

    def test_image_valid_on_flavor_flavor_or_image_not_specified(self):
        validator = self._unwrap_validator(validation.image_valid_on_flavor,
                                           "flavor", "image")
        result = validator({}, None, None)
        self.assertFalse(result.is_valid, result.msg)

        result = validator({"args": {"flavor": {"id": 11}}}, mock.MagicMock(),
                           None)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch("rally.benchmark.validation._get_validated_image")
    @mock.patch("rally.benchmark.validation._get_validated_flavor")
    def test_image_valid_on_flavor(self, mock_get_flavor, mock_get_image):
        image = mock.MagicMock()
        flavor = mock.MagicMock()
        success = validation.ValidationResult()
        mock_get_flavor.return_value = (success, flavor)
        mock_get_image.return_value = (success, image)

        validator = self._unwrap_validator(validation.image_valid_on_flavor,
                                           "flavor", "image")
        # test ram
        flavor.disk = None
        flavor.ram = 2
        image.min_ram = None
        result = validator(None, None, None)
        self.assertTrue(result.is_valid, result.msg)
        image.min_ram = 4
        result = validator(None, None, None)
        self.assertFalse(result.is_valid, result.msg)
        image.min_ram = 1
        result = validator(None, None, None)
        self.assertTrue(result.is_valid, result.msg)

        # test disk (flavor.disk not None)
        image.size = 2
        image.min_disk = 0
        flavor.disk = 5.0 / (1024 ** 3)
        result = validator(None, None, None)
        self.assertTrue(result.is_valid, result.msg)
        image.min_disk = flavor.disk * 2
        result = validator(None, None, None)
        self.assertFalse(result.is_valid, result.msg)
        image.min_disk = flavor.disk / 4
        image.size = 1000
        result = validator(None, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_network_exists(self):
        validator = self._unwrap_validator(validation.network_exists, "net")

        net1 = mock.MagicMock()
        net1.label = "private"
        net2 = mock.MagicMock()
        net2.label = "custom"
        clients = mock.MagicMock()
        clients.nova().networks.list.return_value = [net1, net2]

        result = validator({}, clients, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"net": "custom"}}, clients, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"net": "custom2"}}, clients, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_external_network_exists(self):
        validator = self._unwrap_validator(validation.external_network_exists,
                                           "name", "use_ext")
        result = validator({"args": {"use_ext": False}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

        clients = mock.MagicMock()
        net1 = mock.MagicMock()
        net2 = mock.MagicMock()
        clients.nova().floating_ip_pools.list.return_value = [net1, net2]

        net1.name = "public"
        net2.name = "custom"
        result = validator({}, clients, None)
        self.assertTrue(result.is_valid, result.msg)

        result = validator({"args": {"name": "custom"}}, clients, None)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"name": "non_exist"}}, clients, None)
        self.assertFalse(result.is_valid, result.msg)

        net1.name = {"name": "public"}
        net2.name = {"name": "custom"}
        result = validator({"args": {"name": "custom"}}, clients, None)
        self.assertTrue(result.is_valid, result.msg)

    def test_tempest_tests_exists_no_arg(self):
        validator = self._unwrap_validator(validation.tempest_tests_exists)
        result = validator({}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch("rally.benchmark.validation.tempest.Tempest")
    def test_tempest_tests_exists(self, mock_tempest):
        mock_tempest().is_installed.return_value = False
        mock_tempest().is_configured.return_value = False
        mock_tempest().discover_tests.return_value = set([
            "tempest.api.a", "tempest.api.b", "tempest.api.c"])

        deployment = {"uuid": "someuuid"}
        validator = self._unwrap_validator(validation.tempest_tests_exists)

        result = validator({"args": {"test_name": "a"}}, None, deployment)
        self.assertTrue(result.is_valid, result.msg)
        mock_tempest().is_installed.assert_called_once_with()
        mock_tempest().is_configured.assert_called_once_with()
        mock_tempest().discover_tests.assert_called_once_with()

        result = validator({"args": {"test_name": "d"}}, None, deployment)
        self.assertFalse(result.is_valid, result.msg)

        result = validator({"args": {"test_name": "tempest.api.a"}}, None,
                           deployment)
        self.assertTrue(result.is_valid, result.msg)
        result = validator({"args": {"test_name": "tempest.api.d"}}, None,
                           deployment)
        self.assertFalse(result.is_valid, result.msg)

        result = validator({"args": {"test_names": ["tempest.api.a", "b"]}},
                           None, deployment)
        self.assertTrue(result.is_valid, result.msg)

        result = validator({"args": {"test_names": ["tempest.api.j", "e"]}},
                           None, deployment)
        self.assertFalse(result.is_valid, result.msg)

    @mock.patch("rally.benchmark.validation.tempest.Tempest")
    def test_tempest_tests_exists_tempest_installation_failed(self,
                                                              mock_tempest):
        mock_tempest().is_installed.return_value = False
        mock_tempest().install.side_effect = tempest.TempestSetupFailure

        deployment = {"uuid": "someuuid"}
        validator = self._unwrap_validator(validation.tempest_tests_exists)

        result = validator({"args": {"test_name": "a"}}, None, deployment)
        self.assertFalse(result.is_valid, result.msg)
        mock_tempest().is_installed.assert_called_once_with()

    def test_tempest_set_exists_missing_args(self):
        validator = self._unwrap_validator(validation.tempest_set_exists)
        result = validator({}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_tempest_set_exists(self):
        validator = self._unwrap_validator(validation.tempest_set_exists)
        result = validator(
            {"args": {"set_name": consts.TEMPEST_TEST_SETS[0]}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

        result = validator(
            {"args": {"set_name": "lol"}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_required_parameters(self):
        validator = self._unwrap_validator(validation.required_parameters,
                                           "a", "b")
        result = validator({"args": {"a": 1, "b": 2, "c": 3}}, None, None)
        self.assertTrue(result.is_valid, result.msg)

        result = validator({"args": {"a": 1, "c": 3}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_required_service(self):
        validator = self._unwrap_validator(validation.required_services,
                                           consts.Service.KEYSTONE,
                                           consts.Service.NOVA)
        clients = mock.MagicMock()
        clients.services().values.return_value = [
            consts.Service.KEYSTONE, consts.Service.NOVA]
        result = validator({}, clients, None)
        self.assertTrue(result.is_valid, result.msg)

        clients.services().values.return_value = [consts.Service.KEYSTONE]
        result = validator({}, clients, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_required_service_wrong_service(self):
        validator = self._unwrap_validator(validation.required_services,
                                           consts.Service.KEYSTONE,
                                           consts.Service.NOVA, "lol")
        clients = mock.MagicMock()
        result = validator({}, clients, None)
        self.assertFalse(result.is_valid, result.msg)

    def test_required_contexts(self):
        validator = self._unwrap_validator(validation.required_contexts,
                                           "c1", "c2", "c3")
        result = validator({"context": {"a": 1}}, None, None)
        self.assertFalse(result.is_valid, result.msg)

        result = validator({"context": {"c1": 1, "c2": 2, "c3": 3}},
                           None, None)
        self.assertTrue(result.is_valid, result.msg)

        result = validator({"context": {"c1": 1, "c2": 2, "c3": 3, "a": 1}},
                           None, None)
        self.assertTrue(result.is_valid, result.msg)

    def test_required_openstack_with_admin(self):
        validator = self._unwrap_validator(validation.required_openstack,
                                           admin=True)

        # admin presented in deployment
        fake_deployment = {"admin": "admin_endpoint", "users": []}
        self.assertTrue(validator(None, None, fake_deployment).is_valid)

        # admin not presented in deployment
        fake_deployment = {"admin": None, "users": ["u1", "h2"]}
        self.assertFalse(validator(None, None, fake_deployment).is_valid)

    def test_required_openstack_with_users(self):
        validator = self._unwrap_validator(validation.required_openstack,
                                           users=True)

        # users presented in deployment
        fake_deployment = {"admin": None, "users": ["u_endpoint"]}
        self.assertTrue(validator({}, None, fake_deployment).is_valid)

        # admin and users presented in deployment
        fake_deployment = {"admin": "a", "users": ["u1", "h2"]}
        self.assertTrue(validator({}, None, fake_deployment).is_valid)

        # admin and user context
        fake_deployment = {"admin": "a", "users": []}
        context = {"context": {"users": True}}
        self.assertTrue(validator(context, None, fake_deployment).is_valid)

        # just admin presented
        fake_deployment = {"admin": "a", "users": []}
        self.assertFalse(validator({}, None, fake_deployment).is_valid)

    def test_required_openstack_with_admin_and_users(self):
        validator = self._unwrap_validator(validation.required_openstack,
                                           admin=True, users=True)

        fake_deployment = {"admin": "a", "users": []}
        self.assertFalse(validator({}, None, fake_deployment).is_valid)

        fake_deployment = {"admin": "a", "users": ["u"]}
        self.assertTrue(validator({}, None, fake_deployment).is_valid)

        # admin and user context
        fake_deployment = {"admin": "a", "users": []}
        context = {"context": {"users": True}}
        self.assertTrue(validator(context, None, fake_deployment).is_valid)

    def test_required_openstack_invalid(self):
        validator = self._unwrap_validator(validation.required_openstack)
        self.assertFalse(validator(None, None, None).is_valid)

    def test_volume_type_exists(self):
        validator = self._unwrap_validator(validation.volume_type_exists,
                                           param_name="volume_type")

        clients = mock.MagicMock()
        clients.cinder().volume_type.list.return_value = []

        context = {"args": {"volume_type": False}}

        result = validator(context, clients, mock.MagicMock())
        self.assertTrue(result.is_valid, result.msg)

    def test_volume_type_exists_check_types(self):
        validator = self._unwrap_validator(validation.volume_type_exists,
                                           param_name="volume_type")

        clients = mock.MagicMock()
        clients.cinder().volume_types.list.return_value = ["type"]

        context = {"args": {"volume_type": True}}

        result = validator(context, clients, mock.MagicMock())
        self.assertTrue(result.is_valid, result.msg)

    def test_volume_type_exists_check_types_no_types_exist(self):
        validator = self._unwrap_validator(validation.volume_type_exists,
                                           param_name="volume_type")

        clients = mock.MagicMock()
        clients().cinder().volume_type.list.return_value = []

        context = {"args": {"volume_type": True}}

        result = validator(context, clients, mock.MagicMock())
        self.assertFalse(result.is_valid, result.msg)