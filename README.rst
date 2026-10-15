=====
Rally
=====

.. image:: https://img.shields.io/pypi/v/rally.svg
    :target: https://pypi.org/project/rally/
    :alt: Latest Version

.. image:: https://img.shields.io/github/license/openstack/rally.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Apache License, Version 2.0

Rally is a tool for testing how a system behaves under load. You describe
what to do, how hard to push and what counts as success in a task file.
Rally runs it, measures every iteration, keeps the results and turns them
into reports.

The Rally core has no code for any particular system; plugins connect it to
one. OpenStack support comes from the `rally-openstack`_ package, a few
generic plugins (for example, HTTP requests) ship with Rally itself, and you
can write plugins for your own services.

Features
========

* Load tests with clear pass or fail criteria (SLA), so a task can gate a
  CI pipeline.
* Verification: runs an existing test suite such as Tempest against an
  environment and compares the results with earlier runs.
* History: every result is kept in a `database`_.
* Reports: interactive HTML, trends across many runs, JSON, JUnit XML and
  Elasticsearch export.
* Plugins for everything: platforms, scenarios, runners, contexts, SLA
  criteria, hooks, exporters and verifiers. Write your own or install a
  plugin package.

Quick start
===========

No cloud needed: this task sends HTTP requests to a website and checks that
every response is successful and fast enough.

.. code-block:: console

    $ pip install rally
    $ rally db create
    $ rally env create --name local
    $ cat > task.yaml << EOF
    ---
    version: 2
    title: My first task
    subtasks:
      - title: Check that example.com responds
        scenario:
          HttpRequests.check_request:
            url: https://www.example.com
            method: GET
            status_code: 200
        runner:
          constant:
            times: 20
            concurrency: 4
        sla:
          failure_rate:
            max: 0
          max_seconds_per_iteration: 2
    EOF
    $ rally task start task.yaml
    $ rally task report --out report.html

To test an OpenStack cloud, install ``rally-openstack`` and follow the
`tutorial`_.

Links
=====

* Documentation: https://rally.readthedocs.io/latest/ (also published at
  https://docs.openstack.org/rally/latest/)
* Release notes:
  https://opendev.org/openstack/rally/src/branch/master/CHANGELOG.rst
* Source: https://opendev.org/openstack/rally
* Bugs: https://bugs.launchpad.net/rally
* Contributing:
  https://opendev.org/openstack/rally/src/branch/master/CONTRIBUTING.rst
* OpenStack plugins: https://opendev.org/openstack/rally-openstack
* License: Apache License, Version 2.0

.. _rally-openstack: https://pypi.org/project/rally-openstack/
.. _database: https://rally.readthedocs.io/latest/install.html#database
.. _tutorial: https://rally.readthedocs.io/latest/quick_start/tutorial.html
