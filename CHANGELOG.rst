=========
Changelog
=========

.. Changelogs are for humans, not machines. The end users of Rally project are
   human beings who care about what's is changing, why and how it affects them.
   Please leave these notes as much as possible human oriented.

.. Each release can use the next sections:

    - **Added** for new features.
    - **Changed** for changes in existing functionality.
    - **Deprecated** for soon-to-be removed features/plugins.
    - **Removed** for now removed features/plugins.
    - **Fixed** for any bug fixes.

.. Release notes for existing releases are MUTABLE! If there is something that
   was missed or can be improved, feel free to change it!

[1.1.0] - 2018-08-07
--------------------

Added
~~~~~

* Introducing ``rally env cleanup`` command for performing disaster cleanup.
* New CI jobs for checking compatibility with Python 3.4, 3.6, 3.7 .

Changed
~~~~~~~

* The output of json task result exporter (``rally task report --json``) is
  extended with information about environment where task was executed (new
  ``env_name`` and ``env_uuid`` properties)

* Add the --filter-by option to the command ``rally task detailed``, which
  allows us to show only those workloads which we are interested in (see the
  examples below).
  Examples:

  1. show only failed workloads
     ``rally task detailed --filter-by sla-failures``
  2. show only those workloads which include the next scenario plugin(s)
     ``rally task detailed --filter-by scenarios=scenario1[,scenarios2...]``

* `requirements
  <https://github.com/openstack/rally/blob/1.1.0/requirements.txt>`_ and
  `constraints (suggested versions)
  <https://github.com/openstack/rally/blob/1.1.0/upper-constraints.txt>`_ files
  are updated.


Removed
~~~~~~~

* Disturbing warning message about removing in-tree OpenStack plugins. This
  message became redundant after Rally 1.0.0 when such plugins were removed.
* OpenStack related configuration options for sample file.
* Deprecated in Rally 0.10 ``rally.task.exporter.Exporter`` class in favor of
  ``rally.task.exporter.TaskExporter``.

Fixed
~~~~~

* Building HTML reports for verifications at python 3 environment.
  `Lauchpad-bug #1785549 <https://launchpad.net/bugs/1785549>`_

Deprecated
~~~~~~~~~~

* 'async' argument of API method task.abort in favor of 'wait' argument which
  doesn't conflict with a reserved keyword in python 3.7

[1.0.0] - 2018-06-20
--------------------

It finally happened. We are happy to inform you that OpenStack plugins has a
single home - https://github.com/openstack/rally-openstack .
All in-tree plugins are removed now and framework part become more lightweight.

What does it mean for you?!
~~~~~~~~~~~~~~~~~~~~~~~~~~~
If you are interested only in OpenStack plugins, just change the package you
are installing from ``rally`` to ``rally-openstack``. If you have custom
OpenStack plugins which inherits from upstream, change python imports from
``rally.plugins.openstack`` to ``rally_openstack``. That is all.

If you are interested not only in OpenStack, you can start using your favourite
tool for various platforms and systems. Here you can find our first attempts
to seize the world - https://github.com/xrally/xrally-docker and
https://github.com/xrally/xrally-kubernetes.

Changed
~~~~~~~

Since OpenStack plugins were moved to the separate repository, the new release
notes should become light as well, so there is no need in separate pages for
each release. All release notes will be aggregated in
`a single file CHANGELOG.rst
<https://github.com/openstack/rally/blob/master/CHANGELOG.rst>`_.

Also, it is sad to mention, but due to OpenStack policies we need to stop
duplicating release notes at ``git tag message``. At least for now.

Removed
~~~~~~~

* All OpenStack related plugins.

Fixed
~~~~~

* Validation of existing platforms in Python 3 environment.
* Support of testr for verifiers.

[0.0.0] - [0.12.1]
------------------

Release notes for Rally ``0.0.0``-``0.12.1`` are available at
https://github.com/openstack/rally/tree/master/doc/release_notes/archive
