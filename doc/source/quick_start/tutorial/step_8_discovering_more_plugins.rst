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
-------------------------------

Rally currently comes with a great collection of plugins that use the API of
different OpenStack projects like **Keystone**, **Nova**, **Cinder**,
**Glance** and so on. The good news is that you can combine multiple plugins
in one task to test your cloud in a comprehensive way.

First, let's see what plugins are available in Rally. One of the ways to
discover these plugins is just to inspect their `source code`_.
another is to use build-in rally plugin command.

CLI: rally plugin show
----------------------

Rally plugin CLI command is much more convenient way to learn about different
plugins in Rally. This command allows to list plugins and show detailed
information about them:

.. code-block:: console

    $ rally plugin show create_meter_and_get_stats

    --------------------------------------------------------------------------------
    Create a meter and fetch its statistics.
    --------------------------------------------------------------------------------

    NAME
        CeilometerStats.create_meter_and_get_stats
    PLATFORM
        openstack
    MODULE
        rally.plugins.openstack.scenarios.ceilometer.stats
    DESCRIPTION
        Meter is first created and then statistics is fetched for the same
        using GET /v2/meters/(meter_name)/statistics.
    PARAMETERS
    +--------+-----------------------------------------------+
    | name   | description                                   |
    +--------+-----------------------------------------------+
    | kwargs | contains optional arguments to create a meter |
    +--------+-----------------------------------------------+

In case if multiple plugins were found, all matched elements are listed:

.. code-block:: console

    $ rally plugin show NovaKeypair

    Multiple plugins found:
    +-------------+-------------------------------------------------+-----------+-------------------------------------------------------+
    | Plugin base | Name                                            | Platform  | Title                                                 |
    +-------------+-------------------------------------------------+-----------+-------------------------------------------------------+
    | Scenario    | NovaKeypair.boot_and_delete_server_with_keypair | openstack | Boot and delete server with keypair.                  |
    | Scenario    | NovaKeypair.create_and_delete_keypair           | openstack | Create a keypair with random name and delete keypair. |
    | Scenario    | NovaKeypair.create_and_get_keypair              | openstack | Create a keypair and get the keypair details.         |
    | Scenario    | NovaKeypair.create_and_list_keypairs            | openstack | Create a keypair with random name and list keypairs.  |
    +-------------+-------------------------------------------------+-----------+-------------------------------------------------------+

CLI: rally plugin list
----------------------

This command can be used to list filtered by name list of plugins.

.. code-block:: console

    $ rally plugin list --name Keystone

    +-------------+----------------------------------------------------+-----------+-----------------------------------------------------------------+
    | Plugin base | Name                                               | Platform  | Title                                                           |
    +-------------+----------------------------------------------------+-----------+-----------------------------------------------------------------+
    | OSClient    | keystone                                           | openstack | Wrapper for KeystoneClient which hides OpenStack auth details.  |
    | Scenario    | Authenticate.keystone                              | openstack | Check Keystone Client.                                          |
    | Scenario    | KeystoneBasic.add_and_remove_user_role             | openstack | Create a user role add to a user and disassociate.              |
    | Scenario    | KeystoneBasic.authenticate_user_and_validate_token | openstack | Authenticate and validate a keystone token.                     |
    | Scenario    | KeystoneBasic.create_add_and_list_user_roles       | openstack | Create user role, add it and list user roles for given user.    |
    | Scenario    | KeystoneBasic.create_and_delete_ec2credential      | openstack | Create and delete keystone ec2-credential.                      |
    | Scenario    | KeystoneBasic.create_and_delete_role               | openstack | Create a user role and delete it.                               |
    | Scenario    | KeystoneBasic.create_and_delete_service            | openstack | Create and delete service.                                      |
    | Scenario    | KeystoneBasic.create_and_get_role                  | openstack | Create a user role and get it detailed information.             |
    | Scenario    | KeystoneBasic.create_and_list_ec2credentials       | openstack | Create and List all keystone ec2-credentials.                   |
    | Scenario    | KeystoneBasic.create_and_list_roles                | openstack | Create a role, then list all roles.                             |
    | Scenario    | KeystoneBasic.create_and_list_services             | openstack | Create and list services.                                       |
    | Scenario    | KeystoneBasic.create_and_list_tenants              | openstack | Create a keystone tenant with random name and list all tenants. |
    | Scenario    | KeystoneBasic.create_and_list_users                | openstack | Create a keystone user with random name and list all users.     |
    | Scenario    | KeystoneBasic.create_and_update_user               | openstack | Create user and update the user.                                |
    | Scenario    | KeystoneBasic.create_delete_user                   | openstack | Create a keystone user with random name and then delete it.     |
    | Scenario    | KeystoneBasic.create_tenant                        | openstack | Create a keystone tenant with random name.                      |
    | Scenario    | KeystoneBasic.create_tenant_with_users             | openstack | Create a keystone tenant and several users belonging to it.     |
    | Scenario    | KeystoneBasic.create_update_and_delete_tenant      | openstack | Create, update and delete tenant.                               |
    | Scenario    | KeystoneBasic.create_user                          | openstack | Create a keystone user with random name.                        |
    | Scenario    | KeystoneBasic.create_user_set_enabled_and_delete   | openstack | Create a keystone user, enable or disable it, and delete it.    |
    | Scenario    | KeystoneBasic.create_user_update_password          | openstack | Create user and update password for that user.                  |
    | Scenario    | KeystoneBasic.get_entities                         | openstack | Get instance of a tenant, user, role and service by id's.       |
    +-------------+----------------------------------------------------+-----------+-----------------------------------------------------------------+
.. references:

.. _source code: https://github.com/openstack/rally/tree/master/rally/plugins/
