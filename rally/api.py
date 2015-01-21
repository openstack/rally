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


import re

import jinja2
import jinja2.meta
import jsonschema

from rally.benchmark import engine
from rally.common.i18n import _
from rally.common import log as logging
from rally import consts
from rally import deploy
from rally import exceptions
from rally import objects
from rally.verification.tempest import tempest

LOG = logging.getLogger(__name__)


def create_deploy(config, name):
    """Create a deployment.

    :param config: a dict with deployment configuration
    :param name: a str represents a name of the deployment
    """

    try:
        deployment = objects.Deployment(name=name, config=config)
    except exceptions.DeploymentNameExists as e:
        if logging.is_debug():
            LOG.exception(e)
        raise

    deployer = deploy.EngineFactory.get_engine(deployment["config"]["type"],
                                               deployment)
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


def destroy_deploy(deployment):
    """Destroy the deployment.

    :param deployment: UUID or name of the deployment
    """
    # TODO(akscram): We have to be sure that there are no running
    #                tasks for this deployment.
    # TODO(akscram): Check that the deployment have got a status that
    #                is equal to "*->finished" or "deploy->inconsistent".
    deployment = objects.Deployment.get(deployment)
    deployer = deploy.EngineFactory.get_engine(deployment["config"]["type"],
                                               deployment)

    tempest.Tempest(deployment["uuid"]).uninstall()
    with deployer:
        deployer.make_cleanup()
        deployment.delete()


def recreate_deploy(deployment):
    """Performs a clean up and then start to deploy.

    :param deployment: UUID or name of the deployment
    """
    deployment = objects.Deployment.get(deployment)
    deployer = deploy.EngineFactory.get_engine(deployment["config"]["type"],
                                               deployment)
    with deployer:
        deployer.make_cleanup()
        endpoints = deployer.make_deploy()
        deployment.update_endpoints(endpoints)


def task_template_render(task_template, **kwargs):
    """Render jinja2 task template to Rally input task.

    :param task_template: String that contains template
    :param kwargs: Dict with template arguments
    :returns: rendered template str
    """

    # NOTE(boris-42): We have to import __builtin__ to get full list of builtin
    #                 functions (e.g. range()). Unfortunately __builtins__
    #                 doesn't return them (when it is not main module)
    from six.moves import builtins

    ast = jinja2.Environment().parse(task_template)
    required_kwargs = jinja2.meta.find_undeclared_variables(ast)

    missing = set(required_kwargs) - set(kwargs) - set(dir(builtins))
    # NOTE(boris-42): Removing variables that have default values from missing.
    #                 Construction that won't be properly checked is
    #                 {% set x = x or 1}
    real_missing = []
    for mis in missing:
        if not re.search(mis.join(["{%\s*set\s+", "\s*=\s*", "[^\w]+"]),
                         task_template):
            real_missing.append(mis)

    if real_missing:
        multi_msg = _("Please specify next template task arguments: %s")
        single_msg = _("Please specify template task argument: %s")

        raise TypeError((len(real_missing) > 1 and multi_msg or single_msg) %
                        ", ".join(real_missing))

    return jinja2.Template(task_template).render(**kwargs)


def create_task(deployment, tag):
    """Create a task without starting it.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deployment: UUID or name of the deployment
    :param tag: tag for this task
    """

    deployment_uuid = objects.Deployment.get(deployment)["uuid"]
    return objects.Task(deployment_uuid=deployment_uuid, tag=tag)


def task_validate(deployment, config):
    """Validate a task config against specified deployment.

    :param deployment: UUID or name of the deployment
    :param config: a dict with a task configuration
    """
    deployment = objects.Deployment.get(deployment)
    task = objects.Task(deployment_uuid=deployment["uuid"])
    benchmark_engine = engine.BenchmarkEngine(
        config, task, admin=deployment["admin"], users=deployment["users"])
    benchmark_engine.validate()


def start_task(deployment, config, task=None):
    """Start a task.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deployment: UUID or name of the deployment
    :param config: a dict with a task configuration
    """
    deployment = objects.Deployment.get(deployment)
    task = task or objects.Task(deployment_uuid=deployment["uuid"])
    LOG.info("Benchmark Task %s on Deployment %s" % (task["uuid"],
                                                     deployment["uuid"]))
    benchmark_engine = engine.BenchmarkEngine(
        config, task, admin=deployment["admin"], users=deployment["users"])

    try:
        benchmark_engine.validate()
        benchmark_engine.run()
    except exceptions.InvalidTaskException:
        # NOTE(boris-42): We don't log anything, because it's normal situation
        #                 that user put wrong config.
        pass
    except Exception:
        deployment.update_status(consts.DeployStatus.DEPLOY_INCONSISTENT)
        raise


def abort_task(task_uuid):
    """Abort running task."""
    raise NotImplementedError()


def delete_task(task_uuid, force=False):
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


def verify(deployment, set_name, regex, tempest_config):
    """Start verifying.

    :param deployment: UUID or name of a deployment.
    :param set_name: Valid name of tempest test set.
    :param regex: Regular expression of test
    :param tempest_config: User specified Tempest config file
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


def install_tempest(deployment, source):
    """Install tempest."""
    deployment_uuid = objects.Deployment.get(deployment)['uuid']
    verifier = tempest.Tempest(deployment_uuid, source=source)
    verifier.install()
