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

from rally.benchmark import engine
from rally import consts
from rally import db
from rally import deploy
from rally import objects
from rally.verification.verifiers.tempest import tempest


def create_deploy(config, name):
    """Create a deployment.

    :param config: a dict with deployment configuration
    :param name: a str represents a name of the deployment
    """
    deployment = objects.Deployment(name=name, config=config)
    deployer = deploy.EngineFactory.get_engine(deployment['config']['name'],
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
        endpoints = deployer.make_deploy()
        deployment.update_endpoints(endpoints)


def create_task(deploy_uuid):
    """Create a task without starting it.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deploy_uuid: UUID of the deployment
    """
    return objects.Task(deployment_uuid=deploy_uuid)


def start_task(deploy_uuid, config, task=None):
    """Start a task.

    Task is a list of benchmarks that will be called one by one, results of
    execution will be stored in DB.

    :param deploy_uuid: UUID of the deployment
    :param config: a dict with a task configuration
    """
    deployment = objects.Deployment.get(deploy_uuid)
    task = task or objects.Task(deployment_uuid=deploy_uuid)
    benchmark_engine = engine.BenchmarkEngine(config, task)
    endpoint = deployment['endpoints']
    try:
        with benchmark_engine.bind(endpoint):
            benchmark_engine.run()
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


def verify(deploy_id, image_id, alt_image_id, flavor_id, alt_flavor_id,
           set_name, regex):
    """Start verifying.

    :param deploy_id: a UUID of a deployment.
    :param image_id: Valid primary image reference to be used in tests.
    :param alt_image_id: Valid secondary image reference to be used in tests.
    :param flavor_id: Valid primary flavor to use in tests.
    :param alt_flavor_id: Valid secondary flavor to be used in tests.
    :param set_name: Valid name of tempest test set.
    """
    verifier = tempest.Tempest()
    if not verifier.is_installed():
        print("Tempest is not installed. "
              "Please use 'rally-manage tempest install'")
        return
    print("Starting verification of deployment: %s" % deploy_id)

    endpoints = db.deployment_get(deploy_id)['endpoints']
    endpoint = endpoints[0]
    verifier.verify(image_ref=image_id,
                    image_ref_alt=alt_image_id,
                    flavor_ref=flavor_id,
                    flavor_ref_alt=alt_flavor_id,
                    username=endpoint['username'],
                    password=endpoint['password'],
                    tenant_name=endpoint['tenant_name'],
                    uri=endpoint['auth_url'],
                    uri_v3=re.sub('/v2.0', '/v3', endpoint['auth_url']),
                    set_name=set_name,
                    regex=regex)
