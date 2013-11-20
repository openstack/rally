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
from rally import objects


def create_deploy(config, name):
    """Create a deployment.

    :param config: a dict with deployment configuration
    :param name: a str represents a name of the deployment
    """
    deployment = objects.Deployment(name=name, config=config)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['name'],
                                               deployment)
    with deployer:
        endpoint = deployer.make_deploy()
        deployment.update_endpoint(endpoint)


def destroy_deploy(deploy_uuid):
    """Destroy the deployment.

    :param deploy_uuid: UUID of the deployment
    """
    # TODO(akscram): We have to be sure that there are no running
    #                tasks for this deployment.
    # TODO(akscram): Check that the deployment have got a status that
    #                is equal to "*->finised" or "deploy->inconsistent".
    deployment = objects.Deployment.get(deploy_uuid)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['name'],
                                               deployment)
    with deployer:
        deployer.make_cleanup()
        deployment.delete()


def recreate_deploy(deploy_uuid):
    """Performs a clean up and then start to deploy.

    :param deploy_uuid: UUID of the deployment
    """
    deployment = objects.Deployment.get(deploy_uuid)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['name'],
                                               deployment)
    with deployer:
        deployer.make_cleanup()
        endpoint = deployer.make_deploy()
        deployment.update_endpoint(endpoint)


def start_task(deploy_uuid, config):
    """Start a task.

    A task is performed in two stages: a verification of a deployment
    and a benchmark.

    :param deploy_uuid: UUID of the deployment
    :param config: a dict with a task configuration
    """
    deployment = objects.Deployment.get(deploy_uuid)
    task = objects.Task(deployment_uuid=deploy_uuid)

    tester = engine.TestEngine(config, task)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['name'],
                                               deployment)
    endpoint = deployment['endpoint']
    with deployer:
        with tester.bind(endpoint):
            # TODO(akscram): The verifications should be a part of
            #                deployment.
            tester.verify()
            tester.benchmark()


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
