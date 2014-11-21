..
      Copyright 2014 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _usage:

Usage
=====

Usage demo
----------

**NOTE**: Throughout this demo, we assume that you have a configured :ref:`Rally installation <installation>` and an already existing OpenStack deployment has keystone available at <KEYSTONE_AUTH_URL>.


Step 1. Deployment initialization (use existing cloud)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, you have to provide Rally with an Openstack deployment it is going to benchmark. This is done through deployment **configuration files**. The actual deployment can be either created by Rally (see /doc/samples for configuration examples) or, as in our example, an already existing one. The configuration file (let's call it **existing.json**) should contain the deployment strategy (in our case, the deployment will be performed by the so called **"ExistingCloud"**, since the deployment is ready to use) and some specific parameters (for the ExistingCloud, an endpoint with administrator permissions):

.. code-block:: none

   {
       "type": "ExistingCloud",
       "endpoint": {
           "auth_url": <KEYSTONE_AUTH_URL>,
           "username": <ADMIN_USER_NAME>,
           "password": <ADMIN_PASSWORD>,
           "tenant_name": <ADMIN_TENANT>
       }
   }


To register this deployment in Rally, use the **deployment create** command:

.. code-block:: none

   $ rally deployment create --filename=existing.json --name=existing
   +---------------------------+----------------------------+----------+------------------+
   |            uuid           |         created_at         |   name   |      status      |
   +---------------------------+----------------------------+----------+------------------+
   |     <Deployment UUID>     | 2014-02-15 22:00:28.270941 | existing | deploy->finished |
   +---------------------------+----------------------------+----------+------------------+
   Using deployment : <Deployment UUID>


Note the last line in the output. It says that the just created deployment is now used by Rally; that means that all the benchmarking operations from now on are going to be performed on this deployment. In case you want to switch to another deployment, execute the **use deployment** command:

.. code-block:: none

   $ rally use deployment <Another deployment name or UUID>
   Using deployment : <Another deployment name or UUID>


Finally, the **deployment check** command enables you to verify that your current deployment is healthy and ready to be benchmarked:

.. code-block:: none

   $ rally deployment check
   +----------+-----------+-----------+
   | services |    type   |   status  |
   +----------+-----------+-----------+
   |   nova   |  compute  | Available |
   | cinderv2 |  volumev2 | Available |
   |  novav3  | computev3 | Available |
   |    s3    |     s3    | Available |
   |  glance  |   image   | Available |
   |  cinder  |   volume  | Available |
   |   ec2    |    ec2    | Available |
   | keystone |  identity | Available |
   +----------+-----------+-----------+

Step 2. Benchmarking
^^^^^^^^^^^^^^^^^^^^

Now that we have a working and registered deployment, we can start benchmarking it. Again, the sequence of benchmark scenarios to be launched by Rally should be specified in a **benchmark task configuration file**. Note that there is already a set of nice benchmark tasks examples in *doc/samples/tasks/* (assuming that you are in the Rally root directory). The natural thing would be just to try one of these sample benchmark tasks, say, the one that boots and deletes multiple servers (*doc/samples/tasks/nova/boot-and-delete.json*). To start a benchmark task, run the task start command:

.. code-block:: none

   ubuntu@tempeste-test:~$ rally -v task start rally/doc/samples/tasks/nova/boot-and-delete.json
   =============================================================================================
   Task  392c803b-37fd-4915-9732-3523f4252e9b is started
   --------------------------------------------------------------------------------
   2014-03-20 06:17:39.994 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Starting:  Check cloud.
   2014-03-20 06:17:40.123 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Completed: Check cloud.
   2014-03-20 06:17:40.123 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Starting:  Task validation.
   2014-03-20 06:17:40.133 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Starting:  Task validation of scenarios names.
   2014-03-20 06:17:40.137 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Completed: Task validation of scenarios names.
   2014-03-20 06:17:40.138 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Starting:  Task validation of syntax.
   2014-03-20 06:17:40.140 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Completed: Task validation of syntax.
   2014-03-20 06:17:40.140 27502 INFO rally.benchmark.engine [-] Task 392c803b-37fd-4915-9732-3523f4252e9b | Starting:  Task validation of semantic.
   2014-03-20 06:17:41.098 27502 ERROR glanceclient.common.http [-] Request returned failure status.

   ================================================================================
   Task 392c803b-37fd-4915-9732-3523f4252e9b is failed.
   --------------------------------------------------------------------------------
   <class 'rally.exceptions.InvalidBenchmarkConfig'>
   Task config is invalid.
       Benchmark NovaServers.boot_and_delete_server has wrong configuration of args at position 0: {'image_id': '73257560-c59b-4275-a1ec-ab140e5b9979', 'flavor_id': 1}
       Reason: Image with id '73257560-c59b-4275-a1ec-ab140e5b9979' not found

   For more details run:
   rally -vd task detailed 392c803b-37fd-4915-9732-3523f4252e9b

This attempt, however, will most likely fail because of an **input arguments validation error** (due to a non-existing image name). The thing is that the benchmark scenario that boots a server needs to do that using a concrete image available in the OpenStack deployment. In prior iterations of Rally, the images were denoted by UUID (such as "flavor_id", "image_id", etc). Now, these resources are simply denoted by name.

To get started, make a local copy of the sample benchmark task:

.. code-block:: none

   cp doc/samples/tasks/nova/boot-and-delete.json my-task.json


and then edit it with the resource names from your OpenStack installation:

.. code-block:: none

   {
       "NovaServers.boot_and_delete_server": [
           {
               "args": {
                   "flavor": {
                     "name": "m1.tiny"
                   },
                   "image": {
                       "name": "CirrOS 0.3.1 (x86_64)"
                    }
               },
               "runner": {
                   "type": "constant",
                   "times": 10,
                   "concurrency": 2
               },
               "context": {
                   "users": {
                       "tenants": 3,
                       "users_per_tenant": 2
                   }
               }
           }
       ]
   }


To obtain proper image name and flavor name, you can use the subcommand show of rally.

let's get a proper image name:

.. code-block:: none

   $ rally show images
   +--------------------------------------+-----------------------+-----------+
   |                 UUID                 |          Name         |  Size (B) |
   +--------------------------------------+-----------------------+-----------+
   | 8dfd6098-0c26-4cb5-8e77-1ecb2db0b8ae |  CentOS 6.5 (x86_64)  | 344457216 |
   | 2b8d119e-9461-48fc-885b-1477abe2edc5 | CirrOS 0.3.1 (x86_64) |  13147648 |
   +--------------------------------------+-----------------------+-----------+


and a proper flavor name:

.. code-block:: none

   $ rally show flavors
   +---------------------+-----------+-------+----------+-----------+-----------+
   | ID                  |    Name   | vCPUs | RAM (MB) | Swap (MB) | Disk (GB) |
   +---------------------+-----------+-------+----------+-----------+-----------+
   | 1                   |  m1.tiny  |   1   |   512    |           |     1     |
   | 2                   |  m1.small |   1   |   2048   |           |     20    |
   | 3                   | m1.medium |   2   |   4096   |           |     40    |
   | 4                   |  m1.large |   4   |   8192   |           |     80    |
   | 5                   | m1.xlarge |   8   |  16384   |           |    160    |
   +---------------------+-----------+-------+----------+-----------+-----------+


After you've edited the **my-task.json** file, you can run this benchmark task again. This time, let's also use the --verbose parameter that will allow us to retrieve more logging from Rally while it performs benchmarking:

.. code-block:: none

   $ rally -v task start my-task.json --tag my_task

   ================================================================================
   Task my_task 87eb8ff3-07f9-4941-b1be-63e707aceb1e is started
   --------------------------------------------------------------------------------
   2014-03-20 06:26:36.431 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Check cloud.
   2014-03-20 06:26:36.555 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Check cloud.
   2014-03-20 06:26:36.555 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Task validation.
   2014-03-20 06:26:36.564 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Task validation of scenarios names.
   2014-03-20 06:26:36.568 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Task validation of scenarios names.
   2014-03-20 06:26:36.568 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Task validation of syntax.
   2014-03-20 06:26:36.571 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Task validation of syntax.
   2014-03-20 06:26:36.571 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Task validation of semantic.
   2014-03-20 06:26:37.316 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Task validation of semantic.
   2014-03-20 06:26:37.316 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Task validation.
   2014-03-20 06:26:37.316 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Benchmarking.
   2014-03-20 06:26:41.596 27820 INFO rally.benchmark.runners.base [-] ITER: 0 START
   2014-03-20 06:26:41.596 27821 INFO rally.benchmark.runners.base [-] ITER: 1 START
   2014-03-20 06:26:46.105 27820 INFO rally.benchmark.runners.base [-] ITER: 0 END: Error <class 'rally.exceptions.GetResourceNotFound'>: Resource not found: `404`
   2014-03-20 06:26:46.105 27820 INFO rally.benchmark.runners.base [-] ITER: 2 START
   2014-03-20 06:26:46.451 27821 INFO rally.benchmark.runners.base [-] ITER: 1 END: Error <type 'exceptions.AttributeError'>: status
   2014-03-20 06:26:46.452 27821 INFO rally.benchmark.runners.base [-] ITER: 3 START
   2014-03-20 06:26:46.497 27820 INFO rally.benchmark.runners.base [-] ITER: 2 END: Error <class 'novaclient.exceptions.NotFound'>: Instance could not be found (HTTP 404) (Request-ID: req-dfd372e9-728d-49ca-87e1-54cbf593b2be)
   2014-03-20 06:26:46.497 27820 INFO rally.benchmark.runners.base [-] ITER: 4 START
   2014-03-20 06:26:53.274 27821 INFO rally.benchmark.runners.base [-] ITER: 3 END: OK
   2014-03-20 06:26:53.275 27821 INFO rally.benchmark.runners.base [-] ITER: 5 START
   2014-03-20 06:26:53.709 27820 INFO rally.benchmark.runners.base [-] ITER: 4 END: OK
   2014-03-20 06:26:53.710 27820 INFO rally.benchmark.runners.base [-] ITER: 6 START
   2014-03-20 06:26:59.942 27821 INFO rally.benchmark.runners.base [-] ITER: 5 END: OK
   2014-03-20 06:26:59.943 27821 INFO rally.benchmark.runners.base [-] ITER: 7 START
   2014-03-20 06:27:00.601 27820 INFO rally.benchmark.runners.base [-] ITER: 6 END: OK
   2014-03-20 06:27:00.601 27820 INFO rally.benchmark.runners.base [-] ITER: 8 START
   2014-03-20 06:27:06.635 27821 INFO rally.benchmark.runners.base [-] ITER: 7 END: OK
   2014-03-20 06:27:06.635 27821 INFO rally.benchmark.runners.base [-] ITER: 9 START
   2014-03-20 06:27:07.414 27820 INFO rally.benchmark.runners.base [-] ITER: 8 END: OK
   2014-03-20 06:27:13.311 27821 INFO rally.benchmark.runners.base [-] ITER: 9 END: OK
   2014-03-20 06:27:14.302 27812 WARNING rally.benchmark.context.secgroup [-] Unable to delete secgroup: 43
   2014-03-20 06:27:14.336 27812 WARNING rally.benchmark.context.secgroup [-] Unable to delete secgroup: 45
   2014-03-20 06:27:14.336 27812 INFO rally.benchmark.context.cleaner [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Cleanup users resources.
   2014-03-20 06:27:25.498 27812 INFO rally.benchmark.context.cleaner [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Cleanup users resources.
   2014-03-20 06:27:25.498 27812 INFO rally.benchmark.context.cleaner [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Starting:  Cleanup admin resources.
   2014-03-20 06:27:25.689 27812 INFO rally.benchmark.context.cleaner [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Cleanup admin resources.
   2014-03-20 06:27:26.092 27812 INFO rally.benchmark.engine [-] Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e | Completed: Benchmarking.

   ================================================================================
   Task 87eb8ff3-07f9-4941-b1be-63e707aceb1e is finished.
   --------------------------------------------------------------------------------

   test scenario NovaServers.boot_and_delete_server
   args position 0
   args values:
   {u'args': {u'flavor_id': 1,
              u'image_id': u'976dfd41-d8d5-4688-a8c1-8f196316d8b9'},
    u'context': {u'users': {u'tenants': 3, u'users_per_tenant': 2}},
    u'runner': {u'concurrency': 2, u'times': 10, u'type': u'continuous'}}
   +---------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+
   | action              | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |
   +---------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+
   | nova.boot_server    | 0.480     | 0.501     | 0.521     | 0.521         | 0.521         | 100.0%  | 10    |
   | nova.delete_server  | 0.185     | 0.189     | 0.195     | 0.194         | 0.194         | 70.0%   | 10    |
   | total               | 0.666     | 0.690     | 0.715     | 0.715         | 0.715         | 70.0%   | 10    |
   +---------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+

   HINTS:
   * To plot HTML graphics with this data, run:
       rally task plot2html 87eb8ff3-07f9-4941-b1be-63e707aceb1e --out output.html

   * To get raw JSON output of task results, run:
       rally task results 87eb8ff3-07f9-4941-b1be-63e707aceb1e

Available Rally facilities
--------------------------

To be able to run complex benchmark scenarios on somewhat more sophisticated OpenStack deployment types, you should familiarize yourself with more **deploy engines, server providers** and **benchmark scenarios** available in Rally.

..

List of available Deploy engines (including their description and usage examples):  :ref:`Deploy engines <deploy_engines>`

..

List of available Server providers (including their description and usage examples):  :ref:`Server providers <server_providers>`

You can also learn about different Rally entities without leaving the Command Line Interface. There is a special **search engine** embedded into Rally, which, for a given *search query*, prints documentation for the corresponding benchmark scenario/deploy engine/... as fetched from the source code. This is accomplished by the **rally info find** command:

.. code-block: none

    $ rally info find *create_meter_and_get_stats*

    CeilometerStats.create_meter_and_get_stats (benchmark scenario).

    Test creating a meter and fetching its statistics.

    Meter is first created and then statistics is fetched for the same
    using GET /v2/meters/(meter_name)/statistics.

    Parameters:
        - name_length: length of generated (random) part of meter name
        - kwargs: contains optional arguments to create a meter

    $ rally info find *Authenticate*

    Authenticate (benchmark scenario group).

    This class should contain authentication mechanism.

    For different types of clients like Keystone.

    $ rally info find *some_non_existing_benchmark*

    Failed to find any docs for query: 'some_non_existing_benchmark'
