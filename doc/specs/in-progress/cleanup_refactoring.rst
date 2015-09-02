..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Refactoring Rally Cleanup
=========================

Current generic mechanism is nice but it doesn't work enough well in real life.
And in cases of existing users, persistence context and disaster cleanups it
doesn't work well.
This proposal should be useful for covering following use cases.


Problem description
===================

There are 5 use cases that require cleanup refactoring:

#. Benchmarking with existing tenants.

   Keep existing resources instead of deleting all resources in the tenants.

#. Persistence benchmark context.

   Create benchmark environment once before benchmarking. After that run some
   amount of benchmarks that are using it and at the end just delete all
   created resources by context cleanups.

#. Disaster cleanup.

   Delete all resources created by Rally in such case if something went wrong
   with server that is running Rally.

#. Isolated task

   It is quite important to add ability to run few instances of Rally against
   cloud simultanesouly (and one cleanup, won't affect the others)

#. Testing that cleanups works

   How to ensure that Rally cleaned all resources.


Proposed change
===============

Use consistent resource names as described in
https://review.openstack.org/201545

* Resources created by Rally are deleted after a task finishes by
  `UserCleanup.cleanup()`.

* Resources created by contexts are deleted when the environment is
  not necessary by the context class `cleanup()`.


Alternatives
------------

* Use OpenStack project resources cleaner (ospurge). This enables us to purge
  the tenants, regardless of resource naming, so we only need to keep track of
  Rally tenants (naming could be a solution here) and resources in admin
  tenant. In this case, we need to think about a case where Rally needs to
  cleanup some resources from a existing tenant while leaving the rest
  available.

* Use/enhance Tempest cleanup command (tempest/cmd/cleanup.py). Compare
  functionality or fix the version in tempest. Maybe tempest_lib would be a
  better place for this, and for the cleanup code in general. In this case,
  we need to think about a case where a Rally scenario creates a tenant, and
  then deletes it but some resources are left around. And also we need to think
  about a case of benchmark on existing tenants.


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  wtakase aka Wataru Takase

Other contributors:
  rvasilets aka Roman Vasilets
  stpierre aka Chris St. Pierre


Work Items
----------

* Consider how to deal resources which don't be named by
  generate_random_name(). For example, Neutron ports which are created as
  side-effect of other resources (routers, networks, servers) don't have
  resource names. In this case, ports always have an "owner" so cleanup should
  check port's owner's name. And what about floating IPs?
  (Needed by use cases 1, 2, 3, 4, 5)

* Add name prefix filter for deleting resource which has specified prefix.
  (Needed by use cases 1, 2, 3, 4, 5)

* Add ability to specify the filter to be used for handling more than
  one prefix.
  (Needed by use cases 3, 5)

* Support negative filter which deletes unmatched resources.
  (Needed by use cases 3, 5)


Dependencies
============

* Consistent resource names: https://review.openstack.org/201545

* Add name pattern filter for resource cleanup:
  https://review.openstack.org/#/c/139643/

* Finish support of benchmarking with existing users:
  https://review.openstack.org/#/c/168524/

* Add support of persistence benchmark environment:
  https://github.com/openstack/rally/blob/master/doc/feature_request/persistence_benchmark_env.rst

* Production ready cleanups:
  https://github.com/openstack/rally/blob/master/doc/feature_request/production_ready_cleanup.rst
