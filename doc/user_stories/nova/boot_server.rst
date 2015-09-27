==========================================================================================
Finding a Keystone bug while benchmarking 20 node HA cloud performance at creating 400 VMs
==========================================================================================

*(Contributed by Alexander Maretskiy, Mirantis)*

Below we describe how we found a `bug in keystone <https://bugs.launchpad.net/keystone/+bug/1360446>`_ and achieved 2x average performance increase at booting Nova servers after fixing that bug. Our initial goal was to benchmark the booting of a significant amount of servers on a cluster (running on a custom build of `Mirantis OpenStack <https://software.mirantis.com/>`_ v5.1) and to ensure that this operation has reasonable performance and completes with no errors.

Goal
----

- Get data on how a cluster behaves when a huge amount of servers is started
- Get data on how good the neutron component is good in this case

Summary
-------

- Creating 400 servers with configured networking
- Servers are being created simultaneously - 5 servers at the same time

Hardware
--------

Having a real hardware lab with 20 nodes:

+--------+-------------------------------------------------------+
| Vendor | SUPERMICRO SUPERSERVER                                |
+--------+-------------------------------------------------------+
| CPU    |  12 cores, Intel(R) Xeon(R) CPU E5-2620 v2 @ 2.10GHz  |
+--------+-------------------------------------------------------+
| RAM    | 32GB (4 x Samsung DDRIII 8GB)                         |
+--------+-------------------------------------------------------+
| HDD    | 1TB                                                   |
+--------+-------------------------------------------------------+

Cluster
-------

This cluster was created via Fuel Dashboard interface.

+----------------------+-----------------------------------------------------------------------------+
| Deployment           | Custom build of `Mirantis OpenStack <https://software.mirantis.com/>`_ v5.1 |
+----------------------+-----------------------------------------------------------------------------+
| OpenStack release    | Icehouse                                                                    |
+----------------------+-----------------------------------------------------------------------------+
| Operating System     | Ubuntu 12.04.4                                                              |
+----------------------+-----------------------------------------------------------------------------+
| Mode                 | High availability                                                           |
+----------------------+-----------------------------------------------------------------------------+
| Hypervisor           | KVM                                                                         |
+----------------------+-----------------------------------------------------------------------------+
| Networking           | Neutron with GRE segmentation                                               |
+----------------------+-----------------------------------------------------------------------------+
| Controller nodes     | 3                                                                           |
+----------------------+-----------------------------------------------------------------------------+
| Compute nodes        | 17                                                                          |
+----------------------+-----------------------------------------------------------------------------+

Rally
-----

**Version**

For this benchmark, we use custom rally with the following patch:

https://review.openstack.org/#/c/96300/

**Deployment**

Rally was deployed for cluster using `ExistingCloud <https://github.com/openstack/rally/blob/master/samples/deployments/existing.json>`_ type of deployment.

**Server flavor**

.. code-block:: console

 $ nova flavor-show ram64
 +----------------------------+--------------------------------------+
 | Property                   | Value                                |
 +----------------------------+--------------------------------------+
 | OS-FLV-DISABLED:disabled   | False                                |
 | OS-FLV-EXT-DATA:ephemeral  | 0                                    |
 | disk                       | 0                                    |
 | extra_specs                | {}                                   |
 | id                         | 2e46aba0-9e7f-4572-8b0a-b12cfe7e06a1 |
 | name                       | ram64                                |
 | os-flavor-access:is_public | True                                 |
 | ram                        | 64                                   |
 | rxtx_factor                | 1.0                                  |
 | swap                       |                                      |
 | vcpus                      | 1                                    |
 +----------------------------+--------------------------------------+

**Server image**

.. code-block:: console

 $ nova image-show TestVM
 +----------------------------+-------------------------------------------------+
 | Property                   | Value                                           |
 +----------------------------+-------------------------------------------------+
 | OS-EXT-IMG-SIZE:size       | 13167616                                        |
 | created                    | 2014-08-21T11:18:49Z                            |
 | id                         | 7a0d90cb-4372-40ef-b711-8f63b0ea9678            |
 | metadata murano_image_info | {"title": "Murano Demo", "type": "cirros.demo"} |
 | minDisk                    | 0                                               |
 | minRam                     | 64                                              |
 | name                       | TestVM                                          |
 | progress                   | 100                                             |
 | status                     | ACTIVE                                          |
 | updated                    | 2014-08-21T11:18:50Z                            |
 +----------------------------+-------------------------------------------------+


**Task configuration file (in JSON format):**

.. code-block:: json

 {
    "NovaServers.boot_server": [
        {
            "args": {
                "flavor": {
                    "name": "ram64"
                },
                "image": {
                    "name": "TestVM"
                }
            },
            "runner": {
                "type": "constant",
                "concurrency": 5,
                "times": 400
            },
            "context": {
                "neutron_network": {
                    "network_ip_version": 4
                },
                "users": {
                    "concurrent": 30,
                    "users_per_tenant": 5,
                    "tenants": 5
                },
                "quotas": {
                    "neutron": {
                        "subnet": -1,
                        "port": -1,
                        "network": -1,
                        "router": -1
                    }
                }
            }
        }
    ]
 }

The only difference between first and second run is that runner.times for first time was set to 500

Results
-------

**First time - a bug was found:**

Starting from 142 server, we have error from novaclient: Error <class 'novaclient.exceptions.Unauthorized'>: Unauthorized (HTTP 401).

That is how a `bug in keystone <https://bugs.launchpad.net/keystone/+bug/1360446>`_ was found.

+------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+
| action           | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |
+------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+
| nova.boot_server | 6.507     | 17.402    | 100.303   | 39.222        | 50.134        | 26.8%   | 500   |
| total            | 6.507     | 17.402    | 100.303   | 39.222        | 50.134        | 26.8%   | 500   |
+------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+

**Second run, with bugfix:**

After a patch was applied (using RPC instead of neutron client in metadata agent), we got **100% success and 2x improved average perfomance**:

+------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+
| action           | min (sec) | avg (sec) | max (sec) | 90 percentile | 95 percentile | success | count |
+------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+
| nova.boot_server | 5.031     | 8.008     | 14.093    | 9.616         | 9.716         | 100.0%  | 400   |
| total            | 5.031     | 8.008     | 14.093    | 9.616         | 9.716         | 100.0%  | 400   |
+------------------+-----------+-----------+-----------+---------------+---------------+---------+-------+
