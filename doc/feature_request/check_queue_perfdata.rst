====================
Check queue perfdata
====================

Use case
--------

Sometimes OpenStack services use common messaging system very prodigally. For
example Neutron metering agent sending all database table data on new object
creation i.e https://review.openstack.org/#/c/143672/. It cause to Neutron
degradation and other obvious problems. It will be nice to have a way to track
messages count and messages size in queue during tasks.

Problem description
-------------------

Heavy usage of queue isn't checked.

Possible solution
-----------------

* Before running task start process which will connect to queue
  topics and measure messages count, size and other data which we need.
