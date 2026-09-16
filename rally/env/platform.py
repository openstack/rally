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

import typing as t

import typing_extensions as te

from rally.common import utils
from rally.common import validation
from rally.common.plugin import plugin


if t.TYPE_CHECKING:  # pragma: no cover
    P = t.TypeVar("P", bound="Platform")


class _PlatformStatus(utils.ImmutableMixin, utils.EnumMixin):
    """Rally Env Statuses."""

    INIT = "INITIALIZING"
    SKIPPED = "SKIPPED"

    READY = "READY"
    FAILED_TO_CREATE = "FAILED TO CREATE"

    DESTROYING = "DESTROYING"
    FAILED_TO_DESTROY = "FAILED TO DESTROY"
    DESTROYED = "DESTROYED"

    TRANSITION_TABLE = {
        INIT: (READY, SKIPPED, FAILED_TO_CREATE),
        READY: (DESTROYING,),
        FAILED_TO_CREATE: (DESTROYING,),
        DESTROYING: (DESTROYED, FAILED_TO_DESTROY),
        FAILED_TO_DESTROY: (DESTROYING,),
    }


STATUS = _PlatformStatus()


class HealthInfo(te.TypedDict):
    """The result of :meth:`Platform.check_health`."""

    available: bool
    message: te.NotRequired[str]
    traceback: te.NotRequired[str]


class PlatformInfo(te.TypedDict):
    """The result of :meth:`Platform.info`."""

    info: t.Any
    error: te.NotRequired[str]
    traceback: te.NotRequired[str]


class CleanupCounters(t.TypedDict):
    """The numbers of resources of one type processed by a cleanup."""

    discovered: int
    deleted: int
    failed: int


class CleanupError(te.TypedDict):
    """A resource that a cleanup failed to delete."""

    message: str
    resource_id: te.NotRequired[str]
    resource_type: te.NotRequired[str]
    traceback: te.NotRequired[str]


class CleanupInfo(te.TypedDict):
    """The result of :meth:`Platform.cleanup`."""

    message: te.NotRequired[str]
    discovered: int
    deleted: int
    failed: int
    resources: dict[str, CleanupCounters]
    errors: list[CleanupError]


class SysEnvSpec(te.TypedDict):
    """The result of :meth:`Platform.create_spec_from_sys_environ`."""

    available: bool
    spec: te.NotRequired[dict[str, t.Any]]
    message: te.NotRequired[str]
    traceback: te.NotRequired[str]


def configure(name: str, platform: str) -> t.Callable[[type[P]], type[P]]:
    """Configure platform plugin.

    Platform is building block for Env.

    :param name: str platform plugin name
    :param platform: str thing that is described by this plugin

    """

    def wrapper(cls: type[P]) -> type[P]:
        return plugin.configure(name=name, platform=platform)(cls)

    return wrapper


@validation.add_default("jsonschema")
@plugin.base()
class Platform(plugin.Plugin, validation.ValidatablePluginMixin):
    """Base class for platform plugins.

    A platform plugin teaches Rally about one kind of target. The part of the
    environment spec that belongs to the plugin is validated against its
    ``CONFIG_SCHEMA`` and is available as ``self.spec``.

    Every method is optional, implement the ones that make sense for the
    target. The data returned by :meth:`create` is available as
    ``self.platform_data`` and ``self.plugin_data``.
    """

    def __init__(
        self,
        spec: dict[str, t.Any],
        uuid: str | None = None,
        plugin_data: dict[str, t.Any] | None = None,
        platform_data: dict[str, t.Any] | None = None,
        status: str | None = None,
    ) -> None:
        """Create instance of platform.

        :param spec: the part of the environment spec of the plugin
        :param uuid: the UUID of the platform record
        :param plugin_data: plugin data returned by the create method
        :param platform_data: platform data returned by the create method
        :param status: the status of the platform record
        """
        self.spec = spec
        self.uuid = uuid
        self.plugin_data = plugin_data
        self.platform_data = platform_data
        self.status = status

    def create(self) -> tuple[dict[str, t.Any], dict[str, t.Any]]:
        """Make the target usable.

        Called once, when the environment is created. A plugin that only
        describes an already existing target has nothing to do here.

        Platforms of an environment are created one by one. If this method
        raises, the platform and the whole environment get the
        ``FAILED TO CREATE`` status, and the platforms that were not created
        yet are marked as ``SKIPPED``.

        :returns: a tuple of two dicts, ``platform_data`` and ``plugin_data``.
            Both are stored in the database.
        """
        raise NotImplementedError(
            f"Platform {self.get_fullname()} doesn't support create action"
        )

    def destroy(self) -> None:
        """Undo what :meth:`create` did.

        Called by ``rally env destroy``, after :meth:`cleanup` unless the
        cleanup is skipped. If this method raises, the platform gets the
        ``FAILED TO DESTROY`` status and the destroy can be retried.
        """
        raise NotImplementedError(
            f"Platform {self.get_fullname()} doesn't support destroy action"
        )

    def update(self, new_spec: dict[str, t.Any]) -> dict[str, t.Any]:
        """Apply a new spec to an existing platform.

        Reserved for the future: Rally does not call it yet.

        :param new_spec: the new spec of the plugin
        :returns: the new platform data
        """
        raise NotImplementedError(
            f"Platform {self.get_fullname()} doesn't support update action"
        )

    def cleanup(self, task_uuid: str | None = None) -> CleanupInfo:
        """Find and delete the resources that tasks left behind.

        Called by ``rally env cleanup`` and by ``rally env destroy``. A plugin
        that does not support it is reported as "Not implemented".

        :param task_uuid: clean up only the resources of this task
        :returns: a dict with the number of ``discovered``, ``deleted`` and
            ``failed`` resources, the same numbers per resource type in
            ``resources``, and a list of ``errors``, each with a ``message``
            and optional ``resource_id``, ``resource_type`` and
            ``traceback``. An optional ``message`` summarizes the result.
        """
        raise NotImplementedError(
            f"Platform {self.get_fullname()} doesn't support cleanup action"
        )

    def check_health(self) -> HealthInfo:
        """Check whether the target is alive and usable.

        Called by ``rally env check``.

        :returns: a dict with a boolean ``available`` and an optional
            ``message``, e.g. the reason why the target is not available
        """
        raise NotImplementedError(
            f"Platform {self.get_fullname()} doesn't support health check "
            f"action"
        )

    def info(self) -> PlatformInfo:
        """Describe what the target provides.

        Called by ``rally env info``, which prints the result as it is.

        :returns: a dict with ``info`` of any shape, e.g. the list of services
            of a cloud
        """
        raise NotImplementedError(
            f"Platform {self.get_fullname()} doesn't support info action"
        )

    def _get_validation_context(self) -> dict[str, t.Any]:
        """Return the context that validators of the platform need.

        Called before a task is validated. The contexts of all platforms of
        the environment are merged into one. Most plugins need nothing here.
        """
        return {}

    @classmethod
    def create_spec_from_sys_environ(
        cls, sys_environ: t.Mapping[str, str]
    ) -> SysEnvSpec:
        """Build a spec from credentials found in environment variables.

        Called by ``rally env create --from-sysenv``. The base implementation
        reports that nothing was found, which fits a target that has no such
        convention.

        :param sys_environ: a copy of the environment variables
        :returns: a dict with a boolean ``available``, the ``spec`` of the
            plugin when credentials were found, and an optional ``message``
            that tells what was found or why nothing was
        """
        return SysEnvSpec(
            available=False, message="Skipped. No credentials found."
        )
