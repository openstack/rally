Rally job related files
=======================

This directory contains rally tasks and plugins that are run by OpenStack CI.

Structure
---------

* plugins - directory where you can add rally plugins. Almost everything in
  Rally is a plugin. Benchmark context, Benchmark scenario, SLA checks, Generic
  cleanup resources, ....

* extra - all files from this directory will be copy pasted to gates, so you
  are able to use absolute paths in rally tasks.
  Files will be located in ~/.rally/extra/*

* rally.yaml is a task that is run in gates against OpenStack (nova network)

* rally-neutron.yaml is a task that is run in gates against OpenStack with
  Neutron Service

* rally-designate.yaml is a task that is run in gates against OpenStack with
  Designate Service. It's experimental job. To trigger make a review with
  "check experimental" text.

* rally-zaqar.yaml is a task that is run in gates against OpenStack with
  Zaqar Service. It's experimental job. To trigger make a review with
  "check experimental" text.


Useful links
------------

* More about Rally: https://rally.readthedocs.org/en/latest/

* How to add rally-gates: https://rally.readthedocs.org/en/latest/gates.html

* About plugins:  https://rally.readthedocs.org/en/latest/plugins.html

* Plugin samples: https://github.com/openstack/rally/tree/master/samples/plugins
