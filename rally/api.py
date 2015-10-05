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
import shutil
import tempfile
import time

import jinja2
import jinja2.meta
import jsonschema

from rally.common.i18n import _, _LI
from rally.common import log as logging
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
            LOG.error(_("Deployment %s: Schema validation error.") %
                      deployment["uuid"])
            deployment.update_status(consts.DeployStatus.DEPLOY_FAILED)
            raise

        with deployer:
            endpoints = deployer.make_deploy()
            deployment.update_endpoints(endpoints)
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
        deployer = deploy_engine.Engine.get_engine(
            deployment["config"]["type"], deployment)

        tempest.Tempest(deployment["uuid"]).uninstall()
        with deployer:
            deployer.make_cleanup()
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
            endpoints = deployer.make_deploy()
            deployment.update_endpoints(endpoints)

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
        clients = osclients.Clients(objects.Endpoint(**deployment["admin"]))
        return clients.services()


class Task(object):

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
        ast = env.parse(task_template)
        required_kwargs = jinja2.meta.find_undeclared_variables(ast)

        missing = set(required_kwargs) - set(kwargs) - set(dir(builtins))
        real_missing = [mis for mis in missing
                        if is_really_missing(mis, task_template)]

        if real_missing:
            multi_msg = _("Please specify next template task arguments: %s")
            single_msg = _("Please specify template task argument: %s")

            raise TypeError((len(real_missing) > 1 and multi_msg or single_msg)
                            % ", ".join(real_missing))

        return env.from_string(task_template).render(**kwargs)

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
        benchmark_engine = engine.BenchmarkEngine(
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
        :param abort_on_sla_failure: if True, the execution of a benchmark
                                     scenario will stop when any SLA check
                                     for it fails
        """
        deployment = objects.Deployment.get(deployment)
        task = task or objects.Task(deployment_uuid=deployment["uuid"])

        if task.is_temporary:
            raise ValueError(_(
                "Unable to run a temporary task. Please check your code."))

        LOG.info("Benchmark Task %s on Deployment %s" % (task["uuid"],
                                                         deployment["uuid"]))
        benchmark_engine = engine.BenchmarkEngine(
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
        :param soft: if set to True, task should be aborted after execution of
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

        :param task_uuid: The UUID of the task.
        :param force: If set to True, then delete the task despite to the
                      status.
        :raises: :class:`rally.exceptions.TaskInvalidStatus` when the
                 status of the task is not FINISHED and the force argument
                 if not True
        """
        status = None if force else consts.TaskStatus.FINISHED
        objects.Task.delete_by_uuid(task_uuid, status=status)


class Verification(object):

    @classmethod
    def verify(cls, deployment, set_name, regex, tempest_config,
               system_wide_install=False):
        """Start verifying.

        :param deployment: UUID or name of a deployment.
        :param set_name: Valid name of tempest test set.
        :param regex: Regular expression of test
        :param tempest_config: User specified Tempest config file
        :param system_wide_install: Use virtualenv else run tests in local
                                    environment
        :returns: Verification object
        """

        deployment_uuid = objects.Deployment.get(deployment)["uuid"]

        verification = objects.Verification(deployment_uuid=deployment_uuid)
        verifier = cls._create_verifier(deployment_uuid, verification,
                                        tempest_config, system_wide_install)
        LOG.info("Starting verification of deployment: %s" % deployment_uuid)

        verification.set_running()
        verifier.verify(set_name=set_name, regex=regex)

        return verification

    @staticmethod
    def _create_verifier(deployment_uuid, verification=None,
                         tempest_config=None, system_wide_install=False):
        """Create a Tempest object.

        :param deployment_uuid: UUID or name of a deployment
        :param verification: Verification object
        :param tempest_config: User specified Tempest config file
        :param system_wide_install: Use virtualenv else run tests in local
                                    environment
        :return: Tempest object
        """
        verifier = tempest.Tempest(deployment_uuid, verification=verification,
                                   tempest_config=tempest_config,
                                   system_wide_install=system_wide_install)
        if not verifier.is_installed():
            LOG.info(_("Tempest is not installed "
                       "for the specified deployment."))
            LOG.info(_("Installing Tempest "
                       "for deployment: %s") % deployment_uuid)
            verifier.install()

        return verifier

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
    def install_tempest(cls, deployment, source=None):
        """Install Tempest.

        :param deployment: UUID or name of the deployment
        :param source: Source to fetch Tempest from
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid, source=source)
        verifier.install()

    @classmethod
    def uninstall_tempest(cls, deployment):
        """Remove deployment's local Tempest installation.

        :param deployment: UUID or name of the deployment
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid)
        verifier.uninstall()

    @classmethod
    def reinstall_tempest(cls, deployment, tempest_config=None, source=None):
        """Uninstall Tempest and then reinstall from new source.

        :param deployment: UUID or name of the deployment
        :param tempest_config: Tempest config file. Use previous file as
        default
        :param source: Source to fetch Tempest from. Use old source as default
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid)
        if not tempest_config:
            config_path = verifier.config_file
            filename = os.path.basename(config_path)
            temp_location = tempfile.gettempdir()
            tmp_conf_path = os.path.join(temp_location, filename)
            shutil.copy2(config_path, tmp_conf_path)
        source = source or verifier.tempest_source
        verifier.uninstall()
        verifier = tempest.Tempest(deployment_uuid, source=source,
                                   tempest_config=tempest_config)
        verifier.install()
        if not tempest_config:
            shutil.move(tmp_conf_path, verifier.config_file)

    @classmethod
    def configure_tempest(cls, deployment, tempest_config=None,
                          override=False):
        """Generate configuration file of Tempest.

        :param deployment: UUID or name of a deployment
        :param tempest_config: User specified Tempest config file location
        :param override: Whether or not override existing Tempest config file
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = cls._create_verifier(deployment_uuid,
                                        tempest_config=tempest_config)
        verifier.generate_config_file(override)
