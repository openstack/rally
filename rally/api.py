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
import sys
import time

import jinja2
import jinja2.meta
import jsonschema
from oslo_config import cfg
from requests.packages import urllib3

from rally.common.i18n import _, _LI, _LE, _LW
from rally.common import logging
from rally.common import objects
from rally.common.plugin import discover
from rally.common import utils
from rally.common import version as rally_version
from rally import consts
from rally.deployment import engine as deploy_engine
from rally import exceptions
from rally import osclients
from rally.task import engine
from rally.ui import report
from rally.verification import context as vcontext
from rally.verification import manager as vmanager


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class _Deployment(object):

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
        try:
            deployer = deploy_engine.Engine.get_engine(
                deployment["config"]["type"], deployment)
            with deployer:
                deployer.make_cleanup()
        except exceptions.PluginNotFound:
            LOG.info(_("Deployment %s will be deleted despite exception")
                     % deployment["uuid"])

        for verifier in _Verifier.list():
            _Verifier.delete(verifier.name, deployment["name"], force=True)

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


class _Task(object):

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


class _Verifier(object):

    READY_TO_USE_STATES = (consts.VerifierStatus.INSTALLED,
                           consts.VerifierStatus.CONFIGURED)

    @classmethod
    def list_plugins(cls, namespace=None):
        """List all plugins for verifiers management.

        :param namespace: Verifier plugin namespace
        """
        return [{"name": p.get_name(),
                 "namespace": p.get_namespace(),
                 "description": p.get_info()["title"],
                 "location": "%s.%s" % (p.__module__, p.__name__)}
                for p in vmanager.VerifierManager.get_all(namespace=namespace)]

    @classmethod
    def create(cls, name, vtype, namespace=None, source=None, version=None,
               system_wide=False, extra_settings=None):
        """Create a verifier.

        :param name: Verifier name
        :param vtype: Verifier plugin name
        :param namespace: Verifier plugin namespace. Should be specified when
                          there are two verifier plugins with equal names but
                          in different namespaces
        :param source: Path or URL to the repo to clone verifier from
        :param version: Branch, tag or commit ID to checkout before
                        verifier installation
        :param system_wide: Whether or not to use the system-wide environment
                            for verifier instead of a virtual environment
        :param extra_settings: Extra installation settings for verifier
        """
        # check that the specified verifier type exists
        vmanager.VerifierManager.get(vtype, namespace=namespace)

        LOG.info("Creating verifier '%s'.", name)

        try:
            verifier = cls.get(name)
        except exceptions.ResourceNotFound:
            verifier = objects.Verifier.create(
                name=name, source=source, system_wide=system_wide,
                version=version, vtype=vtype, namespace=namespace,
                extra_settings=extra_settings)
        else:
            raise exceptions.RallyException(
                "Verifier with name '%s' already exists! Please, specify "
                "another name for verifier and try again." % verifier.name)

        verifier.update_status(consts.VerifierStatus.INSTALLING)
        try:
            verifier.manager.install()
        except Exception:
            verifier.update_status(consts.VerifierStatus.FAILED)
            raise
        verifier.update_status(consts.VerifierStatus.INSTALLED)

        LOG.info("Verifier %s has been successfully created!", verifier)

        return verifier.uuid

    @staticmethod
    def get(verifier_id):
        """Get a verifier.

        :param verifier_id: Verifier name or UUID
        """
        return objects.Verifier.get(verifier_id)

    @staticmethod
    def list(status=None):
        """List all verifiers.

        :param status: Status to filter verifiers by
        """
        return objects.Verifier.list(status)

    @classmethod
    def delete(cls, verifier_id, deployment_id=None, force=False):
        """Delete a verifier.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID. If specified,
                              only deployment-specific data will be deleted
                              for verifier
        :param force: Delete all stored verifier verifications.
                      If deployment_id specified, only deployment-specific
                      verifications will be deleted
        """
        verifier = cls.get(verifier_id)
        verifications = _Verification.list(verifier_id, deployment_id)
        if verifications:
            d_msg = ((" for deployment '%s'" % deployment_id)
                     if deployment_id else "")
            if force:
                LOG.info("Deleting all verifications created by verifier "
                         "%s%s.", verifier, d_msg)
                for verification in verifications:
                    _Verification.delete(verification.uuid)
            else:
                raise exceptions.RallyException(
                    "Failed to delete verifier {0} because there are stored "
                    "verifier verifications{1}! Please, make sure that they "
                    "are not important to you. Use 'force' flag if you would "
                    "like to delete verifications{1} as well."
                    .format(verifier, d_msg))

        if deployment_id:
            LOG.info("Deleting deployment-specific data for verifier %s.",
                     verifier)
            verifier.set_deployment(deployment_id)
            verifier.manager.uninstall()
            LOG.info("Deployment-specific data has been successfully deleted!")
        else:
            LOG.info("Deleting verifier %s.", verifier)
            verifier.manager.uninstall(full=True)
            objects.Verifier.delete(verifier_id)
            LOG.info("Verifier has been successfully deleted!")

    @classmethod
    def update(cls, verifier_id, system_wide=None, version=None,
               update_venv=False):
        """Update a verifier.

        :param verifier_id: Verifier name or UUID
        :param system_wide: Switch to using the system-wide environment
        :param version: Branch, tag or commit ID to checkout
        :param update_venv: Update the virtual environment for verifier
        """
        if system_wide is None and version is None and not update_venv:
            # nothing to update
            raise exceptions.RallyException(
                "At least one of the following parameters should be "
                "specified: 'system_wide', 'version', 'update_venv'.")

        verifier = cls.get(verifier_id)
        LOG.info("Updating verifier %s.", verifier)

        if verifier.status not in cls.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to update verifier %s because verifier is in '%s' "
                "status, but should be in %s." % (verifier, verifier.status,
                                                  cls.READY_TO_USE_STATES))

        system_wide_in_use = (system_wide or
                              (system_wide is None and verifier.system_wide))
        if update_venv and system_wide_in_use:
            raise exceptions.RallyException(
                "It is impossible to update the virtual environment for "
                "verifier %s when it uses the system-wide environment."
                % verifier)

        # store original status to set it again after updating or rollback
        original_status = verifier.status
        verifier.update_status(consts.VerifierStatus.UPDATING)

        properties = {}  # store new verifier properties to update old ones

        sw_is_checked = False

        if version:
            properties["version"] = version

            backup = utils.BackupHelper()
            rollback_msg = ("Failed to update verifier %s. It has been "
                            "rollbacked to the previous state." % verifier)
            backup.add_rollback_action(LOG.info, rollback_msg)
            backup.add_rollback_action(verifier.update_status, original_status)
            with backup(verifier.manager.repo_dir):
                verifier.manager.checkout(version)

            if system_wide_in_use:
                verifier.manager.check_system_wide()
                sw_is_checked = True

        if system_wide is not None:
            if system_wide == verifier.system_wide:
                LOG.info(
                    "Verifier %s is already switched to system_wide=%s. "
                    "Nothing will be changed.", verifier, verifier.system_wide)
            else:
                properties["system_wide"] = system_wide
                if not system_wide:
                    update_venv = True  # we need to install a virtual env
                else:
                    # NOTE(andreykurilin): should we remove previously created
                    #   virtual environment?!
                    if not sw_is_checked:
                        verifier.manager.check_system_wide()

        if update_venv:
            backup = utils.BackupHelper()
            rollback_msg = ("Failed to update the virtual environment for "
                            "verifier %s. It has been rollbacked to the "
                            "previous state." % verifier)
            backup.add_rollback_action(LOG.info, rollback_msg)
            backup.add_rollback_action(verifier.update_status, original_status)
            with backup(verifier.manager.venv_dir):
                verifier.manager.install_venv()

        properties["status"] = original_status  # change verifier status back
        verifier.update_properties(**properties)

        LOG.info("Verifier %s has been successfully updated!", verifier)

        return verifier.uuid

    @classmethod
    def configure(cls, verifier, deployment_id, extra_options=None,
                  recreate=False):
        """Configure a verifier.

        :param verifier: Verifier Object or (name or UUID)
        :param deployment_id: Deployment name or UUID
        :param extra_options: Add extra options to the verifier configuration
        :param recreate: Recreate the verifier configuration
        """
        if not isinstance(verifier, objects.Verifier):
            verifier = cls.get(verifier)
        verifier.set_deployment(deployment_id)
        LOG.info(
            "Configuring verifier %s for deployment '%s' (UUID=%s).",
            verifier, verifier.deployment["name"], verifier.deployment["uuid"])

        if verifier.status not in cls.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to configure verifier %s for deployment '%s' "
                "(UUID=%s) because verifier is in '%s' status, but should be "
                "in %s." % (verifier, verifier.deployment["name"],
                            verifier.deployment["uuid"], verifier.status,
                            cls.READY_TO_USE_STATES))

        msg = ("Verifier %s has been successfully configured for deployment "
               "'%s' (UUID=%s)!" % (verifier, verifier.deployment["name"],
                                    verifier.deployment["uuid"]))
        vm = verifier.manager
        if verifier.status == consts.VerifierStatus.CONFIGURED:
            LOG.info("Verifier is already configured!")
            if not recreate:
                if not extra_options:
                    return vm.get_configuration()
                else:
                    # Just add extra options to the config file.
                    if logging.is_debug():
                        LOG.debug("Adding the following extra options: %s "
                                  "to verifier configuration.", extra_options)
                    else:
                        LOG.info(
                            "Adding extra options to verifier configuration.")
                    verifier.update_status(consts.VerifierStatus.CONFIGURING)
                    vm.extend_configuration(extra_options)
                    verifier.update_status(consts.VerifierStatus.CONFIGURED)
                    LOG.info(msg)
                    return vm.get_configuration()

            LOG.info("Reconfiguring verifier.")

        verifier.update_status(consts.VerifierStatus.CONFIGURING)
        raw_config = vm.configure(extra_options=extra_options)
        verifier.update_status(consts.VerifierStatus.CONFIGURED)

        LOG.info(msg)

        return raw_config

    @classmethod
    def override_configuration(cls, verifier_id, deployment_id, new_content):
        """Override verifier configuration (e.g., rewrite the config file).

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param new_content: New content for the verifier configuration
        """
        verifier = cls.get(verifier_id)
        if verifier.status not in cls.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to override verifier configuration for deployment "
                "'%s' (UUID=%s) because verifier %s is in '%s' status, but "
                "should be in %s." % (
                    verifier.deployment["name"], verifier.deployment["uuid"],
                    verifier, verifier.status, cls.READY_TO_USE_STATES))

        LOG.info("Overriding configuration of verifier %s for deployment '%s' "
                 "(UUID=%s).", verifier, verifier.deployment["name"],
                 verifier.deployment["uuid"])

        verifier.set_deployment(deployment_id)
        verifier.update_status(consts.VerifierStatus.CONFIGURING)
        verifier.manager.override_configuration(new_content)
        verifier.update_status(consts.VerifierStatus.CONFIGURED)

        LOG.info("Configuration of verifier %s has been successfully "
                 "overridden for deployment '%s' (UUID=%s)!", verifier,
                 verifier.deployment["name"], verifier.deployment["uuid"])

    @classmethod
    def list_tests(cls, verifier_id, pattern=""):
        """List all verifier tests.

        :param verifier_id: Verifier name or UUID
        :param pattern: Pattern which will be used for matching
        """
        verifier = cls.get(verifier_id)
        if verifier.status not in cls.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to list verifier tests because verifier %s is in '%s' "
                "status, but should be in %s." % (verifier, verifier.status,
                                                  cls.READY_TO_USE_STATES))

        if pattern:
            verifier.manager.validate_args({"pattern": pattern})

        return verifier.manager.list_tests(pattern)

    @classmethod
    def add_extension(cls, verifier_id, source, version=None,
                      extra_settings=None):
        """Add a verifier extension.

        :param verifier_id: Verifier name or UUID
        :param source: Path or URL to the repo to clone verifier extension from
        :param version: Branch, tag or commit ID to checkout before
                        installation of the verifier extension
        :param extra_settings: Extra installation settings for verifier
                               extension
        """
        verifier = cls.get(verifier_id)
        if verifier.status not in cls.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to add verifier extension because verifier %s "
                "is in '%s' status, but should be in %s." % (
                    verifier, verifier.status, cls.READY_TO_USE_STATES))

        LOG.info("Adding extension for verifier %s.", verifier)

        # store original status to rollback it after failure
        original_status = verifier.status
        verifier.update_status(consts.VerifierStatus.EXTENDING)
        try:
            verifier.manager.install_extension(source, version=version,
                                               extra_settings=extra_settings)
        finally:
            verifier.update_status(original_status)

        LOG.info("Extension for verifier %s has been successfully added!",
                 verifier)

    @classmethod
    def list_extensions(cls, verifier_id):
        """List all verifier extensions.

        :param verifier_id: Verifier name or UUID
        """
        verifier = cls.get(verifier_id)
        if verifier.status not in cls.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to list verifier extensions because verifier %s "
                "is in '%s' status, but should be in %s." % (
                    verifier, verifier.status, cls.READY_TO_USE_STATES))

        return verifier.manager.list_extensions()

    @classmethod
    def delete_extension(cls, verifier_id, name):
        """Delete a verifier extension.

        :param verifier_id: Verifier name or UUID
        :param name: Verifier extension name
        """
        verifier = cls.get(verifier_id)
        if verifier.status not in cls.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to delete verifier extension because verifier %s "
                "is in '%s' status, but should be in %s." % (
                    verifier, verifier.status, cls.READY_TO_USE_STATES))

        LOG.info("Deleting extension for verifier %s.", verifier)
        verifier.manager.uninstall_extension(name)
        LOG.info("Extension for verifier %s has been successfully deleted!",
                 verifier)


class _Verification(object):

    @classmethod
    def start(cls, verifier_id, deployment_id, **run_args):
        """Start a verification.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param run_args: Dictionary with run arguments
        """
        # TODO(ylobankov): Add an ability to skip tests by specifying only test
        #                  names (without test IDs). Also, it would be nice to
        #                  skip the whole test suites. For example, all tests
        #                  in the class or module.

        verifier = _Verifier.get(verifier_id)
        if verifier.status not in _Verifier.READY_TO_USE_STATES:
            raise exceptions.RallyException(
                "Failed to start verification because verifier %s is in '%s' "
                "status, but should be in %s." % (
                    verifier, verifier.status, _Verifier.READY_TO_USE_STATES))

        verifier.set_deployment(deployment_id)
        if verifier.status != consts.VerifierStatus.CONFIGURED:
            _Verifier.configure(verifier, deployment_id)

        # TODO(andreykurilin): save validation results to db
        verifier.manager.validate(run_args)

        verification = objects.Verification.create(verifier_id,
                                                   deployment_id=deployment_id,
                                                   run_args=run_args)
        LOG.info("Starting verification (UUID=%s) for deployment '%s' "
                 "(UUID=%s) by verifier %s.", verification.uuid,
                 verifier.deployment["name"], verifier.deployment["uuid"],
                 verifier)
        verification.update_status(consts.VerificationStatus.RUNNING)

        context = {"config": verifier.manager._meta_get("context"),
                   "run_args": run_args,
                   "verification": verification,
                   "verifier": verifier}
        try:
            with vcontext.ContextManager(context):
                results = verifier.manager.run(context)
        except Exception as e:
            verification.set_error(e)
            raise

        # TODO(ylobankov): Check that verification exists in the database
        #                  because users may delete verification before tests
        #                  finish.
        verification.finish(results.totals, results.tests)

        LOG.info("Verification (UUID=%s) has been successfully finished for "
                 "deployment '%s' (UUID=%s)!", verification.uuid,
                 verifier.deployment["name"], verifier.deployment["uuid"])

        return verification, results

    @staticmethod
    def get(verification_uuid):
        """Get a verification.

        :param verification_uuid: Verification UUID
        """
        return objects.Verification.get(verification_uuid)

    @staticmethod
    def list(verifier_id=None, deployment_id=None, status=None):
        """List all verifications.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param status: Status to filter verifications by
        """
        return objects.Verification.list(verifier_id,
                                         deployment_id=deployment_id,
                                         status=status)

    @classmethod
    def delete(cls, verification_uuid):
        """Delete a verification.

        :param verification_uuid: Verification UUID
        """
        verification = cls.get(verification_uuid)
        LOG.info("Deleting verification (UUID=%s).", verification.uuid)
        verification.delete()
        LOG.info("Verification has been successfully deleted!")

    @classmethod
    def report(cls, uuids, html=False):
        """Generate a report for a verification or a few verifications.

        :param uuids: List of verifications UUIDs
        :param html: Whether or not to create the report in HTML format
        """
        verifications = [cls.get(uuid) for uuid in uuids]

        if html:
            return report.VerificationReport(verifications).to_html()

        return report.VerificationReport(verifications).to_json()

    @classmethod
    def import_results(cls, verifier_id, deployment_id, data, **run_args):
        """Import results of a test run into Rally database.

        :param verifier_id: Verifier name or UUID
        :param deployment_id: Deployment name or UUID
        :param data: Results data of a test run to import
        :param run_args: Dictionary with run arguments
        """
        # TODO(aplanas): Create an external deployment if this is missing, as
        # required in the blueprint [1].
        # [1] https://blueprints.launchpad.net/rally/+spec/verification-import

        verifier = _Verifier.get(verifier_id)
        verifier.set_deployment(deployment_id)
        LOG.info("Importing test results into a new verification for "
                 "deployment '%s' (UUID=%s), using verifier %s.",
                 verifier.deployment["name"], verifier.deployment["uuid"],
                 verifier)

        verifier.manager.validate_args(run_args)

        verification = objects.Verification.create(verifier_id,
                                                   deployment_id=deployment_id,
                                                   run_args=run_args)
        verification.update_status(consts.VerificationStatus.RUNNING)

        try:
            results = verifier.manager.parse_results(data)
        except Exception as e:
            verification.set_failed(e)
            raise
        verification.finish(results.totals, results.tests)

        LOG.info("Test results have been successfully imported.")

        return verification, results


class _DeprecatedAPIClass(object):
    """Deprecates direct usage of api classes."""
    def __init__(self, cls):
        self._cls = cls

    def __getattr__(self, attr, default=None):
        LOG.warn(_LW("'%s' is deprecated since Rally 0.8.0 in favor of "
                     "'rally.api.API' class.") % self._cls.__name__[1:])
        return getattr(self._cls, attr, default)


Deployment = _DeprecatedAPIClass(_Deployment)
Task = _DeprecatedAPIClass(_Task)


class API(object):

    CONFIG_SEARCH_PATHS = [sys.prefix + "/etc/rally", "~/.rally", "/etc/rally"]
    CONFIG_FILE_NAME = "rally.conf"

    def __init__(self, config_file=None, config_args=None,
                 rally_endpoint=None, plugin_paths=None, skip_db_check=False):
        """Initialize Rally API instance

        :param config_file: Path to rally configuration file. If None, default
                            path will be selected
        :type config_file: str
        :param config_args: Arguments for initialization current configuration
        :type config_args: list
        :param rally_endpoint: [Restricted]Rally endpoint connection string.
        :type rally_endpoint: str
        :param plugin_paths: Additional custom plugin locations
        :type plugin_paths: list
        :param skip_db_check: Allows to skip db revision check
        :type skip_db_check: bool
        """
        if rally_endpoint:
            raise NotImplementedError(_LE("Sorry, but Rally-as-a-Service is "
                                          "not ready yet."))
        try:
            config_files = ([config_file] if config_file else
                            self._default_config_file())
            CONF(config_args or [],
                 project="rally",
                 version=rally_version.version_string(),
                 default_config_files=config_files)
            logging.setup("rally")
            if not CONF.get("log_config_append"):
                # The below two lines are to disable noise from request module.
                # The standard way should be we make such lots of settings on
                # the root rally. However current oslo codes doesn't support
                # such interface. So I choose to use a 'hacking' way to avoid
                # INFO logs from request module where user didn't give specific
                # log configuration. And we could remove this hacking after
                # oslo.log has such interface.
                LOG.debug(
                    "INFO logs from urllib3 and requests module are hide.")
                requests_log = logging.getLogger("requests").logger
                requests_log.setLevel(logging.WARNING)
                urllib3_log = logging.getLogger("urllib3").logger
                urllib3_log.setLevel(logging.WARNING)

                LOG.debug("urllib3 insecure warnings are hidden.")
                for warning in ("InsecurePlatformWarning",
                                "SNIMissingWarning",
                                "InsecureRequestWarning"):
                    warning_cls = getattr(urllib3.exceptions, warning, None)
                    if warning_cls is not None:
                        urllib3.disable_warnings(warning_cls)

            # NOTE(wtakase): This is for suppressing boto error logging.
            LOG.debug("ERROR log from boto module is hide.")
            boto_log = logging.getLogger("boto").logger
            boto_log.setLevel(logging.CRITICAL)

            # Set alembic log level to ERROR
            alembic_log = logging.getLogger("alembic").logger
            alembic_log.setLevel(logging.ERROR)

        except cfg.ConfigFilesNotFoundError as e:
            cfg_files = e.config_files
            raise exceptions.RallyException(_LE(
                "Failed to read configuration file(s): %s") % cfg_files)

        # Check that db is upgraded to the latest revision
        if not skip_db_check:
            self._check_db_revision()

        # Load plugins
        plugin_paths = plugin_paths or []
        if "plugin_paths" in CONF:
            plugin_paths.extend(CONF.get("plugin_paths") or [])
        for path in plugin_paths:
            discover.load_plugins(path)

        # NOTE(andreykurilin): There is no reason to auto-discover API's. We
        # have only 4 classes, so let's do it in good old way - hardcode them:)
        self._deployment = _Deployment
        self._task = _Task
        self._verifier = _Verifier
        self._verification = _Verification

    def _default_config_file(self):
        for path in self.CONFIG_SEARCH_PATHS:
            abspath = os.path.abspath(os.path.expanduser(path))
            fpath = os.path.join(abspath, self.CONFIG_FILE_NAME)
            if os.path.isfile(fpath):
                return [fpath]

    def _check_db_revision(self):
        rev = rally_version.database_revision()
        if rev["revision"] == rev["current_head"]:
            return
        raise exceptions.RallyException(_LE(
            "Database seems to be outdated. Run upgrade from "
            "revision %(revision)s to %(current_head)s by command "
            "`rally-manage db upgrade'") % rev)

    @property
    def deployment(self):
        return self._deployment

    @property
    def task(self):
        return self._task

    @property
    def verifier(self):
        return self._verifier

    @property
    def verification(self):
        return self._verification
