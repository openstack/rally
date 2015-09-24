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

.. _tutorial_step_8_discovering_more_plugins:

Step 8. Discovering more plugins in Rally
=========================================

.. contents::
   :local:

Plugins in the Rally repository
---------------------------------

Rally currently comes with a great collection of plugins that use the API of
different OpenStack projects like **Keystone**, **Nova**, **Cinder**,
**Glance** and so on. The good news is that you can combine multiple plugins
in one task to test your cloud in a comprehensive way.

First, let's see what plugins are available in Rally.
One of the ways to discover these plugins is just to inspect their
`source code <https://github.com/openstack/rally/tree/master/rally/plugins/>`_.
another is to use build-in rally plugin command.

CLI: rally plugin show
----------------------

Rally plugin CLI command is much more convenient way to learn about different
plugins in Rally. This command allows to list plugins and show detailed
information about them:

.. code-block:: console

    $ rally plugin show create_meter_and_get_stats

    NAME
        CeilometerStats.create_meter_and_get_stats
    NAMESPACE
        default
    MODULE
        rally.plugins.openstack.scenarios.ceilometer.stats
    DESCRIPTION
        Meter is first created and then statistics is fetched for the same
        using GET /v2/meters/(meter_name)/statistics.
    PARAMETERS
    +--------+------------------------------------------------+
    | name   | description                                    |
    +--------+------------------------------------------------+
    | kwargs | contains optional arguments to create a meter |
    |        |                                                |
    +--------+------------------------------------------------+


In case if multiple found benchmarks found command list all matches elements:

.. code-block:: console

    $ rally plugin show NovaKeypair

    Multiple plugins found:
    +-------------------------------------------------+-----------+-------------------------------------------------------+
    | name                                            | namespace | title                                                 |
    +-------------------------------------------------+-----------+-------------------------------------------------------+
    | NovaKeypair.boot_and_delete_server_with_keypair | default   | Boot and delete server with keypair.                  |
    | NovaKeypair.create_and_delete_keypair           | default   | Create a keypair with random name and delete keypair. |
    | NovaKeypair.create_and_list_keypairs            | default   | Create a keypair with random name and list keypairs.  |
    +-------------------------------------------------+-----------+-------------------------------------------------------+


CLI: rally plugin list
----------------------

This command can be used to list filtered by name list of plugins.

.. code-block:: console

    $ rally plugin list --name Keystone

    +--------------------------------------------------+-----------+-----------------------------------------------------------------+
    | name                                             | namespace | title                                                           |
    +--------------------------------------------------+-----------+-----------------------------------------------------------------+
    | Authenticate.keystone                            | default   | Check Keystone Client.                                          |
    | KeystoneBasic.add_and_remove_user_role           | default   | Create a user role add to a user and disassociate.              |
    | KeystoneBasic.create_add_and_list_user_roles     | default   | Create user role, add it and list user roles for given user.    |
    | KeystoneBasic.create_and_delete_ec2credential    | default   | Create and delete keystone ec2-credential.                      |
    | KeystoneBasic.create_and_delete_role             | default   | Create a user role and delete it.                               |
    | KeystoneBasic.create_and_delete_service          | default   | Create and delete service.                                      |
    | KeystoneBasic.create_and_list_ec2credentials     | default   | Create and List all keystone ec2-credentials.                   |
    | KeystoneBasic.create_and_list_services           | default   | Create and list services.                                       |
    | KeystoneBasic.create_and_list_tenants            | default   | Create a keystone tenant with random name and list all tenants. |
    | KeystoneBasic.create_and_list_users              | default   | Create a keystone user with random name and list all users.     |
    | KeystoneBasic.create_delete_user                 | default   | Create a keystone user with random name and then delete it.     |
    | KeystoneBasic.create_tenant                      | default   | Create a keystone tenant with random name.                      |
    | KeystoneBasic.create_tenant_with_users           | default   | Create a keystone tenant and several users belonging to it.     |
    | KeystoneBasic.create_update_and_delete_tenant    | default   | Create, update and delete tenant.                               |
    | KeystoneBasic.create_user                        | default   | Create a keystone user with random name.                        |
    | KeystoneBasic.create_user_set_enabled_and_delete | default   | Create a keystone user, enable or disable it, and delete it.    |
    | KeystoneBasic.create_user_update_password        | default   | Create user and update password for that user.                  |
    | KeystoneBasic.get_entities                       | default   | Get instance of a tenant, user, role and service by id's.       |
    +--------------------------------------------------+-----------+-----------------------------------------------------------------+
