Rally Deployments
=================

Before starting cluster benchmarking, its connection parameters
should be saved in Rally database (deployment record).

If there is no cluster, rally also can create it.

There are examples of deployment configurations:

existing.json
-------------

Register existing OpenStack cluster.

existing-keystone-v3.json
-------------------------

Register existing OpenStack cluster that uses Keystone v3.

existing-with-given-endpoint.json
---------------------------------

Register existing OpenStack cluster, with parameter "endpoint" specified
to explicitly set keystone management_url. Use this parameter if
keystone fails to setup management_url correctly.
For example, this parameter must be specified for FUEL cluster
and has value "http://<identity-public-url-ip>:35357/v2.0/"

devstack-in-existing-servers.json
---------------------------------

Register existing DevStack cluster.

devstack-in-lxc.json
--------------------

Deploy DevStack cluster on LXC and register it by Rally.

devstack-in-openstack.json
--------------------------

Deploy DevStack cluster on OpenStack and register it by Rally.

devstack-lxc-engine-in-existing-servers.json
--------------------------------------------

See *devstack-lxc-engine-in-existing-servers.rst* for details

fuel-ha.json
------------

Deploy High Availability FUEL cluster and register it by Rally.

fuel-multinode.json
-------------------

Deploy Multinode FUEL cluster and register it by Rally.
