Testing
=======

Please, don't hesitate to write tests ;)


Unit tests
----------

*Files: /tests/unit/**

The goal of unit tests is to ensure that internal parts of the code work properly.
All internal methods should be fully covered by unit tests with a reasonable mocks usage.


About Rally unit tests:

- All `unit tests <http://en.wikipedia.org/wiki/Unit_testing>`_ are located inside /tests/unit/*
- Tests are written on top of: *unittest* lib
- `Tox <https://tox.readthedocs.org/en/latest/>`_ is used to run unit tests


To run unit tests locally::

  $ pip install tox
  $ tox

To run py311 or pep8 only::

  $ tox -e <name>

  # NOTE: <name> is one of py311 or pep8

To run py311 against mysql or psql

  $ export RALLY_UNITTEST_DB_URL="mysql://user:secret@localhost/rally"
  $ tox -epy311

To run specific test of py311::

  $ tox -e py311 -- tests.unit.test_osclients

To get test coverage::

  $ tox -e cover

  # NOTE: Results will be in ./cover/index.html

To generate docs::

  $ tox -e docs

  # NOTE: Documentation will be in doc/source/_build/html/index.html

Functional tests
----------------

*Files: /tests/functional/**

The goal of `functional tests <https://en.wikipedia.org/wiki/Functional_testing>`_ is to check that everything works well together.
Fuctional tests use Rally API only and check responses without touching internal parts.

To run functional tests locally::

  $ tox -e functional

By default every test uses its own SQLite database. To run the tests against
MySQL/MariaDB or PostgreSQL, pass a connection string to the database server
through the ``RALLY_FUNCTIONAL_DB_URL`` environment variable. The user needs
permission to create databases: every test creates its own database on that
server and drops it afterwards, so tests can still run in parallel::

  $ RALLY_FUNCTIONAL_DB_URL="mysql+pymysql://rally:rally@127.0.0.1/" \
      tox -e functional
  $ RALLY_FUNCTIONAL_DB_URL="postgresql+psycopg://rally:rally@127.0.0.1/postgres" \
      tox -e functional

Both drivers (the ``mysql`` and ``postgres`` extras) are installed in the
``functional`` environment and need no system packages. Use the ``mysql``
driver for MariaDB as well.

The number of parallel workers defaults to the number of CPUs. Set
``PYTEST_XDIST_AUTO_NUM_WORKERS`` to change it.

Output of every Rally execution will be collected under some reports root in
directory structure like: reports_root/ClassName/MethodName_suffix.extension
This functionality implemented in tests.functional.utils.Rally.__call__ method.
Use 'gen_report_path' method of 'Rally' class to get automatically generated file
path and name if you need. You can use it to publish html reports, generated
during tests.
Reports root can be passed through environment variable 'REPORTS_ROOT'. Default is
'rally-cli-output-files'.


Rally CI scripts
----------------

*Files: /tests/ci/**

This directory contains scripts and files related to the Rally CI system.

Rally Style Commandments
------------------------

*File: /tests/hacking/checks.py*

This module contains Rally specific hacking rules for checking commandments.

