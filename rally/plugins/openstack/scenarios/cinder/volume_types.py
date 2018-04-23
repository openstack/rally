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

from rally.common import logging
from rally import consts
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.plugins.openstack.services.storage import cinder_v2
from rally.task import validation


LOG = logging.getLogger(__name__)


"""Scenarios for Cinder Volume Type."""


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderVolumeTypes.create_and_delete_volume_type",
                    platform="openstack")
class CreateAndDeleteVolumeType(cinder_utils.CinderBasic):

    def run(self, description=None, is_public=True):
        """Create and delete a volume Type.

        :param description: Description of the volume type
        :param is_public: Volume type visibility
        """
        volume_type = self.admin_cinder.create_volume_type(
            description=description,
            is_public=is_public)
        self.admin_cinder.delete_volume_type(volume_type)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderVolumeTypes.create_and_get_volume_type",
                    platform="openstack")
class CreateAndGetVolumeType(cinder_utils.CinderBasic):

    def run(self, description=None, is_public=True):
        """Create a volume Type, then get the details of the type.

        :param description: Description of the volume type
        :param is_public: Volume type visibility
        """
        volume_type = self.admin_cinder.create_volume_type(
            description=description,
            is_public=is_public)
        self.admin_cinder.get_volume_type(volume_type)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_api_versions", component="cinder", versions=["2"])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderVolumeTypes.create_and_update_volume_type",
                    platform="openstack")
class CreateAndUpdateVolumeType(scenario.OpenStackScenario):

    def run(self, description=None, is_public=True, update_name=False,
            update_description=None, update_is_public=None):
        """create a volume type, then update the type.

        :param description: Description of the volume type
        :param is_public: Volume type visibility
        :param update_name: if True, can update name by generating random name.
                            if False, don't update name.
        :param update_description: update Description of the volume type
        :param update_is_public: update Volume type visibility
        """
        service = cinder_v2.CinderV2Service(self._admin_clients,
                                            self.generate_random_name,
                                            atomic_inst=self.atomic_actions())

        volume_type = service.create_volume_type(
            description=description,
            is_public=is_public)

        service.update_volume_type(
            volume_type,
            name=volume_type.name if not update_name else False,
            description=update_description,
            is_public=update_is_public)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderVolumeTypes.create_and_list_volume_types",
                    platform="openstack")
class CreateAndListVolumeTypes(cinder_utils.CinderBasic):

    def run(self, description=None, is_public=True):
        """Create a volume Type, then list all types.

        :param description: Description of the volume type
        :param is_public: Volume type visibility
        """
        volume_type = self.admin_cinder.create_volume_type(
            description=description,
            is_public=is_public)

        pool_list = self.admin_cinder.list_types()
        msg = ("type not included into list of available types"
               "created type: {}\n"
               "pool of types: {}\n").format(volume_type, pool_list)
        self.assertIn(volume_type.id,
                      [vtype.id for vtype in pool_list],
                      err_msg=msg)


@validation.add("required_params", params=[("create_specs", "provider")])
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={"admin_cleanup@openstack": ["cinder"]},
    name="CinderVolumeTypes.create_volume_type_and_encryption_type",
    platform="openstack")
class CreateVolumeTypeAndEncryptionType(cinder_utils.CinderBasic):

    def run(self, create_specs=None, provider=None, cipher=None,
            key_size=None, control_location="front-end", description=None,
            is_public=True):
        """Create encryption type

        This scenario first creates a volume type, then creates an encryption
        type for the volume type.

        :param create_specs: The encryption type specifications to add.
                             DEPRECATED, specify arguments explicitly.
        :param provider: The class that provides encryption support. For
                         example, LuksEncryptor.
        :param cipher: The encryption algorithm or mode.
        :param key_size: Size of encryption key, in bits.
        :param control_location: Notional service where encryption is
                                 performed. Valid values are "front-end"
                                 or "back-end."
        :param description: Description of the volume type
        :param is_public: Volume type visibility
        """
        volume_type = self.admin_cinder.create_volume_type(
            description=description,
            is_public=is_public)
        if create_specs is None:
            specs = {
                "provider": provider,
                "cipher": cipher,
                "key_size": key_size,
                "control_location": control_location
            }
        else:
            LOG.warning("The argument `create_spec` is deprecated since"
                        " Rally 0.10.0. Specify all arguments from it"
                        " explicitly.")
            specs = create_specs
        self.admin_cinder.create_encryption_type(volume_type,
                                                 specs=specs)


@validation.add("required_params", params=[("create_specs", "provider")])
@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={"admin_cleanup@openstack": ["cinder"]},
    name="CinderVolumeTypes.create_and_list_encryption_type",
    platform="openstack")
class CreateAndListEncryptionType(cinder_utils.CinderBasic):

    def run(self, create_specs=None, provider=None, cipher=None,
            key_size=None, control_location="front-end", search_opts=None):
        """Create and list encryption type

        This scenario firstly creates a volume type, secondly creates an
        encryption type for the volume type, thirdly lists all encryption
        types.

        :param create_specs: The encryption type specifications to add.
                             DEPRECATED, specify arguments explicitly.
        :param provider: The class that provides encryption support. For
                         example, LuksEncryptor.
        :param cipher: The encryption algorithm or mode.
        :param key_size: Size of encryption key, in bits.
        :param control_location: Notional service where encryption is
                                 performed. Valid values are "front-end"
                                 or "back-end."
        :param search_opts: Options used when search for encryption types
        """
        vt_idx = self.context["iteration"] % len(self.context["volume_types"])
        volume_type = self.context["volume_types"][vt_idx]
        if create_specs is None:
            specs = {
                "provider": provider,
                "cipher": cipher,
                "key_size": key_size,
                "control_location": control_location
            }
        else:
            LOG.warning("The argument `create_spec` is deprecated since"
                        " Rally 0.10.0. Specify all arguments from it"
                        " explicitly.")
            specs = create_specs
        self.admin_cinder.create_encryption_type(volume_type["id"],
                                                 specs=specs)
        self.admin_cinder.list_encryption_type(search_opts)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderVolumeTypes.create_and_set_volume_type_keys",
                    platform="openstack")
class CreateAndSetVolumeTypeKeys(cinder_utils.CinderBasic):

    def run(self, volume_type_key, description=None, is_public=True):
        """Create and set a volume type's extra specs.

        :param volume_type_key:  A dict of key/value pairs to be set
        :param description: Description of the volume type
        :param is_public: Volume type visibility
        """
        volume_type = self.admin_cinder.create_volume_type(
            description=description,
            is_public=is_public)
        self.admin_cinder.set_volume_type_keys(volume_type,
                                               metadata=volume_type_key)


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_contexts", contexts="volume_types")
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={"admin_cleanup@openstack": ["cinder"]},
    name="CinderVolumeTypes.create_get_and_delete_encryption_type",
    platform="openstack")
class CreateGetAndDeleteEncryptionType(cinder_utils.CinderBasic):

    def run(self, provider=None, cipher=None,
            key_size=None, control_location="front-end"):
        """Create get and delete an encryption type

        This scenario firstly creates an encryption type for a volome
        type created in the context, then gets detailed information of
        the created encryption type, finally deletes the created
        encryption type.

        :param provider: The class that provides encryption support. For
                         example, LuksEncryptor.
        :param cipher: The encryption algorithm or mode.
        :param key_size: Size of encryption key, in bits.
        :param control_location: Notional service where encryption is
                                 performed. Valid values are "front-end"
                                 or "back-end."
        """
        vt_idx = self.context["iteration"] % len(self.context["volume_types"])
        volume_type = self.context["volume_types"][vt_idx]
        specs = {
            "provider": provider,
            "cipher": cipher,
            "key_size": key_size,
            "control_location": control_location
        }
        self.admin_cinder.create_encryption_type(volume_type["id"],
                                                 specs=specs)
        self.admin_cinder.get_encryption_type(volume_type["id"])
        self.admin_cinder.delete_encryption_type(volume_type["id"])


@validation.add("required_services", services=[consts.Service.CINDER])
@validation.add("required_contexts", contexts="volume_types")
@validation.add("required_params", params=[("create_specs", "provider")])
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(
    context={"admin_cleanup@openstack": ["cinder"]},
    name="CinderVolumeTypes.create_and_delete_encryption_type",
    platform="openstack")
class CreateAndDeleteEncryptionType(cinder_utils.CinderBasic):

    def run(self, create_specs=None, provider=None, cipher=None,
            key_size=None, control_location="front-end"):
        """Create and delete encryption type

        This scenario firstly creates an encryption type for a given
        volume type, then deletes the created encryption type.

        :param create_specs: the encryption type specifications to add
        :param provider: The class that provides encryption support. For
                         example, LuksEncryptor.
        :param cipher: The encryption algorithm or mode.
        :param key_size: Size of encryption key, in bits.
        :param control_location: Notional service where encryption is
                                 performed. Valid values are "front-end"
                                 or "back-end."
        """
        vt_idx = self.context["iteration"] % len(self.context["volume_types"])
        volume_type = self.context["volume_types"][vt_idx]
        if create_specs is None:
            specs = {
                "provider": provider,
                "cipher": cipher,
                "key_size": key_size,
                "control_location": control_location
            }
        else:
            LOG.warning("The argument `create_spec` is deprecated since"
                        " Rally 0.10.0. Specify all arguments from it"
                        " explicitly.")
            specs = create_specs
        self.admin_cinder.create_encryption_type(volume_type["id"],
                                                 specs=specs)
        self.admin_cinder.delete_encryption_type(volume_type["id"])


@validation.add("required_services", services=consts.Service.CINDER)
@validation.add("required_contexts", contexts="volume_types")
@validation.add("required_platform", platform="openstack", admin=True)
@scenario.configure(context={"admin_cleanup@openstack": ["cinder"]},
                    name="CinderVolumeTypes.create_and_update_encryption_type",
                    platform="openstack")
class CreateAndUpdateEncryptionType(cinder_utils.CinderBasic):

    def run(self, create_provider=None, create_cipher=None,
            create_key_size=None, create_control_location="front-end",
            update_provider=None, update_cipher=None,
            update_key_size=None, update_control_location=None):
        """Create and update encryption type

        This scenario firstly creates a volume type, secondly creates an
        encryption type for the volume type, thirdly updates the encryption
        type.

        :param create_provider: The class that provides encryption support. For
                                example, LuksEncryptor.
        :param create_cipher: The encryption algorithm or mode.
        :param create_key_size: Size of encryption key, in bits.
        :param create_control_location: Notional service where encryption is
                                        performed. Valid values are "front-end"
                                        or "back-end."
        :param update_provider: The class that provides encryption support. For
                                example, LuksEncryptor.
        :param update_cipher: The encryption algorithm or mode.
        :param update_key_size: Size of encryption key, in bits.
        :param update_control_location: Notional service where encryption is
                                        performed. Valid values are "front-end"
                                        or "back-end."
        """
        vt_idx = self.context["iteration"] % len(self.context["volume_types"])
        volume_type = self.context["volume_types"][vt_idx]
        create_specs = {
            "provider": create_provider,
            "cipher": create_cipher,
            "key_size": create_key_size,
            "control_location": create_control_location
        }
        update_specs = {
            "provider": update_provider,
            "cipher": update_cipher,
            "key_size": update_key_size,
            "control_location": update_control_location
        }
        self.admin_cinder.create_encryption_type(volume_type["id"],
                                                 specs=create_specs)
        self.admin_cinder.update_encryption_type(volume_type["id"],
                                                 specs=update_specs)


@validation.add("required_platform", platform="openstack", admin=True)
@validation.add("required_api_versions", component="cinder", versions=["2"])
@validation.add("required_services", services=consts.Service.CINDER)
@scenario.configure(
    context={"admin_cleanup@openstack": ["cinder"]},
    name="CinderVolumeTypes.create_volume_type_add_and_list_type_access",
    platform="openstack")
class CreateVolumeTypeAddAndListTypeAccess(scenario.OpenStackScenario):

    def run(self, description=None, is_public=False):
        """Add and list volume type access for the given project.

        This scenario first creates a private volume type, then add project
        access and list project access to it.

        :param description: Description of the volume type
        :param is_public: Volume type visibility
        """
        service = cinder_v2.CinderV2Service(self._admin_clients,
                                            self.generate_random_name,
                                            atomic_inst=self.atomic_actions())
        volume_type = service.create_volume_type(description=description,
                                                 is_public=is_public)
        service.add_type_access(volume_type,
                                project=self.context["tenant"]["id"])
        service.list_type_access(volume_type)
