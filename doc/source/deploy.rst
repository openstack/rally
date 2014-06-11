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

.. _deploy:

Deploy
======

Deployment engines
==================

One of the core entities in Rally architecture are the **Deploy engines**. The main task of a deploy engine is to control the process of **deploying some OpenStack distribution** like *DevStack* or *FUEL* before any benchmarking procedures take place. Every deploy engine should implement the following fairly simple interface:

* **constuctor**, which takes a **deployment** entity as its only parameter;
* **deploy()**, which should deploy the appropriate OpenStack distribution given the cloud config from the deployment object the engine was initialized with (possibly using one of available **server providers**). The method should also return a dictionary with endpoints of the deployed OpenStack distribution;
* **cleanup()**, which should clean up the OpenStack deployment (again, possibly using one of available **server providers**).



Server Providers
================

**Server providers** in Rally are typically used by **deploy engines** to manage virtual machines necessary for OpenStack deployment and its following benchmarking. The key feature of server providers is that they provide a **unified interface** for interacting with different **virtualization technologies** (*LXS*, *Virsh* etc.) and **cloud suppliers** (like *Amazon*).

Every server provider should implement the following basic interface:

* **constructor**, which should take the **deployment** entity the provider should bind to and a **config** dictionary as its parameters;
* **create_servers(image_uuid, type_id, amount)**, which should create the requested number of virtual machines of the given type using a specific image. The method should also return the list of created servers wrapped in special *Server* entities.
* **destroy_servers()**, which should destroy all virtual machines previously created by the same server provider.
