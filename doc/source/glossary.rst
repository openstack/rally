:tocdepth: 1

========
Glossary
========

.. warning:: Unfortunately, our glossary is not full, but the Rally
  team is working on improving it.  If you cannot find a definition in
  which you are interested, feel free to ping us via IRC
  (#openstack-rally channel at Freenode) or via E-Mail
  (openstack-dev@lists.openstack.org with tag [Rally]).

.. contents::
  :depth: 1
  :local:

Common
======

Alembic
-------

A lightweight database migration tool which powers Rally migrations.
Read more at `Official Alembic documentation <http://alembic.readthedocs.io/en/latest/>`_

DB Migrations
-------------

Rally supports database schema and data transformations, which are also
known as migrations. This allows you to get your data up-to-date with
latest Rally version.

Rally
-----

A testing tool that automates and unifies multi-node OpenStack deployment
and cloud verification. It can be used as a basic tool
for an OpenStack CI/CD system that would continuously improve its SLA,
performance and stability.

Rally Config
------------

Rally behavior can be customized by editing its configuration file,
*rally.conf*, in `configparser
<https://docs.python.org/3.4/library/configparser.html>`_
format. While being installed, Rally generates a config with default
values from its `sample
<https://github.com/openstack/rally/blob/master/etc/rally/rally.conf.sample>`_.
When started, Rally searches for its config in
"<sys.prefix>/etc/rally/rally.conf", "~/.rally/rally.conf",
"/etc/rally/rally.conf"

Rally DB
--------

Rally uses a relational database as data storage. Several database backends
are supported: SQLite (default), PostgreSQL, and MySQL.
The database connection can be set via the configuration file option
*[database]/connection*.

Rally Plugin
------------

Most parts of Rally
`are pluggable <https://rally.readthedocs.io/en/latest/plugins.html>`_.
Scenarios, runners, contexts and even charts for HTML report are plugins.
It is easy to create your own plugin and use it. Read more at
`plugin reference <https://rally.readthedocs.io/en/latest/plugin/plugin_reference.html>`_.

Deployment
==========

Deployment
----------

A set of information about target environment (for example: URI and
authentication credentials) which is saved in the database. It is used
to define the target system for testing each time a task is started.
It has a "type" value which changes task behavior for the selected
target system; for example type "openstack" will enable OpenStack
authentication and services.

Task
====

Cleanup
-------

This is a specific context which removes all resources on target
system that were created by the current task.  If some Rally-related
resources remain, please `file a bug
<https://bugs.launchpad.net/rally>`_ and attach the task file and a
list of remaining resources.

Context
-------

A type of plugin that can run some actions on the target environment
before the workloads start and after the last workload finishes. This
allows, for example, preparing the environment for workloads (e.g.,
create resources and change parameters) and restoring the environment
later. Each Context must implement ``setup()`` and ``cleanup()``
methods.

Input task
----------

A file that describes how to run a Rally Task. It can be in JSON or
YAML format.  The *rally task start* command needs this file to run
the task.  The input task is pre-processed by the `Jinja2
<http://jinja.pocoo.org/>`_ templating engine so it is very easy to
create repeated parts or calculate specific values at runtime. It is
also possible to pass values via CLI arguments, using the
*--task-args* or *--task-args-file* options.

Runner
------

This is a Rally plugin which decides how to run Workloads.  For
example, they can be run serially in a single process, or using
concurrency.

Scenario
--------

Synonym for `Workload <#workload>`_

Service
-------

Abstraction layer that represents target environment API.  For
example, this can be some OpenStack service.  A Service provides API
versioning and action timings, simplifies API calls, and reduces code
duplication. It can be used in any Rally plugin.

SLA
---

Service-Level Agreement (Success Criteria).
Allows you to determine whether a subtask or workload is successful
by setting success criteria rules.

Subtask
-------

A part of a Task. There can be many subtasks in a single Task.

Task
----

An entity which includes all the necessary data for a test run, and
results of this run.

Workload
--------

An important part of Task: a plugin which is run by the runner.  It is
usually run in separate thread. Workloads are grouped into Subtasks.

Verify
======

Rally can run different subunit-based testing tools against a target
environment, for example `tempest
<http://docs.openstack.org/developer/tempest/>`_ for OpenStack.

Verification
------------

A result of running some third-party subunit-based testing tool.
