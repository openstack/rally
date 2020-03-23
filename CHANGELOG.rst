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

[3.0.0] - 2020-03-23
--------------------

Added
~~~~~

* CI for covering unit and functional tests against Python 3.8 environment.
  Everything works, so we have proved Python 3.8 support

* Add CI job for testing installation of Rally at Centos 8.

* Updating a *latest* tag of `docker image
  <https://hub.docker.com/r/xrally/xrally>`_ on every merged commit.

Changed
~~~~~~~

* *rally plugin show* command returns not-zero exit code in case of not found
  or multiple match errors

* `docker image <https://hub.docker.com/r/xrally/xrally>`_ is switched to use
  python3.6.

* *path_or_url* plugin follows redirects while validating urls now.

* *rally task sla-check* fails if there is no data.

Deprecated
~~~~~~~~~~

* Command *rally task results* is deprecated. Use *rally task report --json*
  instead.

* Module *rally.common.sshutils* is deprecated. Use *rally.utils.sshutils*
  instead.

* Module *rally.common.yamlutils* is deprecated. It was designed for CLI usage
  and moves to right place.

* Module *rally.common.fileutils* is deprecated.

* All modules from *rally.plugins.common.contexts* are deprecated. Use
  *rally.plugins.task.contexts* instead.

* All modules from *rally.plugins.common.exporters* are deprecated. Use
  *rally.plugins.task.exporters* instead.

* Module *rally.plugins.common.hook.sys_call* is deprecated. Use
  *rally.plugins.task.hooks.sys_call* instead.

* All modules from *rally.plugins.common.hook.triggers* are deprecated. Use
  *rally.plugins.task.hook_triggers* instead.

* All modules from *rally.plugins.common.runners* are deprecated. Use
  *rally.plugins.task.runners* instead.

* All modules from *rally.plugins.common.scenarios* are deprecated. Use
  *rally.plugins.task.scenarios* instead.

* All modules from *rally.plugins.common.sla* are deprecated. Use
  *rally.plugins.task.sla* instead.

* All modules from *rally.plugins.common.verification* are deprecated. Use
  *rally.plugins.verification* instead.

Removed
~~~~~~~

* Python 2.7, Python 3.4 and Python 3.5 support

* Devstack plugin. It was deprecated long time ago. rally-openstack project
  should be used instead

* *rally.common.utils.distance* method was deprecated since Rally 0.4.1

* *rally.common.utils.format_float_to_str* method was deprecated since
  Rally 0.11.2. *rally.utils.strutils.format_float_to_str* should be used
  instead.

* *rally.task.atomic.optional_action_timer* decorator was deprecated since
  Rally 0.10.0

* *rally.task.hook.Hook* class was deprecated since Rally 0.10.0.
  *rally.task.hook.HookAction* should be used instead.

* *rally.task.trigger* module was deprecated since Rally 0.10.0.
  *rally.task.hook.HookTrigger* should be used instead.

* *rally.common.i18n* module was deprecated since Rally 0.10.0

* *namespace* argument of *configure* decorator of Scenario, Context,
  Validators plugins. It was deprecated since Rally 0.10.0 in favor of
  *platform*.

* *install_rally.sh* script is too complicated and installs only rally
  framework without plugins.

Fixed
~~~~~

* inaccurate calculation of 90 and 95 percentiles in case of 10k+ iterations

[2.1.0] - 2019-11-19
--------------------

Please note that Python 2.7 will reach the end of its life on
January 1st, 2020. A future version of Rally will drop support for Python 2.7,
it will happen soon. Also, the same will happen with support of Python 3.4 and
Python 3.5

Removed
~~~~~~~

Library *netaddr* from direct project requirements. We never use it at Rally
framework.

Fixed
~~~~~

Support of latest alembic

`Launchpad-bug #1844884 <https://launchpad.net/bugs/1844884>`_

[2.0.0] - 2019-09-13
--------------------

Changed
~~~~~~~

python jsonschema dependency is not limited by *<3.0.0* anymore and you can
use draft-7 as for now.

Removed
~~~~~~~

* *rally task sla_check* command was deprecated in Rally 0.8.0 in favor of
  *rally task sla-check*.

* *rally-manage db* command (and the whole *rally-manage* entry-point) was
  deprecated in Rally 0.10.0 in favor of *rally db* command.

* *--namespace* argument was deprecated in Rally 0.10.0 in favor of
  *--platform* which has better meaning.
  Affected commands: *rally plugin show*, *rally plugin list*,
  *rally verify list-plugins*, *rally verify create-verifier*.

* *--tasks* argument of *rally task report* command and *--task* argument of
  *rally task use* command were deprecated in Rally 0.10.0 in favor of
  unified *--uuid* argument.

* *--junit* argument of *rally task report* command is deprecated in
  Rally 0.10.0 in favor of *rally task export --type junit-xml*

[1.6.0] - 2019-06-19
--------------------

Added
~~~~~

A list of tests to skip while running verification now supports regular
expressions.

Fixed
~~~~~

* incompatibility with SQLAlchemy 1.3
* several py3 issues of verification component

[1.5.1] - 2019-05-15
--------------------

Fixed
~~~~~

**rally deployment create --fromenv** creates wrong spec for
rally-openstack<=1.4.0 which doesn't pass **rally deployment check**.

`Launchpad-bug #1829030 <https://launchpad.net/bugs/1829030>`_


[1.5.0] - 2019-05-08
--------------------

Added
~~~~~

New two charts **EmbeddedChart** and **EmbeddedExternalChart** for embedding
custom html code or external pages as complete charts of scenarios.

[1.4.1] - 2019-02-28
--------------------

Fixed
~~~~~

* Python 3 issue of Verification component
* Docker README file

[1.4.0] - 2019-02-04
--------------------

Changed
~~~~~~~

* Add the --html-static option to commands ``rally task trends``, it could generate
  trends report with embedded js/css.

* Removed dependency to ``morph`` library.

Fixed
~~~~~

* ``rally`` command crashes while calling without any arguments

* Fix the ssh error while passing an dss key in ssh utils.

  `Launchpad-bug #1807870 <https://launchpad.net/bugs/1807870>`_


[1.3.0] - 2018-12-01
--------------------

Added
~~~~~

* Add the --deployment option to commands ``rally task report`` and
  ``rally task export`` that allows to report/export all tasks from defined
  deployment.

* Briefly: the new base image is published at `Docker Hub
  <https://hub.docker.com/r/xrally/xrally>`_
  Detailed story: Long time ago Rally team introduced first docker images which
    were hosted by `rallyforge account at Docker Hub
    <https://hub.docker.com/r/rallyforge/rally/>`_. Due to various
    circumstances we lost access to that account and Docker support restored
    access to it in a strange way (we lost all repositories and could not
    recreate them). That is why Rally team started publishing docker images
    from scratch. The new organization was created -`xRally
    <https://hub.docker.com/r/xrally>`_ . Since we already had plans to move
    OpenStack plugins to the separate repository, we started publishing images
    with in-tree OpenStack plugins to `xrally/xrally-openstack repository
    <https://hub.docker.com/r/xrally/xrally-openstack/>`_. As soon as, a
    separate package for OpenStack plugins was introduced, we switched the
    source of `xrally/xrally-openstack Docker Hub repository
    <https://hub.docker.com/r/xrally/xrally-openstack/>`_ to `rally-openstack
    git repository <http://github.com/openstack/rally-openstack>`_.
    As for Rally 1.0.0 we finally have pure framework without heavy
    dependencies and can start publishing separate images for Rally framework
    itself which can be used as a base image for all plugins.
    New images will be located at `xrally/xrally Docker Hub repository
    <https://hub.docker.com/r/xrally/xrally>`_.

Changed
~~~~~~~

* ``rally --version`` prints version of Rally framework with versions of
  installed plugins instead of printing just version of Rally framework.
* Dockerfile moved from the root directory to ./etc/docker/

Fixed
~~~~~

A floating bug with ``constant_for_duration`` runner.

`Launchpad-bug #1800447 <https://launchpad.net/bugs/1800447>`_

[1.2.1] - 2018-09-27
--------------------

Minor inner fixes

[1.2.0] - 2018-09-19
--------------------

Added
~~~~~

* New validator ``map_keys`` for checking keys of specific argument.
* Support of ElasticSearch 6.x cluster *elastic* exporter.

Changed
~~~~~~~

* Improved validation errors for task component.
* [ElasticSearch exporter] Do not send 'no-name-action' index when the item
  fails after some atomic actions completed and there is a root atomic.
  For example, there is 'wait-for-some-resource-ready' action. It consists of
  a bunch of get requests to update the current status. After specified timeout
  this action can fail if the resource is not in the right state. In such case,
  there is no reason to use 'no-name-action' for saving the error, the parent
  index (i.e 'wait-for-some-resource-ready') will already store it.

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
  `Launchpad-bug #1785549 <https://launchpad.net/bugs/1785549>`_

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
