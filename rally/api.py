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

import jinja2
import jinja2.meta
import jsonschema

from rally.benchmark import engine
from rally.common.i18n import _
from rally.common import log as logging
from rally.common import utils
from rally import consts
from rally import deploy
from rally import exceptions
from rally import objects
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

        deployer = deploy.EngineFactory.get_engine(
            deployment["config"]["type"], deployment)
        try:
            deployer.validate()
        except jsonschema.ValidationError:
            LOG.error(_("Deployment %(uuid)s: Schema validation error.") %
                      {"uuid": deployment["uuid"]})
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
        deployer = deploy.EngineFactory.get_engine(
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
        deployer = deploy.EngineFactory.get_engine(
            deployment["config"]["type"], deployment)
        with deployer:
            deployer.make_cleanup()
            endpoints = deployer.make_deploy()
            deployment.update_endpoints(endpoints)


class Task(object):

    @classmethod
    def render_template(cls, task_template, **kwargs):
        """Render jinja2 task template to Rally input task.

        :param task_template: String that contains template
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

        ast = jinja2.Environment().parse(task_template)
        required_kwargs = jinja2.meta.find_undeclared_variables(ast)

        missing = set(required_kwargs) - set(kwargs) - set(dir(builtins))
        real_missing = [mis for mis in missing
                        if is_really_missing(mis, task_template)]

        if real_missing:
            multi_msg = _("Please specify next template task arguments: %s")
            single_msg = _("Please specify template task argument: %s")

            raise TypeError((len(real_missing) > 1 and multi_msg or single_msg)
                            % ", ".join(real_missing))

        return jinja2.Template(task_template).render(**kwargs)

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
    def validate(cls, deployment, config):
        """Validate a task config against specified deployment.

        :param deployment: UUID or name of the deployment
        :param config: a dict with a task configuration
        """
        deployment = objects.Deployment.get(deployment)
        task = objects.Task(deployment_uuid=deployment["uuid"], fake=True)
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
        LOG.info("Benchmark Task %s on Deployment %s" % (task["uuid"],
                                                         deployment["uuid"]))
        benchmark_engine = engine.BenchmarkEngine(
            config, task, admin=deployment["admin"], users=deployment["users"],
            abort_on_sla_failure=abort_on_sla_failure)

        try:
            benchmark_engine.validate()
            benchmark_engine.run()
        except exceptions.InvalidTaskException:
            # NOTE(boris-42): We don't log anything, because it's a normal
            #                 situation when a user puts a wrong config.
            pass
        except Exception:
            deployment.update_status(consts.DeployStatus.DEPLOY_INCONSISTENT)
            raise

    @classmethod
    def abort(cls, task_uuid):
        """Abort running task."""
        raise NotImplementedError()

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
    def verify(cls, deployment, set_name, regex, tempest_config):
        """Start verifying.

        :param deployment: UUID or name of a deployment.
        :param set_name: Valid name of tempest test set.
        :param regex: Regular expression of test
        :param tempest_config: User specified Tempest config file
        :returns: Verification object
        """

        deployment_uuid = objects.Deployment.get(deployment)["uuid"]

        verification = objects.Verification(deployment_uuid=deployment_uuid)
        verifier = tempest.Tempest(deployment_uuid, verification=verification,
                                   tempest_config=tempest_config)
        if not verifier.is_installed():
            print("Tempest is not installed for specified deployment.")
            print("Installing Tempest for deployment %s" % deploy)
            verifier.install()
        LOG.info("Starting verification of deployment: %s" % deploy)

        verification.set_running()
        verifier.verify(set_name=set_name, regex=regex)

        return verification

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
        """Removes deployment's local Tempest installation

        :param deployment: UUID or name of the deployment
        """
        deployment_uuid = objects.Deployment.get(deployment)["uuid"]
        verifier = tempest.Tempest(deployment_uuid)
        verifier.uninstall()

    @classmethod
    def reinstall_tempest(cls, deployment, tempest_config=None, source=None):
        """Uninstall Tempest and then reinstall from new source

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


# NOTE(msdubov): API methods below are deprecated and left for compability.
#                they're going to be removed in Rally v0.1.0.


@utils.log_deprecated("Use api.Deployment.create() instead of "
                      "api.create_deploy()", rally_version="0.0.2")
def create_deploy(config, name):
    """Create a deployment.

    :param config: a dict with deployment configuration
    :param name: a str represents a name of the deployment
    :returns: Deployment object
    """
    return Deployment.create(config, name)


@utils.log_deprecated("Use api.Deployment.destroy() instead of "
                      "api.destroy_deploy()", rally_version="0.0.2")
def destroy_deploy(deployment):
    """Destroy the deployment.

    :param deployment: UUID or name of the deployment
    """
    Deployment.destroy(deployment)


@utils.log_deprecated("Use api.Deployment.recreate() instead of "
                      "api.recreate_deploy()", rally_version="0.0.2")
def recreate_deploy(deployment):
    """Performs a clean up and then start to deploy.

    :param deployment: UUID or name of the deployment
    """
    Deployment.recreate(deployment)


@utils.log_deprecated("Use api.Task.render_template() instead of "
                      "api.task_template_render()", rally_version="0.0.2")
def task_template_render(task_template, **kwargs):
    """Render jinja2 task template to Rally input task.

    :param task_template: String that contains template
    :param kwargs: Dict with template arguments
    :returns: rendered template str
    """
    return Task.render_template(task_template, **kwargs)


@utils.log_deprecated("Use api.Task.create() instead of "
                      "api.create_task()", rally_version="0.0.2")
def create_task(deployment, tag):
    """Create a task without starting it.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deployment: UUID or name of the deployment
    :param tag: tag for this task
    :returns: Task object
    """
    return Task.create(deployment, tag)


@utils.log_deprecated("Use api.Task.validate() instead of "
                      "api.task_validate()", rally_version="0.0.2")
def task_validate(deployment, config):
    """Validate a task config against specified deployment.

    :param deployment: UUID or name of the deployment
    :param config: a dict with a task configuration
    """
    Task.validate(deployment, config)


@utils.log_deprecated("Use api.Task.start() instead of "
                      "api.start_task()", rally_version="0.0.2")
def start_task(deployment, config, task=None):
    """Start a task.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deployment: UUID or name of the deployment
    :param config: a dict with a task configuration
    :param task: Task object. If None, it will be created
    """
    Task.start(deployment, config, task)


@utils.log_deprecated("Use api.Task.abort() instead of "
                      "api.abort_task()", rally_version="0.0.2")
def abort_task(task_uuid):
    """Abort running task."""
    Task.abort(task_uuid)


@utils.log_deprecated("Use api.Task.delete() instead of "
                      "api.delete_task()", rally_version="0.0.2")
def delete_task(task_uuid, force=False):
    """Delete the task.

    :param task_uuid: The UUID of the task.
    :param force: If set to True, then delete the task despite to the
                  status.
    :raises: :class:`rally.exceptions.TaskInvalidStatus` when the
             status of the task is not FINISHED and the force argument
             if not True
    """
    Task.delete(task_uuid, force)


@utils.log_deprecated("Use api.Verification.verify() instead of "
                      "api.verify()", rally_version="0.0.2")
def verify(deployment, set_name, regex, tempest_config):
    """Start verifying.

    :param deployment: UUID or name of a deployment.
    :param set_name: Valid name of tempest test set.
    :param regex: Regular expression of test
    :param tempest_config: User specified Tempest config file
    :returns: Verification object
    """
    return Verification.verify(deployment, set_name, regex, tempest_config)


@utils.log_deprecated("Use api.Verification.install_tempest() instead of "
                      "api.install_tempest()", rally_version="0.0.2")
def install_tempest(deployment, source):
    """Install Tempest.

    :param deployment: UUID or name of the deployment
    :param source: Source to fetch Tempest from
    """
    Verification.install_tempest(deployment, source)
