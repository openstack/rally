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

from rally.common.plugin import plugin
from rally.common import utils
from rally.common import validation


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
        READY: (DESTROYING, ),
        FAILED_TO_CREATE: (DESTROYING, ),
        DESTROYING: (DESTROYED, FAILED_TO_DESTROY),
        FAILED_TO_DESTROY: (DESTROYING, )
    }


STATUS = _PlatformStatus()


def configure(name, platform):
    """Configure platform plugin.

    Platform is building block for Env.

    :param name: str platform plugin name
    :param platform: str thing that is described by this plugin

    """
    def wrapper(cls):
        return plugin.configure(name=name, platform=platform)(cls)

    return wrapper


@validation.add_default("jsonschema")
@plugin.base()
class Platform(plugin.Plugin, validation.ValidatablePluginMixin):

    def __init__(self, spec,
                 uuid=None, plugin_data=None, platform_data=None, status=None):
        """Create instance of platform and validates config.

        :param platform_config: Platform configuration file
        :param platform_data: Platform specific data returned by create method
    """
        self.spec = spec
        self.uuid = uuid
        self.plugin_data = plugin_data
        self.platform_data = platform_data
        self.status = status

    def create(self):
        """Perform operations required to create platform.

        :returns: Complete platform data as dictionary
        """
        raise NotImplementedError(
            "Platform %s doesn't support create action" % self.get_fullname())

    def destroy(self):
        """Destroys platform."""
        raise NotImplementedError(
            "Platform %s doesn't support destroy action" % self.get_fullname())

    def update(self, new_spec):
        """Updates existing platform config and returns new platform data.

        :param new_platform_config: New platform config.
        :returns: Complete platform data as dictionary
        """
        raise NotImplementedError(
            "Platform %s doesn't support update action" % self.get_fullname())

    def cleanup(self, task_uuid=None):
        """Disaster cleanup for platform."""
        raise NotImplementedError(
            "Platform %s doesn't support cleanup action" % self.get_fullname())

    def check_health(self):
        """Check whatever platform is alive."""
        raise NotImplementedError(
            "Platform %s doesn't support health check action"
            % self.get_fullname())

    def info(self):
        """Return information about platform as dictionary."""
        raise NotImplementedError(
            "Platform %s doesn't support info action" % self.get_fullname())

    def get_validation_context(self):
        """Return a validation context for a platform."""
        return {}

    @classmethod
    def create_spec_from_sys_environ(cls, sys_environ):
        """Check system env for credentials and return a spec if present."""
        return {"available": False,
                "message": "Skipped. No credentials found."}
