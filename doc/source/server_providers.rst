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

.. _server_providers:

Server providers
================

Introduction
------------

Server providers in Rally are typically used by :ref:`deploy engines <deploy_engines>` to manage virtual machines necessary for OpenStack deployment and its following benchmarking. The key feature of server providers is that they provide a **unified interface** for interacting with different **virtualization technologies** (LXS, Virsh etc.) and **cloud suppliers** (like Amazon).

Every server provider should implement the following basic interface:

..

    **constructor**, which should take the **deployment** entity the provider should bind to and a **config** dictionary as its parameters;

..

    **create_servers(image_uuid, type_id, amount)**, which should create the requested number of virtual machines of the given type using a specific image. The method should also return the list of created servers wrapped in special Server entities.

..

    **destroy_servers()**, which should destroy all virtual machines previously created by the same server provider.


Below you will find a short but informative description of server providers implemented in Rally.

Available Server providers
--------------------------

ExistingServers
^^^^^^^^^^^^^^^

**Description**

This provider does nothing, but returns endpoints from configuration. This may be useful if you have specific software/hardware configuration ready to deploy OpenStack.

**Configuration Example**

.. code-block:: none


   {
       "type": "DevstackEngine",
       "provider": {
           "type": "ExistingServers",
           "credentials": [{"user": "root", "host": "10.2.0.8"}]
       }
   }


VirshProvider
^^^^^^^^^^^^^

**Description**

This provider creates virtual machines on host provided by configuration.

**Configuration Examples**

Clone VM from pre-built template using virsh

.. code-block:: none

      {
           "type": "VirshProvider",
           "connection": "user@host.net",
           "template_name": "stack-01-devstack-template",
           "template_user": "ubuntu",
           "template_password": "password"
       }


LxcProvider
^^^^^^^^^^^

**Description**

This provider creates lxc containers on host provided by another provider. Container is attached to the same network as host.

Works well with ubuntu-13.10 hosts.

**Configuration Example**

.. code-block:: none

   {
           "type": "LxcProvider",
           "containers_per_host": 1,
           "distribution": "ubuntu",
           "ipv4_start_address": "192.168.1.43",
           "ipv4_prefixlen": 16,
           "host_provider": {
               "type": "DummyProvider",
               "credentials": [{"user": "root", "host": "192.168.1.42"}]
           }
   }


OpenStackProvider
^^^^^^^^^^^^^^^^^

**Description**

Provides VMs using existing OpenStack cloud.

**Configuration Example**

.. code-block:: none

   {
       "type": "OpenStackProvider",
       "deployment_name": "Rally sample deployment",
       "amount": 3,
       "user": "admin",
       "tenant": "admin",
       "password": "secret",
       "auth_url": "http://example.net:5000/v2.0",
       "flavor_id": 2,
       "image": {
           "checksum": "75846dd06e9fcfd2b184aba7fa2b2a8d",
           "url": "http://example.com/disk1.img",
           "name": "Ubuntu Precise(added by rally)",
           "format": "qcow2",
           "userdata": "#cloud-config\r\n disable_root: false\r\n manage_etc_hosts: true\r\n"
       }
   }


