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

import os
import shutil
import tempfile
import uuid
import zipfile

from oslo_config import cfg
import yaml

from rally.common import fileutils
from rally.common import utils as common_utils
from rally.plugins.openstack import scenario
from rally.task import atomic
from rally.task import utils

CONF = cfg.CONF

MURANO_BENCHMARK_OPTS = [
    cfg.IntOpt("murano_deploy_environment_timeout", default=1200,
               deprecated_name="deploy_environment_timeout",
               help="A timeout in seconds for an environment deploy"),
    cfg.IntOpt("murano_deploy_environment_check_interval", default=5,
               deprecated_name="deploy_environment_check_interval",
               help="Deploy environment check interval in seconds"),
]

benchmark_group = cfg.OptGroup(name="benchmark", title="benchmark options")
CONF.register_opts(MURANO_BENCHMARK_OPTS, group=benchmark_group)


class MuranoScenario(scenario.OpenStackScenario):
    """Base class for Murano scenarios with basic atomic actions."""

    @atomic.action_timer("murano.list_environments")
    def _list_environments(self):
        """Return environments list."""
        return self.clients("murano").environments.list()

    @atomic.action_timer("murano.create_environment")
    def _create_environment(self):
        """Create environment.

        :param env_name: String used to name environment

        :returns: Environment instance
        """
        env_name = self.generate_random_name()
        return self.clients("murano").environments.create({"name": env_name})

    @atomic.action_timer("murano.delete_environment")
    def _delete_environment(self, environment):
        """Delete given environment.

        Return when the environment is actually deleted.

        :param environment: Environment instance
        """
        self.clients("murano").environments.delete(environment.id)

    @atomic.action_timer("murano.create_session")
    def _create_session(self, environment_id):
        """Create session for environment with specific id

        :param environment_id: Environment id
        :returns: Session instance
        """
        return self.clients("murano").sessions.configure(environment_id)

    @atomic.optional_action_timer("murano.create_service")
    def _create_service(self, environment, session, full_package_name,
                        image_name=None, flavor_name=None):
        """Create Murano service.

        :param environment: Environment instance
        :param session: Session instance
        :param full_package_name: full name of the Murano package
        :param image_name: Image name
        :param flavor_name: Flavor name
        :param atomic_action: True if this is atomic action. added and
                              handled by the optional_action_timer()
                              decorator
        :returns: Service instance
        """
        app_id = str(uuid.uuid4())
        data = {"?": {"id": app_id,
                      "type": full_package_name},
                "name": self.generate_random_name()}

        return self.clients("murano").services.post(
            environment_id=environment.id, path="/", data=data,
            session_id=session.id)

    @atomic.action_timer("murano.deploy_environment")
    def _deploy_environment(self, environment, session):
        """Deploy environment.

        :param environment: Environment instance
        :param session: Session instance
        """
        self.clients("murano").sessions.deploy(environment.id,
                                               session.id)

        config = CONF.benchmark
        utils.wait_for(
            environment,
            ready_statuses=["READY"],
            update_resource=utils.get_from_manager(["DEPLOY FAILURE"]),
            timeout=config.murano_deploy_environment_timeout,
            check_interval=config.murano_deploy_environment_check_interval
        )

    @atomic.action_timer("murano.list_packages")
    def _list_packages(self, include_disabled=False):
        """Returns packages list.

        :param include_disabled: if "True" then disabled packages will be
                                 included in a the result.
                                 Default value is False.
        :returns: list of imported packages
        """
        return self.clients("murano").packages.list(
            include_disabled=include_disabled)

    @atomic.action_timer("murano.import_package")
    def _import_package(self, package):
        """Import package to the Murano.

        :param package: path to zip archive with Murano application
        :returns: imported package
        """

        package = self.clients("murano").packages.create(
            {}, {"file": open(package)}
        )

        return package

    @atomic.action_timer("murano.delete_package")
    def _delete_package(self, package):
        """Delete specified package.

        :param package: package that will be deleted
        """

        self.clients("murano").packages.delete(package.id)

    @atomic.action_timer("murano.update_package")
    def _update_package(self, package, body, operation="replace"):
        """Update specified package.

        :param package: package that will be updated
        :param body: dict object that defines what package property will be
                     updated, e.g {"tags": ["tag"]} or {"enabled": "true"}
        :param operation: string object that defines the way of how package
                          property will be updated, allowed operations are
                          "add", "replace" or "delete".
                          Default value is "replace".
        :returns: updated package
        """

        return self.clients("murano").packages.update(
            package.id, body, operation)

    @atomic.action_timer("murano.filter_applications")
    def _filter_applications(self, filter_query):
        """Filter list of uploaded application by specified criteria.

        :param filter_query: dict that contains filter criteria, it
                             will be passed as **kwargs to filter method
                             e.g. {"category": "Web"}
        :returns: filtered list of packages
        """

        return self.clients("murano").packages.filter(**filter_query)

    def _zip_package(self, package_path):
        """Call _prepare_package method that returns path to zip archive."""
        return MuranoPackageManager(self.task)._prepare_package(package_path)


class MuranoPackageManager(common_utils.RandomNameGeneratorMixin):
    RESOURCE_NAME_FORMAT = "app.rally_XXXXXXXX_XXXXXXXX"

    def __init__(self, task):
        self.task = task

    @staticmethod
    def _read_from_file(filename):
        with open(filename, "r") as f:
            read_data = f.read()
        return yaml.safe_load(read_data)

    @staticmethod
    def _write_to_file(data, filename):
        with open(filename, "w") as f:
            yaml.safe_dump(data, f)

    def _change_app_fullname(self, app_dir):
        """Change application full name.

        To avoid name conflict error during package import (when user
        tries to import a few packages into the same tenant) need to change the
        application name. For doing this need to replace following parts
        in manifest.yaml
        from
            ...
            FullName: app.name
            ...
            Classes:
              app.name: app_class.yaml
        to:
            ...
            FullName: <new_name>
            ...
            Classes:
              <new_name>: app_class.yaml

        :param app_dir: path to directory with Murano application context
        """

        new_fullname = self.generate_random_name()

        manifest_file = os.path.join(app_dir, "manifest.yaml")
        manifest = self._read_from_file(manifest_file)

        class_file_name = manifest["Classes"][manifest["FullName"]]

        # update manifest.yaml file
        del manifest["Classes"][manifest["FullName"]]
        manifest["FullName"] = new_fullname
        manifest["Classes"][new_fullname] = class_file_name
        self._write_to_file(manifest, manifest_file)

    def _prepare_package(self, package_path):
        """Check whether the package path is path to zip archive or not.

        If package_path is not a path to zip archive but path to Murano
        application folder, than method prepares zip archive with Murano
        application. It copies directory with Murano app files to temporary
        folder, changes manifest.yaml and class file (to avoid '409 Conflict'
        errors in Murano) and prepares zip package.

        :param package_path: path to zip archive or directory with package
                             components
        :returns: path to zip archive with Murano application
        """

        if not zipfile.is_zipfile(package_path):
            tmp_dir = tempfile.mkdtemp()
            pkg_dir = os.path.join(tmp_dir, "package/")
            try:
                shutil.copytree(package_path, pkg_dir)

                self._change_app_fullname(pkg_dir)
                package_path = fileutils.pack_dir(pkg_dir)

            finally:
                shutil.rmtree(tmp_dir)

        return package_path
