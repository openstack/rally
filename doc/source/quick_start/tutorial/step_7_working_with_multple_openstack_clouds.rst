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

This step shows the OpenStack side of it. Environments themselves are
described in :ref:`env-component`.

.. code-block:: console

    $ . openrc admin admin  # openrc with correct credentials
    $ rally env create --name=cloud-1 --from-sysenv
    Your system environment includes specifications of 1 platform(s).
    Discovery information:
         - existing@openstack : Available.
    Using environment: 4251b491-73b2-422a-aecb-695a94165b5e
    ...

    $ . bad_openrc admin admin  # openrc with wrong credentials
    $ rally env create --name=cloud-2 --from-sysenv
    Your system environment includes specifications of 1 platform(s).
    Discovery information:
         - existing@openstack : Available.
    Using environment: 658b9bae-1f9c-4036-9400-9e71e88864fc
    ...

Note that *env create* does not talk to the cloud, so the second environment
is created just fine despite the wrong credentials. It is *env check* below
that tells the two apart.

Let us now list the environments we have created:

.. code-block:: console

    $ rally env list
    +--------------------------------------+---------+--------+----------------------------+-------------+---------+
    | uuid                                 | name    | status | created_at                 | description | default |
    +--------------------------------------+---------+--------+----------------------------+-------------+---------+
    | 658b9bae-1f9c-4036-9400-9e71e88864fc | cloud-2 | READY  | 2025-01-05T00:40:58.451435 |             | *       |
    | 4251b491-73b2-422a-aecb-695a94165b5e | cloud-1 | READY  | 2025-01-05T00:11:14.757203 |             |         |
    +--------------------------------------+---------+--------+----------------------------+-------------+---------+

The second one is marked as **"default"**, because we created it last. Every
command that needs an environment will use it, unless you pass *--env*:

.. code-block:: console

    $ rally env check
    Env `cloud-2 (658b9bae-1f9c-4036-9400-9e71e88864fc)' :-(
    +-----------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------+
    | Available | Platform  | Message                                                                                                                                       |
    +-----------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------+
    | :-(       | openstack | Failed to authenticate to http://example.net:5000/v3/ for user 'admin' in project 'admin': The request you have made requires authentication. |
    +-----------+-----------+-----------------------------------------------------------------------------------------------------------------------------------------------+

    $ rally env check --env=cloud-1
    Env `cloud-1 (4251b491-73b2-422a-aecb-695a94165b5e)' :-)
    +-----------+-----------+---------+
    | Available | Platform  | Message |
    +-----------+-----------+---------+
    | :-)       | openstack | OK!     |
    +-----------+-----------+---------+

You can also switch the default environment using the **rally env use**
command:

.. code-block:: console

    $ rally env use cloud-1
    Using environment: 4251b491-73b2-422a-aecb-695a94165b5e

    $ rally env check
    Env `cloud-1 (4251b491-73b2-422a-aecb-695a94165b5e)' :-)
    +-----------+-----------+---------+
    | Available | Platform  | Message |
    +-----------+-----------+---------+
    | :-)       | openstack | OK!     |
    +-----------+-----------+---------+

Keep in mind that *rally task list* shows only the tasks of the current
default environment. See :ref:`env-component` for that and for the rest of
the environment commands.
