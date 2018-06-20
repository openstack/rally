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
