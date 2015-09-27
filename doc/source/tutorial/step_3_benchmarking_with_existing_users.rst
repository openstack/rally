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

.. _tutorial_step_3_benchmarking_with_existing_users:

Step 3. Benchmarking OpenStack with existing users
==================================================

.. contents::
   :local:

Motivation
----------

There are two very important reasons from the production world of why it is preferable to use some already existing users to benchmark your OpenStack cloud:

1. *Read-only Keystone Backends:* creating temporary users for benchmark scenarios in Rally is just impossible in case of r/o Keystone backends like *LDAP* and *AD*.

2. *Safety:* Rally can be run from an isolated group of users, and if something goes wrong, this won’t affect the rest of the cloud users.


Registering existing users in Rally
-----------------------------------

The information about existing users in your OpenStack cloud should be passed to Rally at the :ref:`deployment initialization step <tutorial_step_1_setting_up_env_and_running_benchmark_from_samples>`. You have to use the **ExistingCloud** deployment plugin that just provides Rally with credentials of an already existing cloud. The difference from the deployment configuration we've seen previously is that you should set up the *"users"* section with the credentials of already existing users. Let's call this deployment configuration file *existing_users.json*:

.. code-block:: json

    {
        "type": "ExistingCloud",
        "auth_url": "http://example.net:5000/v2.0/",
        "region_name": "RegionOne",
        "endpoint_type": "public",
        "admin": {
            "username": "admin",
            "password": "pa55word",
            "tenant_name": "demo"
        },
        "users": [
            {
                "username": "b1",
                "password": "1234",
                "tenant_name": "testing"
            },
            {
                "username": "b2",
                "password": "1234",
                "tenant_name": "testing"
            }
        ]
    }

This deployment configuration requires some basic information about the OpenStack cloud like the region name, auth url. admin user credentials, and any amount of users already existing in the system. Rally will use their credentials to generate load in against this deployment as soon as we register it as usual:

.. code-block:: console

    $ rally deployment create --file existings_users --name our_cloud
    +--------------------------------------+----------------------------+-----------+------------------+--------+
    | uuid                                 | created_at                 | name      | status           | active |
    +--------------------------------------+----------------------------+-----------+------------------+--------+
    | 1849a9bf-4b18-4fd5-89f0-ddcc56eae4c9 | 2015-03-28 02:43:27.759702 | our_cloud | deploy->finished |        |
    +--------------------------------------+----------------------------+-----------+------------------+--------+
    Using deployment: 1849a9bf-4b18-4fd5-89f0-ddcc56eae4c9
    ~/.rally/openrc was updated


After that, the **rally show** command lists the resources for each user separately:

.. code-block:: console

    $ rally show images

    Images for user `admin` in tenant `admin`:
    +--------------------------------------+---------------------------------+-----------+
    | UUID                                 | Name                            | Size (B)  |
    +--------------------------------------+---------------------------------+-----------+
    | 041cfd70-0e90-4ed6-8c0c-ad9c12a94191 | cirros-0.3.4-x86_64-uec         | 25165824  |
    | 87710f09-3625-4496-9d18-e20e34906b72 | Fedora-x86_64-20-20140618-sda   | 209649664 |
    | b0f269be-4859-48e0-a0ca-03fb80d14602 | cirros-0.3.4-x86_64-uec-ramdisk | 3740163   |
    | d82eaf7a-ff63-4826-9aa7-5fa105610e01 | cirros-0.3.4-x86_64-uec-kernel  | 4979632   |
    +--------------------------------------+---------------------------------+-----------+

    Images for user `b1` in tenant `testing`:
    +--------------------------------------+---------------------------------+-----------+
    | UUID                                 | Name                            | Size (B)  |
    +--------------------------------------+---------------------------------+-----------+
    | 041cfd70-0e90-4ed6-8c0c-ad9c12a94191 | cirros-0.3.4-x86_64-uec         | 25165824  |
    | 87710f09-3625-4496-9d18-e20e34906b72 | Fedora-x86_64-20-20140618-sda   | 209649664 |
    | b0f269be-4859-48e0-a0ca-03fb80d14602 | cirros-0.3.4-x86_64-uec-ramdisk | 3740163   |
    | d82eaf7a-ff63-4826-9aa7-5fa105610e01 | cirros-0.3.4-x86_64-uec-kernel  | 4979632   |
    +--------------------------------------+---------------------------------+-----------+

    Images for user `b2` in tenant `testing`:
    +--------------------------------------+---------------------------------+-----------+
    | UUID                                 | Name                            | Size (B)  |
    +--------------------------------------+---------------------------------+-----------+
    | 041cfd70-0e90-4ed6-8c0c-ad9c12a94191 | cirros-0.3.4-x86_64-uec         | 25165824  |
    | 87710f09-3625-4496-9d18-e20e34906b72 | Fedora-x86_64-20-20140618-sda   | 209649664 |
    | b0f269be-4859-48e0-a0ca-03fb80d14602 | cirros-0.3.4-x86_64-uec-ramdisk | 3740163   |
    | d82eaf7a-ff63-4826-9aa7-5fa105610e01 | cirros-0.3.4-x86_64-uec-kernel  | 4979632   |
    +--------------------------------------+---------------------------------+-----------+

With this new deployment being active, Rally will use the already existing users *"b1"* and *"b2"* instead of creating the temporary ones when launching benchmark task that do not specify the *"users"* context.


Running benchmark scenarios with existing users
-----------------------------------------------

After you have registered a deployment with existing users, don't forget to remove the *"users"* context from your benchmark task configuration if you want to use existing users, like in the following configuration file (*boot-and-delete.json*):


.. code-block:: json

    {
        "NovaServers.boot_and_delete_server": [
            {
                "args": {
                    "flavor": {
                        "name": "m1.tiny"
                    },
                    "image": {
                        "name": "^cirros.*uec$"
                    },
                    "force_delete": false
                },
                "runner": {
                    "type": "constant",
                    "times": 10,
                    "concurrency": 2
                },
                "context": {}
            }
        ]
    }

When you start this task, it will use the existing users *"b1"* and *"b2"* instead of creating the temporary ones:

.. code-block:: bash

    rally task start samples/tasks/scenarios/nova/boot-and-delete.json

It goes without saying that support of benchmarking with predefined users simplifies the usage of Rally for generating loads against production clouds.


(based on: http://boris-42.me/rally-can-generate-load-with-passed-users-now/)
