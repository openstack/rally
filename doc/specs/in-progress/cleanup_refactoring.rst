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

Specifically, there are three cases we need to be able to handle:

* Cleanup of all resources created by a single subtask run;
* Cleanup of all resources created by contexts; and
* Cleanup of all resources, possibly (or probably) out-of-band.

In each case, this can be handled by matching resource names with a
subset of plugins. For instance, to clean up scenario resources, we
will do something like:

.. code-block:: python

    scenarios = [cls for cls in discover.itersubclasses(scenario.Scenario)
                 if issubclass(cls, utils.RandomNameGeneratorMixin)]
    for resource in resource_manager.list():
        manager = resource_manager_cls(raw_resource=resource, ...)
        if utils.name_matches_object(resource_manager.name, scenarios,
                                     task_id=task_id):
            manager.delete()

This is pseudocode that hides much of the complexity of our current
cleanup process, but it demonstrates the basic idea:

#. Generate a list of subclasses to delete resources for. In this case
   we use ``rally.task.scenario.Scenario``, but for context cleanup it
   would be ``rally.task.context.Context``, and for global cleanup it
   would be ``rally.common.plugin.plugin.Plugin``. In all three cases
   we would only delete resources for plugins that have
   ``rally.common.utils.RandomNameGeneratorMixin`` as a superclass;
   this lets us easily perform global cleanup without needing to worry
   about which plugin subclasses might implement
   ``RandomNameGeneratorMixin``.
#. For each resource manager, list resources.
#. If the resource name matches the list of possible patterns gleaned
   from the set of classes, delete it.

A fair bit of functionality will need to be added to support this:

* ``rally.plugins.openstack.cleanup.manager.cleanup()`` will
  need to accept a keyword argument specifying the type of
  cleanup. This should be a superclass that will be used to discover
  the subclasses to delete resources for. It will be passed to
  ``rally.plugins.openstack.cleanup.manager.SeekAndDestroy``,
  which will also need to accept the argument and generate the list of
  classes.
* ``rally.plugins.openstack.cleanup.base``,
  ``rally.plugins.openstack.cleanup.manager`` and
  ``rally.plugins.openstack.cleanup.resources`` need to be
  moved out of the context space, since they will be used not only by
  the cleanup context to do scenario cleanup, but also to do
  out-of-band cleanup of all resources.
* A new function, ``name()``, will need to be added to
  ``rally.plugins.openstack.cleanup.base.ResourceManager``
  so that we can determine the name of a resource in order to match it.
* A ``task_id`` keyword argument will be added to
  ``name_matches_object`` and ``name_matches_pattern`` in order to
  ensure that we only match names from the currently-running
  task. This will need to be passed along starting with
  ``rally.plugins.openstack.cleanup.manager.cleanup()``, and
  added as a keyword argument to every intermediate function.

Additionally, a new top-level command will be added::

    rally cleanup [--deployment <deployment>] [--task <uuid>]

This will invoke cleanup of all resources, either for a specific task,
or for any rally-created resource at all, regardless of task ID. This
will not be ``rally task cleanup`` because it can be run with or
without a task.

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

#. Consider how to deal resources which don't be named by
   generate_random_name(). For example, Neutron ports which are
   created as side-effect of other resources (routers, networks,
   servers) don't have resource names. In this case, ports always have
   an "owner" so cleanup should check port's owner's name. And what
   about floating IPs?  (Needed by use cases 1, 2, 3, 4, 5)
#. Modify ``name_matches_{object,pattern}`` to accept a task ID.
#. Add ``name()`` functions to all ``ResourceManager`` subclasses.
#. Move
   ``rally.plugins.openstack.cleanup.manager.{base,manager,resources}``
   to ``rally.plugins.openstack.cleanup``.
#. Modify ``rally.plugins.openstack.cleanup.manager.cleanup()`` to
   accept a task ID and a superclass, pass them along to
   ``SeekAndDestroy``, and generally Do The Right Thing with them.
#. Create the ``rally cleanup`` command.
#. Support negative filter which deletes unmatched resources. (Needed
   by use cases 3, 5)


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
