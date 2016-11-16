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

.. _tutorial_step_9_deploying_openstack:

Step 9. Deploying OpenStack from Rally
======================================

Along with supporting already existing OpenStack deployments, Rally itself can
**deploy OpenStack automatically** by using one of its *deployment engines*.
Take a look at other `deployment configuration file samples`_. For example,
*devstack-in-existing-servers.json* is a deployment configuration file that
tells Rally to deploy OpenStack with **Devstack** on the existing servers with
given credentials:

.. code-block:: json

    {
        "type": "DevstackEngine",
        "provider": {
            "type": "ExistingServers",
            "credentials": [{"user": "root", "host": "10.2.0.8"}]
        }
    }

You can try to deploy OpenStack in your Virtual Machine using this script. Edit
the configuration file with your IP address/user name and run, as usual:

.. code-block:: console

   $ rally deployment create --file=samples/deployments/for_deploying_openstack_with_rally/devstack-in-existing-servers.json --name=new-devstack
   +---------------------------+----------------------------+--------------+------------------+
   |            uuid           |         created_at         |     name     |      status      |
   +---------------------------+----------------------------+--------------+------------------+
   |     <Deployment UUID>     | 2015-01-10 22:00:28.270941 | new-devstack | deploy->finished |
   +---------------------------+----------------------------+--------------+------------------+
   Using deployment : <Deployment UUID>

.. references:

.. _deployment configuration file samples: https://github.com/openstack/rally/tree/master/samples/deployments
