# Copyright 2017: Mirantis Inc.
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

import copy
import ddt
import mock

from glanceclient import exc as glance_exc
from novaclient import exceptions as nova_exc

from rally import consts
from rally import exceptions
from rally.plugins.openstack import validators
from tests.unit import test


PATH = "rally.plugins.openstack.validators"


context = {
    "admin": mock.MagicMock(),
    "users": [mock.MagicMock()],
}

config = dict(args={"image": {"id": "fake_id",
                              "min_ram": 10,
                              "size": 1024 ** 3,
                              "min_disk": 10.0 * (1024 ** 3),
                              "image_name": "foo_image"},
                    "flavor": {"id": "fake_flavor_id",
                               "name": "test"},
                    "foo_image": {"id": "fake_image_id"}
                    },
              context={"images": {"image_name": "foo_image"},
                       "api_versions@openstack": mock.MagicMock()}
              )


@mock.patch("rally.plugins.openstack.context.keystone.roles.RoleGenerator")
def test_with_roles_ctx(mock_role_generator):

    @validators.with_roles_ctx()
    def func(config, context):
        pass

    config = {"contexts": {}}
    context = {"admin": {"credential": mock.MagicMock()},
               "task": mock.MagicMock()}
    func(config, context)
    mock_role_generator().setup.assert_not_called()

    config = {"contexts": {"roles": "admin"}}
    func(config, context)
    mock_role_generator().setup.assert_called_once_with()


@ddt.ddt
class ImageExistsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ImageExistsValidatorTestCase, self).setUp()
        self.validator = validators.ImageExistsValidator("image", True)
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    @ddt.unpack
    @ddt.data(
        {"param_name": "fake_param", "nullable": True, "err_msg": None},
        {"param_name": "fake_param", "nullable": False,
         "err_msg": "Parameter fake_param is not specified."},
        {"param_name": "image", "nullable": True, "err_msg": None},
    )
    def test_validator(self, param_name, nullable, err_msg, ex=False):
        validator = validators.ImageExistsValidator(param_name,
                                                    nullable)

        clients = self.context["users"][0].clients.return_value

        clients.glance().images.get = mock.Mock()
        if ex:
            clients.glance().images.get.side_effect = ex

        if err_msg:
            e = self.assertRaises(
                validators.validation.ValidationError,
                validator.validate, self.context, self.config, None, None)
            self.assertEqual(err_msg, e.message)
        else:
            result = validator.validate(self.config, self.context, None,
                                        None)
            self.assertIsNone(result)

    def test_validator_image_from_context(self):
        config = {
            "args": {"image": {"regex": r"^foo$"}},
            "contexts": {"images": {"image_name": "foo"}}}

        self.validator.validate(self.context, config, None, None)

    @mock.patch("%s.openstack_types.GlanceImage" % PATH)
    def test_validator_image_not_in_context(self, mock_glance_image):
        mock_glance_image.return_value.pre_process.return_value = "image_id"
        config = {
            "args": {"image": "fake_image"},
            "contexts": {
                "images": {"fake_image_name": "foo"}}}

        clients = self.context[
            "users"][0]["credential"].clients.return_value
        clients.glance().images.get = mock.Mock()

        result = self.validator.validate(self.context, config, None, None)
        self.assertIsNone(result)

        mock_glance_image.assert_called_once_with(
            context={"admin": {
                "credential": self.context["users"][0]["credential"]}})
        mock_glance_image.return_value.pre_process.assert_called_once_with(
            config["args"]["image"], config={})
        clients.glance().images.get.assert_called_with("image_id")

        exs = [exceptions.InvalidScenarioArgument(),
               glance_exc.HTTPNotFound()]
        for ex in exs:
            clients.glance().images.get.side_effect = ex

            e = self.assertRaises(
                validators.validation.ValidationError,
                self.validator.validate, self.context, config, None, None)

            self.assertEqual("Image 'fake_image' not found", e.message)


@ddt.ddt
class ExternalNetworkExistsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ExternalNetworkExistsValidatorTestCase, self).setUp()
        self.validator = validators.ExternalNetworkExistsValidator("net")
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    @ddt.unpack
    @ddt.data(
        {"foo_conf": {}},
        {"foo_conf": {"args": {"net": "custom"}}},
        {"foo_conf": {"args": {"net": "non_exist"}},
         "err_msg": "External (floating) network with name non_exist"
                    " not found by user {}. Available networks:"
                    " [{}, {}]"},
        {"foo_conf": {"args": {"net": "custom"}},
         "net1_name": {"name": {"net": "public"}},
         "net2_name": {"name": {"net": "custom"}},
         "err_msg": "External (floating) network with name custom"
                    " not found by user {}. Available networks:"
                    " [{}, {}]"}
    )
    def test_validator(self, foo_conf, net1_name="public", net2_name="custom",
                       err_msg=""):

        user = self.context["users"][0]

        net1 = {"name": net1_name, "router:external": True}
        net2 = {"name": net2_name, "router:external": True}

        user["credential"].clients().neutron().list_networks.return_value = {
            "networks": [net1, net2]}
        if err_msg:
            e = self.assertRaises(
                validators.validation.ValidationError,
                self.validator.validate, self.context, foo_conf,
                None, None)
            self.assertEqual(
                err_msg.format(user["credential"].username, net1, net2),
                e.message)
        else:
            result = self.validator.validate(self.context, foo_conf,
                                             None, None)
            self.assertIsNone(result, "Unexpected result '%s'" % result)


@ddt.ddt
class RequiredNeutronExtensionsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredNeutronExtensionsValidatorTestCase, self).setUp()
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    def test_validator(self):
        validator = validators.RequiredNeutronExtensionsValidator(
            "existing_extension")
        clients = self.context["users"][0]["credential"].clients()

        clients.neutron().list_extensions.return_value = {
            "extensions": [{"alias": "existing_extension"}]}

        validator.validate(self.context, {}, None, None)

    def test_validator_failed(self):
        err_msg = "Neutron extension absent_extension is not configured"
        validator = validators.RequiredNeutronExtensionsValidator(
            "absent_extension")
        clients = self.context["users"][0]["credential"].clients()

        clients.neutron().list_extensions.return_value = {
            "extensions": [{"alias": "existing_extension"}]}

        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, {}, None, None)
        self.assertEqual(err_msg, e.message)


class FlavorExistsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(FlavorExistsValidatorTestCase, self).setUp()
        self.validator = validators.FlavorExistsValidator(
            param_name="foo_flavor")
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    def test__get_validated_flavor_wrong_value_in_config(self):
        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator._get_validated_flavor, self.config,
            mock.MagicMock(), "foo_flavor")
        self.assertEqual("Parameter foo_flavor is not specified.",
                         e.message)

    @mock.patch("%s.openstack_types.Flavor" % PATH)
    def test__get_validated_flavor(self, mock_flavor):
        mock_flavor.return_value.pre_process.return_value = "flavor_id"

        clients = mock.Mock()
        clients.nova().flavors.get.return_value = "flavor"

        result = self.validator._get_validated_flavor(self.config,
                                                      clients,
                                                      "flavor")
        self.assertEqual("flavor", result)

        mock_flavor.assert_called_once_with(
            context={"admin": {"credential": clients.credential}}
        )
        mock_flavor_obj = mock_flavor.return_value
        mock_flavor_obj.pre_process.assert_called_once_with(
            self.config["args"]["flavor"], config={})
        clients.nova().flavors.get.assert_called_once_with(flavor="flavor_id")
        mock_flavor_obj.pre_process.reset_mock()

        clients.side_effect = exceptions.InvalidScenarioArgument("")
        result = self.validator._get_validated_flavor(
            self.config, clients, "flavor")
        self.assertEqual("flavor", result)
        mock_flavor_obj.pre_process.assert_called_once_with(
            self.config["args"]["flavor"], config={})
        clients.nova().flavors.get.assert_called_with(flavor="flavor_id")

    @mock.patch("%s.openstack_types.Flavor" % PATH)
    def test__get_validated_flavor_not_found(self, mock_flavor):
        mock_flavor.return_value.pre_process.return_value = "flavor_id"

        clients = mock.MagicMock()
        clients.nova().flavors.get.side_effect = nova_exc.NotFound("")

        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator._get_validated_flavor,
            self.config, clients, "flavor")
        self.assertEqual("Flavor '%s' not found" %
                         self.config["args"]["flavor"],
                         e.message)
        mock_flavor_obj = mock_flavor.return_value
        mock_flavor_obj.pre_process.assert_called_once_with(
            self.config["args"]["flavor"], config={})

    @mock.patch("%s.types.obj_from_name" % PATH)
    @mock.patch("%s.flavors_ctx.FlavorConfig" % PATH)
    def test__get_flavor_from_context(self, mock_flavor_config,
                                      mock_obj_from_name):
        config = {
            "contexts": {"images": {"fake_parameter_name": "foo_image"}}}

        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator._get_flavor_from_context,
            config, "foo_flavor")
        self.assertEqual("No flavors context", e.message)

        config = {"contexts": {"images": {"fake_parameter_name": "foo_image"},
                               "flavors": [{"flavor1": "fake_flavor1"}]}}
        result = self.validator._get_flavor_from_context(config, "foo_flavor")
        self.assertEqual("<context flavor: %s>" % result.name, result.id)

    def test_validate(self):
        expected_e = validators.validation.ValidationError("fpp")
        self.validator._get_validated_flavor = mock.Mock(
            side_effect=expected_e)

        config = {}
        ctx = mock.MagicMock()
        actual_e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator.validate, ctx, config, None, None)
        self.assertEqual(expected_e, actual_e)
        self.validator._get_validated_flavor.assert_called_once_with(
            config=config,
            clients=ctx["users"][0]["credential"].clients(),
            param_name=self.validator.param_name)


@ddt.ddt
class ImageValidOnFlavorValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ImageValidOnFlavorValidatorTestCase, self).setUp()
        self.validator = validators.ImageValidOnFlavorValidator("foo_flavor",
                                                                "image")
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    @ddt.data(
        {"validate_disk": True, "flavor_disk": True},
        {"validate_disk": False, "flavor_disk": True},
        {"validate_disk": False, "flavor_disk": False}
    )
    @ddt.unpack
    def test_validate(self, validate_disk, flavor_disk):
        validator = validators.ImageValidOnFlavorValidator(
            flavor_param="foo_flavor",
            image_param="image",
            fail_on_404_image=False,
            validate_disk=validate_disk)

        min_ram = 2048
        disk = 10
        fake_image = {"min_ram": min_ram,
                      "size": disk * (1024 ** 3),
                      "min_disk": disk}
        fake_flavor = mock.Mock(disk=None, ram=min_ram * 2)
        if flavor_disk:
            fake_flavor.disk = disk * 2

        validator._get_validated_flavor = mock.Mock(
            return_value=fake_flavor)

        # case 1: no image, but it is ok, since fail_on_404_image is False
        validator._get_validated_image = mock.Mock(
            side_effect=validators.validation.ValidationError("!!!"))
        validator.validate(self.context, {}, None, None)

        # case 2: there is an image
        validator._get_validated_image = mock.Mock(
            return_value=fake_image)
        validator.validate(self.context, {}, None, None)

        # case 3: check caching of the flavor
        self.context["users"].append(self.context["users"][0])
        validator._get_validated_image.reset_mock()
        validator._get_validated_flavor.reset_mock()

        validator.validate(self.context, {}, None, None)

        self.assertEqual(1, validator._get_validated_flavor.call_count)
        self.assertEqual(2, validator._get_validated_image.call_count)

    def test_validate_failed(self):
        validator = validators.ImageValidOnFlavorValidator(
            flavor_param="foo_flavor",
            image_param="image",
            fail_on_404_image=True,
            validate_disk=True)

        min_ram = 2048
        disk = 10
        fake_flavor = mock.Mock(disk=disk, ram=min_ram)
        fake_flavor.id = "flavor_id"

        validator._get_validated_flavor = mock.Mock(
            return_value=fake_flavor)

        # case 1: there is no image and fail_on_404_image flag is True
        expected_e = validators.validation.ValidationError("!!!")
        validator._get_validated_image = mock.Mock(
            side_effect=expected_e)
        actual_e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, {}, None, None
        )
        self.assertEqual(expected_e, actual_e)

        # case 2: there is no right flavor
        expected_e = KeyError("Ooops")
        validator._get_validated_flavor.side_effect = expected_e
        actual_e = self.assertRaises(
            KeyError,
            validator.validate, self.context, {}, None, None
        )
        self.assertEqual(expected_e, actual_e)

        # case 3: ram of a flavor is less than min_ram of an image
        validator._get_validated_flavor = mock.Mock(
            return_value=fake_flavor)

        fake_image = {"min_ram": min_ram * 2, "id": "image_id"}
        validator._get_validated_image = mock.Mock(
            return_value=fake_image)
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, {}, None, None
        )
        self.assertEqual(
            "The memory size for flavor 'flavor_id' is too small for "
            "requested image 'image_id'.", e.message)

        # case 4: disk of a flavor is less than size of an image
        fake_image = {"min_ram": min_ram / 2.0,
                      "size": disk * (1024 ** 3) * 3,
                      "id": "image_id"}
        validator._get_validated_image = mock.Mock(
            return_value=fake_image)
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, {}, None, None
        )
        self.assertEqual(
            "The disk size for flavor 'flavor_id' is too small for "
            "requested image 'image_id'.", e.message)

        # case 5: disk of a flavor is less than size of an image
        fake_image = {"min_ram": min_ram,
                      "size": disk * (1024 ** 3),
                      "min_disk": disk * 2,
                      "id": "image_id"}
        validator._get_validated_image = mock.Mock(
            return_value=fake_image)
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, {}, None, None
        )
        self.assertEqual(
            "The minimal disk size for flavor 'flavor_id' is too small for "
            "requested image 'image_id'.", e.message)

        # case 6: _get_validated_image raises an unexpected error,
        #   fail_on_404_image=False should not work in this case
        expected_e = KeyError("Foo!")
        validator = validators.ImageValidOnFlavorValidator(
            flavor_param="foo_flavor",
            image_param="image",
            fail_on_404_image=False,
            validate_disk=True)
        validator._get_validated_image = mock.Mock(
            side_effect=expected_e)
        validator._get_validated_flavor = mock.Mock()

        actual_e = self.assertRaises(
            KeyError,
            validator.validate, self.context, {}, None, None
        )

        self.assertEqual(expected_e, actual_e)

    @mock.patch("%s.openstack_types.GlanceImage" % PATH)
    def test__get_validated_image(self, mock_glance_image):
        mock_glance_image.return_value.pre_process.return_value = "image_id"
        image = {
            "size": 0,
            "min_ram": 0,
            "min_disk": 0
        }
        # Get image name from context
        result = self.validator._get_validated_image({
            "args": {
                "image": {"regex": r"^foo$"}},
            "contexts": {
                "images": {"image_name": "foo"}}},
            mock.Mock(), "image")
        self.assertEqual(image, result)

        clients = mock.Mock()
        clients.glance().images.get().to_dict.return_value = {
            "image": "image_id"}
        image["image"] = "image_id"

        result = self.validator._get_validated_image(self.config,
                                                     clients,
                                                     "image")
        self.assertEqual(image, result)
        mock_glance_image.assert_called_once_with(
            context={"admin": {"credential": clients.credential}})
        mock_glance_image.return_value.pre_process.assert_called_once_with(
            config["args"]["image"], config={})
        clients.glance().images.get.assert_called_with("image_id")

    @mock.patch("%s.openstack_types.GlanceImage" % PATH)
    def test__get_validated_image_incorrect_param(self, mock_glance_image):
        mock_glance_image.return_value.pre_process.return_value = "image_id"
        # Wrong 'param_name'
        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator._get_validated_image, self.config,
            mock.Mock(), "fake_param")
        self.assertEqual("Parameter fake_param is not specified.",
                         e.message)

        # 'image_name' is not in 'image_context'
        image = {"id": "image_id", "size": 1024,
                 "min_ram": 256, "min_disk": 512}

        clients = mock.Mock()
        clients.glance().images.get().to_dict.return_value = image
        config = {"args": {"image": "foo_image",
                           "context": {"images": {
                               "fake_parameter_name": "foo_image"}
                           }}
                  }
        result = self.validator._get_validated_image(config, clients, "image")
        self.assertEqual(image, result)

        mock_glance_image.assert_called_once_with(
            context={"admin": {"credential": clients.credential}})
        mock_glance_image.return_value.pre_process.assert_called_once_with(
            config["args"]["image"], config={})
        clients.glance().images.get.assert_called_with("image_id")

    @mock.patch("%s.openstack_types.GlanceImage" % PATH)
    def test__get_validated_image_exceptions(self, mock_glance_image):
        mock_glance_image.return_value.pre_process.return_value = "image_id"
        clients = mock.Mock()
        clients.glance().images.get.side_effect = glance_exc.HTTPNotFound("")
        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator._get_validated_image,
            config, clients, "image")
        self.assertEqual("Image '%s' not found" % config["args"]["image"],
                         e.message)

        mock_glance_image.assert_called_once_with(
            context={"admin": {"credential": clients.credential}})
        mock_glance_image.return_value.pre_process.assert_called_once_with(
            config["args"]["image"], config={})
        clients.glance().images.get.assert_called_with("image_id")
        mock_glance_image.return_value.pre_process.reset_mock()

        clients.side_effect = exceptions.InvalidScenarioArgument("")
        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator._get_validated_image, config, clients, "image")
        self.assertEqual("Image '%s' not found" % config["args"]["image"],
                         e.message)
        mock_glance_image.return_value.pre_process.assert_called_once_with(
            config["args"]["image"], config={})
        clients.glance().images.get.assert_called_with("image_id")


class RequiredClientsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredClientsValidatorTestCase, self).setUp()
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    def test_validate(self):
        validator = validators.RequiredClientsValidator(components=["keystone",
                                                                    "nova"])
        clients = self.context["users"][0]["credential"].clients.return_value

        result = validator.validate(self.context, self.config, None, None)
        self.assertIsNone(result)

        clients.nova.side_effect = ImportError
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, self.config, None, None)
        self.assertEqual("Client for nova is not installed. To install it "
                         "run `pip install python-novaclient`", e.message)

    def test_validate_with_admin(self):
        validator = validators.RequiredClientsValidator(components=["keystone",
                                                                    "nova"],
                                                        admin=True)
        clients = self.context["admin"]["credential"].clients.return_value
        result = validator.validate(self.context, self.config, None, None)
        self.assertIsNone(result)

        clients.keystone.side_effect = ImportError
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, self.config, None, None)
        self.assertEqual("Client for keystone is not installed. To install it "
                         "run `pip install python-keystoneclient`", e.message)


class RequiredServicesValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredServicesValidatorTestCase, self).setUp()
        self.validator = validators.RequiredServicesValidator([
            consts.Service.KEYSTONE,
            consts.Service.NOVA,
            consts.Service.NOVA_NET])
        self.config = config
        self.context = context

    def test_validator(self):

        self.config["context"]["api_versions@openstack"].get = mock.Mock(
            return_value={consts.Service.KEYSTONE: "service_type"})

        clients = self.context["admin"].get("credential").clients()

        clients.services().values.return_value = [
            consts.Service.KEYSTONE, consts.Service.NOVA,
            consts.Service.NOVA_NET]
        fake_service = mock.Mock(binary="nova-network", status="enabled")
        clients.nova.services.list.return_value = [fake_service]
        result = self.validator.validate(self.context, self.config,
                                         None, None)
        self.assertIsNone(result)

        fake_service = mock.Mock(binary="keystone", status="enabled")
        clients.nova.services.list.return_value = [fake_service]
        result = self.validator.validate(self.context, self.config,
                                         None, None)
        self.assertIsNone(result)

        fake_service = mock.Mock(binary="nova-network", status="disabled")
        clients.nova.services.list.return_value = [fake_service]
        result = self.validator.validate(self.context, self.config,
                                         None, None)
        self.assertIsNone(result)

    def test_validator_wrong_service(self):

        self.config["context"]["api_versions@openstack"].get = mock.Mock(
            return_value={consts.Service.KEYSTONE: "service_type",
                          consts.Service.NOVA: "service_name"})

        clients = self.context["admin"].get("credential").clients()
        clients.services().values.return_value = [
            consts.Service.KEYSTONE, consts.Service.NOVA]

        validator = validators.RequiredServicesValidator([
            consts.Service.KEYSTONE,
            consts.Service.NOVA, "lol"])

        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, {}, None, None)
        expected_msg = ("'{0}' service is not available. Hint: If '{0}'"
                        " service has non-default service_type, try to setup"
                        " it via 'api_versions' context.").format("lol")
        self.assertEqual(expected_msg, e.message)


@ddt.ddt
class ValidateHeatTemplateValidatorTestCase(test.TestCase):

    def setUp(self):
        super(ValidateHeatTemplateValidatorTestCase, self).setUp()
        self.validator = validators.ValidateHeatTemplateValidator(
            "template_path1", "template_path2")
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    @ddt.data(
        {"exception_msg": "Heat template validation failed on fake_path1. "
                          "Original error message: fake_msg."},
        {"exception_msg": None}
    )
    @ddt.unpack
    @mock.patch("%s.os.path.exists" % PATH,
                return_value=True)
    @mock.patch("rally.plugins.openstack.validators.open",
                side_effect=mock.mock_open(), create=True)
    def test_validate(self, mock_open, mock_exists, exception_msg):
        clients = self.context["users"][0]["credential"].clients()
        mock_open().__enter__().read.side_effect = ["fake_template1",
                                                    "fake_template2"]
        heat_validator = mock.MagicMock()
        if exception_msg:
            heat_validator.side_effect = Exception("fake_msg")
        clients.heat().stacks.validate = heat_validator
        context = {"args": {"template_path1": "fake_path1",
                            "template_path2": "fake_path2"}}
        if not exception_msg:
            result = self.validator.validate(self.context, context, None, None)

            heat_validator.assert_has_calls([
                mock.call(template="fake_template1"),
                mock.call(template="fake_template2")
            ])
            mock_open.assert_has_calls([
                mock.call("fake_path1", "r"),
                mock.call("fake_path2", "r")
            ], any_order=True)
            self.assertIsNone(result)
        else:
            e = self.assertRaises(
                validators.validation.ValidationError,
                self.validator.validate, self.context, context, None, None)
            heat_validator.assert_called_once_with(
                template="fake_template1")
            self.assertEqual(
                "Heat template validation failed on fake_path1."
                " Original error message: fake_msg.", e.message)

    def test_validate_missed_params(self):
        validator = validators.ValidateHeatTemplateValidator(
            params="fake_param")

        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, self.config, None, None)

        expected_msg = ("Path to heat template is not specified. Its needed "
                        "for heat template validation. Please check the "
                        "content of `fake_param` scenario argument.")
        self.assertEqual(expected_msg, e.message)

    @mock.patch("%s.os.path.exists" % PATH,
                return_value=False)
    def test_validate_file_not_found(self, mock_exists):
        config = {"args": {"template_path1": "fake_path1",
                           "template_path2": "fake_path2"}}
        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator.validate, self.context, config, None, None)
        expected_msg = "No file found by the given path fake_path1"
        self.assertEqual(expected_msg, e.message)


class RequiredCinderServicesValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredCinderServicesValidatorTestCase, self).setUp()
        self.context = copy.deepcopy(context)
        self.config = copy.deepcopy(config)

    def test_validate(self):
        validator = validators.RequiredCinderServicesValidator(
            "cinder_service")

        fake_service = mock.Mock(binary="cinder_service", state="up")
        clients = self.context["admin"]["credential"].clients()
        clients.cinder().services.list.return_value = [fake_service]
        result = validator.validate(self.context, self.config, None, None)
        self.assertIsNone(result)

        fake_service.state = "down"
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, self.config, None, None)
        self.assertEqual("cinder_service service is not available",
                         e.message)


@ddt.ddt
class RequiredAPIVersionsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(RequiredAPIVersionsValidatorTestCase, self).setUp()
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    def _get_keystone_v2_mock_client(self):
        keystone = mock.Mock()
        del keystone.projects
        keystone.tenants = mock.Mock()
        return keystone

    def _get_keystone_v3_mock_client(self):
        keystone = mock.Mock()
        del keystone.tenants
        keystone.projects = mock.Mock()
        return keystone

    def test_validate(self):
        validator = validators.RequiredAPIVersionsValidator("keystone",
                                                            [2.0, 3])

        clients = self.context["users"][0]["credential"].clients()

        clients.keystone.return_value = self._get_keystone_v3_mock_client()
        validator.validate(self.context, self.config, None, None)

        clients.keystone.return_value = self._get_keystone_v2_mock_client()
        validator.validate(self.context, self.config, None, None)

    def test_validate_with_keystone_v2(self):
        validator = validators.RequiredAPIVersionsValidator("keystone",
                                                            [2.0])

        clients = self.context["users"][0]["credential"].clients()
        clients.keystone.return_value = self._get_keystone_v2_mock_client()
        validator.validate(self.context, self.config, None, None)

        clients.keystone.return_value = self._get_keystone_v3_mock_client()
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, self.config, None, None)
        self.assertEqual("Task was designed to be used with keystone V2.0, "
                         "but V3 is selected.", e.message)

    def test_validate_with_keystone_v3(self):
        validator = validators.RequiredAPIVersionsValidator("keystone",
                                                            [3])

        clients = self.context["users"][0]["credential"].clients()
        clients.keystone.return_value = self._get_keystone_v3_mock_client()
        validator.validate(self.context, self.config, None, None)

        clients.keystone.return_value = self._get_keystone_v2_mock_client()
        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, self.config, None, None)
        self.assertEqual("Task was designed to be used with keystone V3, "
                         "but V2.0 is selected.", e.message)

    @ddt.unpack
    @ddt.data(
        {"nova": 2, "versions": [2], "err_msg": None},
        {"nova": 3, "versions": [2],
         "err_msg": "Task was designed to be used with nova V2, "
                    "but V3 is selected."},
        {"nova": None, "versions": [2],
         "err_msg": "Unable to determine the API version."},
        {"nova": 2, "versions": [2, 3], "err_msg": None},
        {"nova": 4, "versions": [2, 3],
         "err_msg": "Task was designed to be used with nova V2, 3, "
                    "but V4 is selected."}
    )
    def test_validate_nova(self, nova, versions, err_msg):
        validator = validators.RequiredAPIVersionsValidator("nova",
                                                            versions)

        clients = self.context["users"][0]["credential"].clients()

        clients.nova.choose_version.return_value = nova
        config = {"contexts": {"api_versions@openstack": {}}}

        if err_msg:
            e = self.assertRaises(
                validators.validation.ValidationError,
                validator.validate, self.context, config, None, None)
            self.assertEqual(err_msg, e.message)
        else:
            result = validator.validate(self.context, config, None, None)
            self.assertIsNone(result)

    @ddt.unpack
    @ddt.data({"version": 2, "err_msg": None},
              {"version": 3, "err_msg": "Task was designed to be used with "
                                        "nova V3, but V2 is selected."})
    def test_validate_context(self, version, err_msg):
        validator = validators.RequiredAPIVersionsValidator("nova",
                                                            [version])

        config = {
            "contexts": {"api_versions@openstack": {"nova": {"version": 2}}}}

        if err_msg:
            e = self.assertRaises(
                validators.validation.ValidationError,
                validator.validate, self.context, config, None, None)
            self.assertEqual(err_msg, e.message)
        else:
            result = validator.validate(self.context, config, None, None)
            self.assertIsNone(result)


class VolumeTypeExistsValidatorTestCase(test.TestCase):

    def setUp(self):
        super(VolumeTypeExistsValidatorTestCase, self).setUp()
        self.validator = validators.VolumeTypeExistsValidator("volume_type",
                                                              True)
        self.config = copy.deepcopy(config)
        self.context = copy.deepcopy(context)

    def test_validator_without_ctx(self):
        validator = validators.VolumeTypeExistsValidator("fake_param",
                                                         nullable=True)

        clients = self.context["users"][0]["credential"].clients()

        clients.cinder().volume_types.list.return_value = [mock.MagicMock()]

        result = validator.validate(self.context, self.config, None, None)
        self.assertIsNone(result, "Unexpected result")

    def test_validator_without_ctx_failed(self):
        validator = validators.VolumeTypeExistsValidator("fake_param",
                                                         nullable=False)

        clients = self.context["users"][0]["credential"].clients()

        clients.cinder().volume_types.list.return_value = [mock.MagicMock()]

        e = self.assertRaises(
            validators.validation.ValidationError,
            validator.validate, self.context, self.config, None, None)
        self.assertEqual(
            "The parameter 'fake_param' is required and should not be empty.",
            e.message)

    def test_validate_with_ctx(self):
        clients = self.context["users"][0]["credential"].clients()
        clients.cinder().volume_types.list.return_value = []
        ctx = {"args": {"volume_type": "fake_type"},
               "contexts": {"volume_types": ["fake_type"]}}
        result = self.validator.validate(self.context, ctx, None, None)

        self.assertIsNone(result)

    def test_validate_with_ctx_failed(self):
        clients = self.context["users"][0]["credential"].clients()
        clients.cinder().volume_types.list.return_value = []
        config = {"args": {"volume_type": "fake_type"},
                  "contexts": {"volume_types": ["fake_type_2"]}}
        e = self.assertRaises(
            validators.validation.ValidationError,
            self.validator.validate, self.context, config, None, None)

        err_msg = ("Specified volume type fake_type not found for user {}. "
                   "List of available types: ['fake_type_2']")
        fake_user = self.context["users"][0]
        self.assertEqual(err_msg.format(fake_user), e.message)


@ddt.ddt
class WorkbookContainsWorkflowValidatorTestCase(test.TestCase):

    @mock.patch("rally.common.yamlutils.safe_load")
    @mock.patch("%s.os.access" % PATH)
    @mock.patch("%s.open" % PATH)
    def test_validator(self, mock_open, mock_access, mock_safe_load):
        mock_safe_load.return_value = {
            "version": "2.0",
            "name": "wb",
            "workflows": {
                "wf1": {
                    "type": "direct",
                    "tasks": {
                        "t1": {
                            "action": "std.noop"
                        }
                    }
                }
            }
        }
        validator = validators.WorkbookContainsWorkflowValidator(
            workbook_param="definition", workflow_param="workflow_name")

        config = {
            "args": {
                "definition": "fake_path1",
                "workflow_name": "wf1"
            }
        }

        result = validator.validate(None, config, None, None)
        self.assertIsNone(result)

        self.assertEqual(1, mock_open.called)
        self.assertEqual(1, mock_access.called)
        self.assertEqual(1, mock_safe_load.called)
