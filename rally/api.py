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

import os
import re
import time

import jinja2
import jinja2.meta
import jsonschema

from rally.common.i18n import _, _LI, _LE
from rally.common import logging
from rally.common import objects
from rally import consts
from rally.deployment import engine as deploy_engine
from rally import exceptions
from rally import osclients
from rally.task import engine
from rally.verification.tempest import tempest

LOG = logging.getLogger(__name__)


class Deployment(object):

    @classmethod
    def create(cls, config, name):
        """Create a deployment.

        :param config: a dict with deployment configuration
        :param name: a str represents a name of the deployment
        :returns: Deployment object
        """

        try:
            deployment = objects.Deployment(name=name, config=config)
        except exceptions.DeploymentNameExists as e:
            if logging.is_debug():
                LOG.exception(e)
            raise

        deployer = deploy_engine.Engine.get_engine(
            deployment["config"]["type"], deployment)
        try:
            deployer.validate()
        except jsonschema.ValidationError:
            LOG.error(_LE("Deployment %s: Schema validation error.") %
                      deployment["uuid"])
            deployment.update_status(consts.DeployStatus.DEPLOY_FAILED)
            raise

        with deployer:
            credentials = deployer.make_deploy()
            deployment.update_credentials(credentials)
            return deployment

    @classmethod
    def destroy(cls, deployment):
        """Destroy the deployment.

        :param deployment: UUID or name of the deployment
        """
        # TODO(akscram): We have to be sure that there are no running
        #                tasks for this deployment.
        # TODO(akscram): Check that the deployment have got a status that
        #                is equal to "*->finished" or "deploy->inconsistent".
        deployment = objects.Deployment.get(deployment)
        tempest.Tempest(deployment["uuid"]).uninstall()
        try:
            deployer = deploy_engine.Engine.get_engine(
                deployment["config"]["type"], deployment)
            with deployer:
                deployer.make_cleanup()
        except exceptions.PluginNotFound:
            LOG.info(_("Deployment %s will be deleted despite"
                       " exception") % deployment["uuid"])

        deployment.delete()

    @classmethod
    def recreate(cls, deployment):
        """Performs a cleanup and then makes a deployment again.

        :param deployment: UUID or name of the deployment
        """
        deployment = objects.Deployment.get(deployment)
        deployer = deploy_engine.Engine.get_engine(
            deployment["config"]["type"], deployment)
        with deployer:
            deployer.make_cleanup()
            credentials = deployer.make_deploy()
            deployment.update_credentials(credentials)

    @classmethod
    def get(cls, deployment):
        """Get the deployment.

        :param deployment: UUID or name of the deployment
        :returns: Deployment instance
        """
        return objects.Deployment.get(deployment)

    @classmethod
    def service_list(cls, deployment):
        """Get the services list.

        :param deployment: Deployment object
        :returns: Service list
        """
        # TODO(kun): put this work into objects.Deployment
        clients = osclients.Clients(objects.Credential(**deployment["admin"]))
        return clients.services()

    @staticmethod
    def list(status=None, parent_uuid=None, name=None):
        """Get the deployments list.

        :returns: Deployment list
        """
        return objects.Deployment.list(status, parent_uuid, name)

    @classmethod
    def check(cls, deployment):
        """Check keystone authentication and list all available services.

        :returns: Service list
        """
        services = cls.service_list(deployment)
        users = deployment["users"]
        for endpoint_dict in users:
            osclients.Clients(objects.Credential(**endpoint_dict)).keystone()

        return services


class Task(object):

    TASK_RESULT_SCHEMA = objects.task.TASK_RESULT_SCHEMA

    @staticmethod
    def list(**filters):
        return objects.Task.list(**filters)

    @staticmethod
    def get(task_id):
        return objects.Task.get(task_id)

    @staticmethod
    def get_detailed(task_id, extended_results=False):
        """Get detailed task data.

        :param task_id: str task UUID
        :param extended_results: whether to return task data as dict
                                 with extended results
        :returns: rally.common.db.sqlalchemy.models.Task
        :returns: dict
        """
        task = objects.Task.get_detailed(task_id)
        if task and extended_results:
            task = dict(task)
            task["results"] = objects.Task.extend_results(task["results"])
        return task

    @classmethod
    def render_template(cls, task_template, template_dir="./", **kwargs):
        """Render jinja2 task template to Rally input task.

        :param task_template: String that contains template
        :param template_dir: The path of directory contain template files
        :param kwargs: Dict with template arguments
        :returns: rendered template str
        """

        def is_really_missing(mis, task_template):
            # NOTE(boris-42): Removing variables that have default values from
            #                 missing. Construction that won't be properly
            #                 checked is {% set x = x or 1}
            if re.search(mis.join(["{%\s*set\s+", "\s*=\s*", "[^\w]+"]),
                         task_template):
                return False
            # NOTE(jlk): Also check for a default filter which can show up as
            #            a missing variable
            if re.search(mis + "\s*\|\s*default\(", task_template):
                return False
            return True

        # NOTE(boris-42): We have to import builtins to get the full list of
        #                 builtin functions (e.g. range()). Unfortunately,
        #                 __builtins__ doesn't return them (when it is not
        #                 main module)
        from six.moves import builtins

        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir, encoding="utf8"))
        env.globals.update(cls.create_template_functions())
        ast = env.parse(task_template)
        # NOTE(Julia Varigina):
        # Bug in jinja2.meta.find_undeclared_variables
        #
        # The method shows inconsistent behavior:
        # it does not return undeclared variables that appear
        # in included templates only (via {%- include "some_template.yaml"-%})
        # and in the same time is declared in jinja2.Environment.globals.
        #
        # This is different for undeclared variables that appear directly
        # in task_template. The method jinja2.meta.find_undeclared_variables
        # returns an undeclared variable that is used in task_template
        # and is set in jinja2.Environment.globals.
        #
        # Despite this bug, jinja resolves values
        # declared in jinja2.Environment.globals for both types of undeclared
        # variables and successfully renders templates in both cases.
        required_kwargs = jinja2.meta.find_undeclared_variables(ast)
        missing = (set(required_kwargs) - set(kwargs) - set(dir(builtins)) -
                   set(env.globals))
        real_missing = [mis for mis in missing
                        if is_really_missing(mis, task_template)]
        if real_missing:
            multi_msg = _("Please specify next template task arguments: %s")
            single_msg = _("Please specify template task argument: %s")

            raise TypeError((len(real_missing) > 1 and multi_msg or single_msg)
                            % ", ".join(real_missing))

        return env.from_string(task_template).render(**kwargs)

    @classmethod
    def create_template_functions(cls):

        def template_min(int1, int2):
            return min(int1, int2)

        def template_max(int1, int2):
            return max(int1, int2)

        def template_round(float1):
            return int(round(float1))

        def template_ceil(float1):
            import math
            return int(math.ceil(float1))

        return {"min": template_min, "max": template_max,
                "ceil": template_ceil, "round": template_round}

    @classmethod
    def create(cls, deployment, tag):
        """Create a task without starting it.

        Task is a list of benchmarks that will be called one by one, results of
        execution will be stored in DB.

        :param deployment: UUID or name of the deployment
        :param tag: tag for this task
        :returns: Task object
        """

        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        return objects.Task(deployment_uuid=deployment_uuid, tag=tag)

    @classmethod
    def validate(cls, deployment, config, task_instance=None):
        """Validate a task config against specified deployment.

        :param deployment: UUID or name of the deployment
        :param config: a dict with a task configuration
        """
        deployment = objects.Deployment.get(deployment)
        task = task_instance or objects.Task(
            deployment_uuid=deployment["uuid"], temporary=True)
        benchmark_engine = engine.TaskEngine(
            config, task, admin=deployment["admin"], users=deployment["users"])

        benchmark_engine.validate()

    @classmethod
    def start(cls, deployment, config, task=None, abort_on_sla_failure=False):
        """Start a task.

        Task is a list of benchmarks that will be called one by one, results of
        execution will be stored in DB.

        :param deployment: UUID or name of the deployment
        :param config: a dict with a task configuration
        :param task: Task object. If None, it will be created
        :param abort_on_sla_failure: If set to True, the task execution will
                                     stop when any SLA check for it fails
        """
        deployment = objects.Deployment.get(deployment)
        task = task or objects.Task(deployment_uuid=deployment["uuid"])

        if task.is_temporary:
            raise ValueError(_(
                "Unable to run a temporary task. Please check your code."))

        LOG.info("Benchmark Task %s on Deployment %s" % (task["uuid"],
                                                         deployment["uuid"]))
        benchmark_engine = engine.TaskEngine(
            config, task, admin=deployment["admin"], users=deployment["users"],
            abort_on_sla_failure=abort_on_sla_failure)

        try:
            benchmark_engine.run()
        except Exception:
            deployment.update_status(consts.DeployStatus.DEPLOY_INCONSISTENT)
            raise

    @classmethod
    def abort(cls, task_uuid, soft=False, async=True):
        """Abort running task.

        :param task_uuid: The UUID of the task
        :type task_uuid: str
        :param soft: If set to True, task should be aborted after execution of
                     current scenario, otherwise as soon as possible before
                     all the scenario iterations finish [Default: False]
        :type soft: bool
        :param async: don't wait until task became in 'running' state
                      [Default: False]
        :type async: bool
        """

        if not async:
            current_status = objects.Task.get_status(task_uuid)
            if current_status in objects.Task.NOT_IMPLEMENTED_STAGES_FOR_ABORT:
                LOG.info(_LI("Task status is '%s'. Should wait until it became"
                             " 'running'") % current_status)
                while (current_status in
                       objects.Task.NOT_IMPLEMENTED_STAGES_FOR_ABORT):
                    time.sleep(1)
                    current_status = objects.Task.get_status(task_uuid)

        objects.Task.get(task_uuid).abort(soft=soft)

        if not async:
            LOG.info(_LI("Waiting until the task stops."))
            finished_stages = [consts.TaskStatus.ABORTED,
                               consts.TaskStatus.FINISHED,
                               consts.TaskStatus.FAILED]
            while objects.Task.get_status(task_uuid) not in finished_stages:
                time.sleep(1)

    @classmethod
    def delete(cls, task_uuid, force=False):
        """Delete the task.

        :param task_uuid: The UUID of the task
        :param force: If set to True, then delete the task despite to the
                      status
        :raises TaskInvalidStatus: when the status of the task is not
                                   in FINISHED, FAILED or ABORTED and
                                   the force argument is not True
        """
        if force:
            objects.Task.delete_by_uuid(task_uuid, status=None)
        elif objects.Task.get_status(task_uuid) in (
                consts.TaskStatus.ABORTED,
                consts.TaskStatus.FINISHED,
                consts.TaskStatus.FAILED):
            objects.Task.delete_by_uuid(task_uuid, status=None)
        else:
            objects.Task.delete_by_uuid(
                task_uuid, status=consts.TaskStatus.FINISHED)


class Verification(object):

    @staticmethod
    def _check_tempest_tree_existence(verifier):
        if not os.path.exists(verifier.path()):
            msg = _("Tempest tree for "
                    "deployment '%s' not found! ") % verifier.deployment
            LOG.error(
                msg + _("Use `rally verify install` for Tempest installation"))
            raise exceptions.NotFoundException(message=msg)

    @classmethod
    def verify(cls, deployment, set_name="", regex=None, tests_file=None,
               tests_file_to_skip=None, tempest_config=None,
               expected_failures=None, system_wide=False, concur=0,
               failing=False):
        """Start verification.

        :param deployment: UUID or name of a deployment
        :param set_name: Name of a Tempest test set
        :param regex: Regular expression of test
        :param tests_file: Path to a file with a list of Tempest tests
                           to run them
        :param tests_file_to_skip: Path to a file with a list of Tempest tests
                                   to skip them
        :param tempest_config: User specified Tempest config file location
        :param expected_failures: Dictionary with Tempest tests that are
                                  expected to fail. Keys are test names;
                                  values are reasons of test failures
        :param system_wide: Whether or not to create a virtual env when
                            installing Tempest; whether or not to use
                            the local env instead of the Tempest virtual
                            env when running the tests
        :param concur: How many processes to use to run Tempest tests.
                       The default value (0) auto-detects CPU count
        :param failing: Re-run tests that failed during the last execution
        :returns: Verification object
        """

        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verification = objects.Verification(deployment_uuid=deployment_uuid)
        verifier = tempest.Tempest(deployment_uuid,
                                   verification=verification,
                                   tempest_config=tempest_config,
                                   system_wide=system_wide)

        cls._check_tempest_tree_existence(verifier)

        LOG.info("Starting verification of deployment: %s" % deployment_uuid)
        verification.set_running()
        verifier.verify(set_name=set_name, regex=regex, tests_file=tests_file,
                        tests_file_to_skip=tests_file_to_skip,
                        expected_failures=expected_failures, concur=concur,
                        failing=failing)

        return verification

    @classmethod
    def import_results(cls, deployment, set_name="", log_file=None):
        """Import Tempest tests results into the Rally database.

        :param deployment: UUID or name of a deployment
        :param log_file: User specified Tempest log file in subunit format
        :returns: Deployment and verification objects
        """
        # TODO(aplanas): Create an external deployment if this is
        # missing, as required in the blueprint [1].
        # [1] https://blueprints.launchpad.net/rally/+spec/verification-import
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verification = objects.Verification(deployment_uuid=deployment_uuid)
        verifier = tempest.Tempest(deployment_uuid, verification=verification)

        LOG.info("Importing verification of deployment: %s" % deployment_uuid)
        verification.set_running()
        verifier.import_results(set_name=set_name, log_file=log_file)

        return deployment, verification

    @classmethod
    def install_tempest(cls, deployment, source=None, version=None,
                        system_wide=False):
        """Install Tempest.

        :param deployment: UUID or name of a deployment
        :param source: Path/URL to repo to clone Tempest from
        :param version: Commit ID or tag to checkout before Tempest
                        installation
        :param system_wide: Whether or not to install Tempest package and
                            create a Tempest virtual env
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid, source=source,
                                   version=version, system_wide=system_wide)
        verifier.install()

    @classmethod
    def uninstall_tempest(cls, deployment):
        """Remove deployment's local Tempest installation.

        :param deployment: UUID or name of a deployment
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid)
        verifier.uninstall()

    @classmethod
    def reinstall_tempest(cls, deployment, source=None, version=None,
                          system_wide=False):
        """Uninstall Tempest and install again.

        :param deployment: UUID or name of a deployment
        :param source: Path/URL to repo to clone Tempest from
        :param version: Commit ID or tag to checkout before Tempest
                        installation
        :param system_wide: Whether or not to install Tempest package and
                            create a Tempest virtual env
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid, source=source,
                                   version=version, system_wide=system_wide)
        verifier.uninstall()
        verifier.install()

    @classmethod
    def install_tempest_plugin(cls, deployment, source=None, version=None,
                               system_wide=False):
        """Install Tempest plugin.

        :param deployment: UUID or name of a deployment
        :param source: Path/URL to repo to clone Tempest plugin from
        :param version: Branch, commit ID or tag to checkout before Tempest
                        plugin installation
        :param system_wide: Install plugin in Tempest virtual env or
                            in the local env
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid,
                                   plugin_source=source,
                                   plugin_version=version,
                                   system_wide=system_wide)

        cls._check_tempest_tree_existence(verifier)

        verifier.install_plugin()

    @classmethod
    def list_tempest_plugins(cls, deployment, system_wide=False):
        """List all installed Tempest plugins.

        :param deployment: UUID or name of a deployment
        :param system_wide: List all plugins installed in the local env or
                            in Tempest virtual env
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid, system_wide=system_wide)

        cls._check_tempest_tree_existence(verifier)

        return verifier.list_plugins()

    @classmethod
    def uninstall_tempest_plugin(cls, deployment, repo_name,
                                 system_wide=False):
        """Uninstall Tempest plugin.

        :param deployment: UUID or name of a deployment
        :param repo_name: Plugin repo name
        :param system_wide: Uninstall plugin from Tempest virtual env or
                            from the local env
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid, system_wide=system_wide)
        verifier.uninstall_plugin(repo_name)

    @classmethod
    def discover_tests(cls, deployment, pattern="", system_wide=False):
        """Get a list of discovered tests.

        :param deployment: UUID or name of a deployment
        :param pattern: Test name pattern which can be used to match
        :param system_wide: Discover tests for system-wide or venv
                            Tempest installation
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid, system_wide=system_wide)

        cls._check_tempest_tree_existence(verifier)

        return verifier.discover_tests(pattern)

    @classmethod
    def configure_tempest(cls, deployment, tempest_config=None,
                          extra_conf=None, override=False):
        """Generate Tempest configuration file.

        :param deployment: UUID or name of a deployment
        :param tempest_config: User specified Tempest config file location
        :param extra_conf: A ConfigParser() object with options to
                           extend/update Tempest config file
        :param override: Whether or not to override existing Tempest
                         config file
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid,
                                   tempest_config=tempest_config)

        cls._check_tempest_tree_existence(verifier)

        verifier.generate_config_file(extra_conf, override)

    @classmethod
    def show_config_info(cls, deployment):
        """Get information about Tempest configuration file.

        :param deployment: UUID or name of a deployment
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid)

        cls._check_tempest_tree_existence(verifier)

        if not verifier.is_configured():
            verifier.generate_config_file()

        with open(verifier.config_file, "rb") as conf:
            return {"conf_data": conf.read(),
                    "conf_path": verifier.config_file}

    @staticmethod
    def list(status=None):
        """List all verifications.

        :param status: Filter verifications by the specified status
        """
        return objects.Verification.list(status)

    @staticmethod
    def get(verification_uuid):
        """Get verification.

        :param verification_uuid: UUID of a verification
        """
        return objects.Verification.get(verification_uuid)
