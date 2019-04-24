=====
Rally
=====

Rally is tool & framework that allows one to write simple plugins and combine
them in complex tests scenarios that allows to perform all kinds of testing!

Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/rally.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. image:: https://img.shields.io/pypi/v/rally.svg
    :target: https://pypi.org/project/rally/
    :alt: Latest Version

.. image:: https://img.shields.io/badge/gitter-join_chat-ff69b4.svg
    :target: https://gitter.im/rally-dev/Lobby
    :alt: Gitter Chat

.. image:: https://img.shields.io/badge/tasks-trello_board-blue.svg
    :target: https://trello.com/b/DoD8aeZy/rally
    :alt: Trello Board

.. image:: https://img.shields.io/github/license/openstack/rally.svg
    :target: https://www.apache.org/licenses/LICENSE-2.0
    :alt: Apache License, Version 2.0


What is Rally
=============

Rally is intended to provide a testing framework that is
capable to perform **specific**, **complicated** and **reproducible**
test cases on **real deployment** scenarios.

**Rally** workflow can be visualized by the following diagram:

.. image:: doc/source/images/Rally-Actions.png
   :alt: Rally Architecture


Who Is Using Rally
==================

.. image:: doc/source/images/Rally_who_is_using.png
   :alt: Who is Using Rally


Documentation
=============

`Rally documentation on ReadTheDocs <https://rally.readthedocs.org/en/latest/>`_
is a perfect place to start learning about Rally. It provides you with an
**easy** and **illustrative** guidance through this benchmarking tool.

For example, check out the `Rally step-by-step tutorial
<https://rally.readthedocs.io/en/latest/quick_start/tutorial.html>`_ that
explains, in a series of lessons, how to explore the power of Rally in
benchmarking your OpenStack clouds.

Architecture
------------

In terms of software architecture, Rally is built of 4 main components:

1. **Environment** - one of key component in Rally. It manages and stores
   information about tested platforms. Env manager is using platform plugins
   to: create, delete, cleanup, check health, obtain information about
   platforms.
2. **Task** component is responsible for executing tests defined in
   task specs, persisting and reporting results.
3. **Verification** component allows to wrap subunit-based testing tools and
   provide complete tool on top of them with allow to do pre configuration,
   post cleanup as well process and persist results to Rally DB for future use
   like reporting and results comparing.

Use Cases
---------

There are 3 major high level Rally Use Cases:

.. image:: doc/source/images/Rally-UseCases.png
   :alt: Rally Use Cases


Typical cases where Rally aims to help are:

- Automate measuring & profiling focused on how new code changes affect the
  OpenStack performance;
- Using Rally profiler to detect scaling & performance issues;
- Investigate how different deployments affect the OS performance:

    - Find the set of suitable OpenStack deployment architectures;
    - Create deployment specifications for different loads (amount of
      controllers, swift nodes, etc.);
- Automate the search for hardware best suited for particular OpenStack cloud;
- Automate the production cloud specification generation:

    - Determine terminal loads for basic cloud operations: VM start & stop,
      Block Device create/destroy & various OpenStack API methods;
    - Check performance of basic cloud operations in case of different loads.

Links
-----

* Free software: Apache license
* Documentation: https://rally.readthedocs.org/en/latest/
* Source: https://opendev.org/openstack/rally
* Bugs: https://bugs.launchpad.net/rally
* Step-by-step tutorial: https://rally.readthedocs.io/en/latest/quick_start/tutorial.html
* Launchpad page: https://launchpad.net/rally
* Gitter chat: https://gitter.im/rally-dev/Lobby
* Trello board: https://trello.com/b/DoD8aeZy/rally
