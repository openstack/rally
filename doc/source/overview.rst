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

.. _overview:

Overview
========

Use Cases
---------

Before diving deep in Rally architecture let's take a look at 3 major high level Rally Use Cases:

.. image:: ./images/Rally-UseCases.png
   :width: 50%
   :align: center


Typical cases where Rally aims to help are:

    1. Automate measuring & profiling focused on how new code changes affect the OS performance;
    2. Using Rally profiler to detect scaling & performance issues;
    3. Investigate how different deployments affect the OS performance:
        * Find the set of suitable OpenStack deployment architectures;
        * Create deployment specifications for different loads (amount of controllers, swift nodes, etc.);
    4. Automate the search for hardware best suited for particular OpenStack cloud;
    5. Automate the production cloud specification generation:
        * Determine terminal loads for basic cloud operations: VM start & stop, Block Device create/destroy & various OpenStack API methods;
        * Check performance of basic cloud operations in case of different loads.


Architecture
------------

Usually OpenStack projects are as-a-Service, so Rally provides this approach and a CLI driven approach that does not require a daemon:

    1. Rally as-a-Service: Run rally as a set of daemons that present Web UI (work in progress) so 1 RaaS could be used by whole team.
    2. Rally as-an-App: Rally as a just lightweight CLI app (without any daemons), that makes it simple to develop & much more portable.


How is this possible? Take a look at diagram below:

.. image:: ./images/Rally_Architecture.png
   :width: 50%
   :align: center

So what is behind Rally?


Rally Components
^^^^^^^^^^^^^^^^

Rally consists of 4 main components:

    1. **Server Providers** - provide servers (virtual servers), with ssh access, in one L3 network.
    2. **Deploy Engines** - deploy OpenStack cloud on servers that are presented by Server Providers
    3. **Verification** - component that runs tempest (or another pecific set of tests) against a deployed cloud, collects results & presents them in human readable form.
    4. **Benchmark engine** - allows to write parameterized benchmark scenarios & run them against the cloud.


But **why** does Rally need these components?
It becomes really clear if we try to imagine: how I will benchmark cloud at Scale, if ...

.. image:: ./images/Rally_QA.png
   :align: center
   :width: 50%



Rally in action
---------------

How amqp_rpc_single_reply_queue affects performance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To show Rally's capabilities and potential we used NovaServers.boot_and_destroy scenario to see how amqp_rpc_single_reply_queue option affects VM bootup time. Some time ago it was `shown <https://docs.google.com/file/d/0B-droFdkDaVhVzhsN3RKRlFLODQ/edit?pli=1>`_ that cloud performance can be boosted by setting it on so naturally we decided to check this result. To make this test we issued requests for booting up and deleting VMs for different number of concurrent users ranging from one to 30 with and without this option set. For each group of users a total number of 200 requests was issued. Averaged time per request is shown below:

.. image:: ./images/Amqp_rpc_single_reply_queue.png
   :width: 50%
   :align: center

So apparently this option affects cloud performance, but not in the way it was thought before.


Performance of Nova instance list command
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Context**: 1 OpenStack user

**Scenario**: 1) boot VM from this user 2) list VM

**Runner**: Repeat 200 times.

As a result, on every next iteration user has more and more VMs and performance of VM list is degrading quite fast:

.. image:: ./images/Rally_VM_list.png
   :width: 50%
   :align: center

Complex scenarios & detailed information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For example NovaServers.snapshot contains a lot of "atomic" actions:

    1. boot VM
    2. snapshot VM
    3. delete VM
    4. boot VM from snapshot
    5. delete VM
    6. delete snapshot

Fortunately Rally collects information about duration of all these operation for every iteration.

As a result we are generating beautiful graph  image:: Rally_snapshot_vm.png

.. image:: ./images/Rally_snapshot_vm.png
   :width: 50%
   :align: center

