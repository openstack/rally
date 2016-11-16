..
      Copyright 2015 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _tutorial_step_7_working_with_multple_openstack_clouds:

Step 7. Working with multiple OpenStack clouds
==============================================

Rally is an awesome tool that allows you to work with multiple clouds and can
itself deploy them. We already know how to work with
:ref:`a single cloud <tutorial_step_1_setting_up_env_and_running_benchmark_from_samples>`.
Let us now register 2 clouds in Rally: the one that we have access to and the
other that we know is registered with wrong credentials.

.. code-block:: console

    $ . openrc admin admin  # openrc with correct credentials
    $ rally deployment create --fromenv --name=cloud-1
    +--------------------------------------+----------------------------+------------+------------------+--------+
    | uuid                                 | created_at                 | name       | status           | active |
    +--------------------------------------+----------------------------+------------+------------------+--------+
    | 4251b491-73b2-422a-aecb-695a94165b5e | 2015-01-18 00:11:14.757203 | cloud-1    | deploy->finished |        |
    +--------------------------------------+----------------------------+------------+------------------+--------+
    Using deployment: 4251b491-73b2-422a-aecb-695a94165b5e
    ~/.rally/openrc was updated
    ...

    $ . bad_openrc admin admin  # openrc with wrong credentials
    $ rally deployment create --fromenv --name=cloud-2
    +--------------------------------------+----------------------------+------------+------------------+--------+
    | uuid                                 | created_at                 | name       | status           | active |
    +--------------------------------------+----------------------------+------------+------------------+--------+
    | 658b9bae-1f9c-4036-9400-9e71e88864fc | 2015-01-18 00:38:26.127171 | cloud-2    | deploy->finished |        |
    +--------------------------------------+----------------------------+------------+------------------+--------+
    Using deployment: 658b9bae-1f9c-4036-9400-9e71e88864fc
    ~/.rally/openrc was updated
    ...

Let us now list the deployments we have created:

.. code-block:: console

    $ rally deployment list
    +--------------------------------------+----------------------------+------------+------------------+--------+
    | uuid                                 | created_at                 | name       | status           | active |
    +--------------------------------------+----------------------------+------------+------------------+--------+
    | 4251b491-73b2-422a-aecb-695a94165b5e | 2015-01-05 00:11:14.757203 | cloud-1    | deploy->finished |        |
    | 658b9bae-1f9c-4036-9400-9e71e88864fc | 2015-01-05 00:40:58.451435 | cloud-2    | deploy->finished | *      |
    +--------------------------------------+----------------------------+------------+------------------+--------+

Note that the second is marked as **"active"** because this is the deployment
we have created most recently. This means that it will be automatically (unless
its UUID or name is passed explicitly via the *--deployment* parameter) used by
the commands that need a deployment, like *rally task start ...* or *rally
deployment check*:

.. code-block:: console

    $ rally deployment check
    Authentication Issues: wrong keystone credentials specified in your endpoint properties. (HTTP 401).

    $ rally deployment check --deployment=cloud-1
    keystone endpoints are valid and following services are available:
    +----------+----------------+-----------+
    | services | type           | status    |
    +----------+----------------+-----------+
    | cinder   | volume         | Available |
    | cinderv2 | volumev2       | Available |
    | ec2      | ec2            | Available |
    | glance   | image          | Available |
    | heat     | orchestration  | Available |
    | heat-cfn | cloudformation | Available |
    | keystone | identity       | Available |
    | nova     | compute        | Available |
    | novav21  | computev21     | Available |
    | s3       | s3             | Available |
    +----------+----------------+-----------+

You can also switch the active deployment using the **rally deployment use**
command:

.. code-block:: console

    $ rally deployment use cloud-1
    Using deployment: 658b9bae-1f9c-4036-9400-9e71e88864fc
    ~/.rally/openrc was updated
    ...

    $ rally deployment check
    keystone endpoints are valid and following services are available:
    +----------+----------------+-----------+
    | services | type           | status    |
    +----------+----------------+-----------+
    | cinder   | volume         | Available |
    | cinderv2 | volumev2       | Available |
    | ec2      | ec2            | Available |
    | glance   | image          | Available |
    | heat     | orchestration  | Available |
    | heat-cfn | cloudformation | Available |
    | keystone | identity       | Available |
    | nova     | compute        | Available |
    | novav21  | computev21     | Available |
    | s3       | s3             | Available |
    +----------+----------------+-----------+

Note the first two lines of the CLI output for the *rally deployment use*
command. They tell you the UUID of the new active deployment and also say that
the *~/.rally/openrc* file was updated -- this is the place where the "active"
UUID is actually stored by Rally.

One last detail about managing different deployments in Rally is that the
*rally task list* command outputs only those tasks that were run against the
currently active deployment, and you have to provide the *--all-deployments*
parameter to list all the tasks:

.. code-block:: console

    $ rally task list
    +--------------------------------------+-----------------+----------------------------+----------------+----------+--------+-----+
    | uuid                                 | deployment_name | created_at                 | duration       | status   | failed | tag |
    +--------------------------------------+-----------------+----------------------------+----------------+----------+--------+-----+
    | c21a6ecb-57b2-43d6-bbbb-d7a827f1b420 | cloud-1         | 2015-01-05 01:00:42.099596 | 0:00:13.419226 | finished | False  |     |
    | f6dad6ab-1a6d-450d-8981-f77062c6ef4f | cloud-1         | 2015-01-05 01:05:57.653253 | 0:00:14.160493 | finished | False  |     |
    +--------------------------------------+-----------------+----------------------------+----------------+----------+--------+-----+
    $ rally task list --all-deployment
    +--------------------------------------+-----------------+----------------------------+----------------+----------+--------+-----+
    | uuid                                 | deployment_name | created_at                 | duration       | status   | failed | tag |
    +--------------------------------------+-----------------+----------------------------+----------------+----------+--------+-----+
    | c21a6ecb-57b2-43d6-bbbb-d7a827f1b420 | cloud-1         | 2015-01-05 01:00:42.099596 | 0:00:13.419226 | finished | False  |     |
    | f6dad6ab-1a6d-450d-8981-f77062c6ef4f | cloud-1         | 2015-01-05 01:05:57.653253 | 0:00:14.160493 | finished | False  |     |
    | 6fd9a19f-5cf8-4f76-ab72-2e34bb1d4996 | cloud-2         | 2015-01-05 01:14:51.428958 | 0:00:15.042265 | finished | False  |     |
    +--------------------------------------+-----------------+----------------------------+----------------+----------+--------+-----+
