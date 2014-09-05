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

from rally.benchmark import engine
from rally import consts
from rally import deploy
from rally import exceptions
from rally import objects
from rally.openstack.common import log as logging
from rally.verification.verifiers.tempest import tempest

LOG = logging.getLogger(__name__)


def create_deploy(config, name):
    """Create a deployment.

    :param config: a dict with deployment configuration
    :param name: a str represents a name of the deployment
    """
    deployment = objects.Deployment(name=name, config=config)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['type'],
                                               deployment)
    with deployer:
        endpoints = deployer.make_deploy()
        deployment.update_endpoints(endpoints)
        return deployment


def destroy_deploy(deploy_uuid):
    """Destroy the deployment.

    :param deploy_uuid: UUID of the deployment
    """
    # TODO(akscram): We have to be sure that there are no running
    #                tasks for this deployment.
    # TODO(akscram): Check that the deployment have got a status that
    #                is equal to "*->finished" or "deploy->inconsistent".
    deployment = objects.Deployment.get(deploy_uuid)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['type'],
                                               deployment)
    with deployer:
        deployer.make_cleanup()
        deployment.delete()

    tempest.Tempest(deploy_uuid).uninstall()


def recreate_deploy(deploy_uuid):
    """Performs a clean up and then start to deploy.

    :param deploy_uuid: UUID of the deployment
    """
    deployment = objects.Deployment.get(deploy_uuid)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['type'],
                                               deployment)
    with deployer:
        deployer.make_cleanup()
        endpoints = deployer.make_deploy()
        deployment.update_endpoints(endpoints)


def create_task(deploy_uuid, tag):
    """Create a task without starting it.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deploy_uuid: UUID of the deployment
    :param tag: tag for this task
    """
    return objects.Task(deployment_uuid=deploy_uuid, tag=tag)


def task_validate(deploy_uuid, config):
    """Validate a task config against specified deployment.

    :param deploy_uuid: UUID of the deployment
    :param config: a dict with a task configuration
    """
    deployment = objects.Deployment.get(deploy_uuid)
    task = objects.Task(deployment_uuid=deploy_uuid)
    benchmark_engine = engine.BenchmarkEngine(config, task)
    benchmark_engine.bind(admin=deployment["admin"],
                          users=deployment["users"])
    benchmark_engine.validate()


def start_task(deploy_uuid, config, task=None):
    """Start a task.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deploy_uuid: UUID of the deployment
    :param config: a dict with a task configuration
    """
    deployment = objects.Deployment.get(deploy_uuid)
    task = task or objects.Task(deployment_uuid=deploy_uuid)
    LOG.info("Benchmark Task %s on Deployment %s" % (task['uuid'],
                                                     deployment['uuid']))
    benchmark_engine = engine.BenchmarkEngine(config, task)
    admin = deployment["admin"]
    users = deployment["users"]

    try:
        benchmark_engine.bind(admin=admin, users=users)
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


def verify(deploy_id, set_name, regex, tempest_config):
    """Start verifying.

    :param deploy_id: a UUID of a deployment.
    :param set_name: Valid name of tempest test set.
    :param regex: Regular expression of test
    :param tempest_config: User specified Tempest config file
    """

    verification = objects.Verification(deployment_uuid=deploy_id)
    verifier = tempest.Tempest(deploy_id, verification=verification,
                               tempest_config=tempest_config)
    if not verifier.is_installed():
        print("Tempest is not installed for specified deployment.")
        print("Installing Tempest for deployment %s" % deploy_id)
        verifier.install()
    LOG.info("Starting verification of deployment: %s" % deploy_id)

    verification.set_running()
    verifier.verify(set_name=set_name, regex=regex)
