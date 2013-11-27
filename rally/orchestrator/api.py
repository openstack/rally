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


def start_task(config):
    """Start Benchmark task.
        1) Deploy OpenStack Cloud
        2) Verify Deployment
        3) Run Benchmarks
        4) Process benchmark results
        5) Destroy cloud and cleanup
    Returns task uuid
    """
    deploy_conf = config['deploy']
    benchmark_conf = config['tests']

    deployment = objects.Deployment(config=deploy_conf)
    task = objects.Task(deployment_uuid=deployment['uuid'])

    deployer = deploy.EngineFactory.get_engine(deployment['config']['name'],
                                               deployment)
    tester = engine.TestEngine(benchmark_conf, task)
    with deployer:
        endpoint = deployer.make_deploy()
        deployment.update_endpoint(endpoint)
        with tester.bind(endpoint):
            tester.verify()
            tester.benchmark()
        deployer.make_cleanup()
    # TODO(akscram): It's just to follow legacy logic.
    deployment.delete()


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
