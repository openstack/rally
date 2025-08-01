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

from __future__ import annotations

import abc
import traceback
import typing as t

from rally.common import logging
from rally.common.plugin import plugin
from rally import exceptions

if t.TYPE_CHECKING:  # pragma: no cover
    P = t.TypeVar("P", bound=plugin.Plugin)
    V = t.TypeVar("V", bound="Validator")

LOG = logging.getLogger(__name__)


def configure(
    name: str, platform: str = "default"
) -> t.Callable[[type[V]], type[V]]:
    """Configure validator plugin with name and platform."""
    def wrapper(cls: type[V]) -> type[V]:
        return plugin.configure(name=name, platform=platform)(cls)

    return wrapper


@plugin.base()
class Validator(plugin.Plugin, metaclass=abc.ABCMeta):
    """A base class for all validators."""

    def __init__(self) -> None:
        pass

    @abc.abstractmethod
    def validate(
        self,
        context: dict[str, t.Any],
        config: dict[str, t.Any] | None,
        plugin_cls: type[plugin.Plugin],
        plugin_cfg: dict[str, t.Any] | None
    ) -> None:
        """Method that validates something.

        :param context: a validation context
        :param config: dict, configuration of workload
        :param plugin_cls: plugin class
        :param plugin_cfg: dict, with exact configuration of the plugin
        :returns: None if succeeded
        :raises ValidationError: if the config doesn't pass the validator
        """

    @staticmethod
    def fail(msg: str) -> t.NoReturn:
        raise ValidationError(msg)

    @classmethod
    def _get_doc(cls) -> str:
        doc = ""
        if cls.__doc__ is not None:
            doc = cls.__doc__
        if cls.__init__.__doc__ is not None:
            if not cls.__init__.__doc__.startswith("\n"):
                doc += "\n"
            doc += cls.__init__.__doc__
        return doc


@configure(name="required_platform")
class RequiredPlatformValidator(Validator):

    def __init__(self, platform: str, **kwargs: t.Any) -> None:
        """Validates specification of specified platform for the workload.

        :param platform: name of the platform
        """
        super(RequiredPlatformValidator, self).__init__()
        self.platform = platform
        self._kwargs = kwargs

    def validate(
        self,
        context: dict[str, t.Any],
        config: dict[str, t.Any] | None,
        plugin_cls: type[plugin.Plugin],
        plugin_cfg: dict[str, t.Any] | None
    ) -> None:
        try:
            pvalidator_cls = RequiredPlatformValidator.get(
                "required_platform",
                platform=self.platform,
                allow_hidden=True)
        except exceptions.PluginNotFound:
            # There is no specific validation for this platform

            if self.platform not in context["platforms"]:
                self.fail("There is no specification for %s platform in "
                          "selected environment." % self.platform)

            if self.platform == "openstack":
                # NOTE(andreykurilin): We had in-tree openstack plugins for a
                #   long time. It will be a hard task to remove this logic
                #   easily, since even rally-openstack project (the new
                #   location for openstack plugins) use common
                #   "required_platform" validator.
                admin = self._kwargs.get("admin", False)
                users = self._kwargs.get("users", False)
                if not (admin or users):
                    self.fail(
                        "You should specify admin=True or users=True or both "
                        "for validating openstack platform.")

                platform_context = context["platforms"].get(self.platform, {})

                if admin and platform_context.get("admin") is None:
                    self.fail("No admin credential for %s" % self.platform)
                if users and len(platform_context.get("users", ())) == 0:
                    if platform_context.get("admin") is None:
                        self.fail("No user credentials for %s" % self.platform)
                    else:
                        # NOTE(andreykurilin): It is a case when the plugin
                        #   requires 'users' for launching, but there are no
                        #   specified users in deployment. Let's assume that
                        #   'users' context can create them via admin user
                        #   and do not fail."
                        pass
        else:
            pvalidator = pvalidator_cls(**self._kwargs)
            pvalidator.validate(context=context,
                                config=config,
                                plugin_cls=plugin_cls,
                                plugin_cfg=plugin_cfg)


def add(name: str, **kwargs: t.Any) -> t.Callable[[type[P]], type[P]]:
    """Add validator to the plugin class meta.

    Add validator name and arguments to validators list stored in the
    plugin meta by 'validators' key. This would be used to iterate
    and execute through all validators during execution of subtask.

    :param name: str, name of the validator plugin
    :param kwargs: dict, arguments used to initialize validator class
        instance
    """

    def wrapper(plugin: type[P]) -> type[P]:
        if issubclass(plugin, RequiredPlatformValidator):
            raise exceptions.RallyException(
                "Cannot add a validator to RequiredPlatformValidator")
        elif issubclass(plugin, Validator) and name != "required_platform":
            raise exceptions.RallyException(
                "Only RequiredPlatformValidator can be added "
                "to other validators as a validator")

        plugin._meta_setdefault("validators", [])
        plugin._meta_get("validators").append((name, (), kwargs,))
        return plugin

    return wrapper


def add_default(name: str, **kwargs: t.Any) -> t.Callable[[type[P]], type[P]]:
    """Add validator to the plugin class default meta.

    Validator is added to all subclasses by default

    :param name: str, full name of the validator plugin
    :param kwargs: dict, validator plugin arguments
    """

    def wrapper(plugin: type[P]) -> type[P]:
        plugin._default_meta_setdefault("validators", [])
        plugin._default_meta_get("validators").append((name, (), kwargs,))
        return plugin
    return wrapper


# this class doesn't inherit from rally.exceptions.RallyException, since
#   ValidationError should be used only for inner purpose.
class ValidationError(Exception):
    def __init__(self, message: str) -> None:
        super(ValidationError, self).__init__(message)
        self.message = message


_ValidatorInfo = tuple[type[Validator], tuple[t.Any, ...], dict[str, t.Any]]


class ValidatablePluginMixin:

    @staticmethod
    def _load_validators(plugin: type[plugin.Plugin]) -> list[_ValidatorInfo]:
        validators = plugin._meta_get("validators", default=[])
        return [(Validator.get(name), args, kwargs)
                for name, args, kwargs in validators]

    @classmethod
    def validate(
        cls,
        name: str,
        context: dict[str, t.Any],
        config: dict[str, t.Any] | None,
        plugin_cfg: dict[str, t.Any] | None,
        allow_hidden: bool = False,
        vtype: str | list[str] | tuple[str, ...] | None = None
    ) -> list[str]:
        """Execute all validators stored in meta of plugin.

        Iterate during all validators stored in the meta of Validator
        and execute proper validate() method and add validation result
        to the list.

        :param name: full name of the plugin to validate
        :param context: a validation context
        :param config: dict with configuration of specified workload
        :param plugin_cfg: dict, with exact configuration of the plugin
        :param allow_hidden: do not ignore hidden plugins
        :param vtype: Type of validation. Allowed types: syntax, platform,
            semantic. HINT: To specify several types use tuple or list with
            types
        :returns: list of ValidationResult(is_valid=False) instances
        """
        try:
            plugin_cls = t.cast(plugin.Plugin, cls).get(
                name, allow_hidden=allow_hidden)
        except exceptions.PluginNotFound as e:
            return [e.format_message()]

        if vtype is None:
            semantic = True
            syntax = True
            platform = True
        else:
            if not isinstance(vtype, (list, tuple)):
                vtype = [vtype]
            wrong_types = set(vtype) - {"semantic", "syntax", "platform"}
            if wrong_types:
                raise ValueError("Wrong type of validation: %s" %
                                 ", ".join(wrong_types))
            semantic = "semantic" in vtype
            syntax = "syntax" in vtype
            platform = "platform" in vtype

        syntax_validators: list[_ValidatorInfo] = []
        platform_validators: list[_ValidatorInfo] = []
        regular_validators: list[_ValidatorInfo] = []

        plugin_validators = cls._load_validators(plugin_cls)
        for validator_cls, args, kwargs in plugin_validators:
            if issubclass(validator_cls, RequiredPlatformValidator):
                if platform:
                    platform_validators.append((validator_cls, args, kwargs))
            else:
                validators_of_validators = cls._load_validators(validator_cls)
                if validators_of_validators:
                    if semantic:
                        regular_validators.append(
                            (validator_cls, args, kwargs))
                    if platform:
                        # Load platform validators from each validator
                        platform_validators.extend(validators_of_validators)
                else:
                    if syntax:
                        syntax_validators.append((validator_cls, args, kwargs))

        results: list[str] = []
        for validators in (syntax_validators, platform_validators,
                           regular_validators):
            for validator_cls, args, kwargs in validators:
                validator = validator_cls(*args, **kwargs)
                result: str | None = None
                try:
                    validator.validate(
                        context=context,
                        config=config,
                        plugin_cls=plugin_cls,
                        plugin_cfg=plugin_cfg)
                except ValidationError as e:
                    result = e.message
                except Exception:
                    # Unexpected error is returned. save traceback as well
                    result = traceback.format_exc()
                if result:
                    results.append(
                        f"{cls.__name__} plugin '{name}' doesn't pass "
                        f"{validator_cls.get_fullname()} validation. "
                        f"Details: {result}"
                    )
            if results:
                break

        return results
