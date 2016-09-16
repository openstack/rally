..
      Copyright 2015 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _contribute:

Contribute to Rally
===================

Where to begin
--------------

Please take a look `our Roadmap <https://docs.google.com/a/mirantis.com/spreadsheets/d/16DXpfbqvlzMFaqaXAcJsBzzpowb_XpymaK2aFY2gA2g/edit#gid=0>`_ to get information about our current work directions.

In case you have questions or want to share your ideas, be sure to contact us at the ``#openstack-rally`` IRC channel on **irc.freenode.net**.

If you are going to contribute to Rally, you will probably need to grasp a better understanding of several main design concepts used throughout our project (such as **benchmark scenarios**, **contexts** etc.). To do so, please read :ref:`this article <main_concepts>`.


How to contribute
-----------------

1. You need a `Launchpad <https://launchpad.net/>`_ account and need to be joined to the `OpenStack team <https://launchpad.net/openstack>`_. You can also join the `Rally team <https://launchpad.net/rally>`_ if you want to. Make sure Launchpad has your SSH key, Gerrit (the code review system) uses this.

2. Sign the CLA as outlined in the `account setup <http://docs.openstack.org/infra/manual/developers.html#development-workflow>`_ section of the developer guide.

3. Tell git your details:

.. code-block:: bash

    git config --global user.name "Firstname Lastname"
    git config --global user.email "your_email@youremail.com"

4. Install git-review. This tool takes a lot of the pain out of remembering commands to push code up to Gerrit for review and to pull it back down to edit it. It is installed using:

.. code-block:: bash

    pip install git-review

Several Linux distributions (notably Fedora 16 and Ubuntu 12.04) are also starting to include git-review in their repositories so it can also be installed using the standard package manager.

5. Grab the Rally repository:

.. code-block:: bash

    git clone git@github.com:openstack/rally.git

6. Checkout a new branch to hack on:

.. code-block:: bash

    git checkout -b TOPIC-BRANCH

7. Start coding

8. Run the test suite locally to make sure nothing broke, e.g. (this will run py34/py27/pep8 tests):

.. code-block:: bash

    tox

**(NOTE: you should have installed tox<=1.6.1)**

If you extend Rally with new functionality, make sure you have also provided unit and/or functional tests for it.

9. Commit your work using:

.. code-block:: bash

    git commit -a


Make sure you have supplied your commit with a neat commit message, containing a link to the corresponding blueprint / bug, if appropriate.

10. Push the commit up for code review using:

.. code-block:: bash

    git review -R

That is the awesome tool we installed earlier that does a lot of hard work for you.

11. Watch your email or `review site <http://review.openstack.org/>`_, it will automatically send your code for a battery of tests on our `Jenkins setup <http://jenkins.openstack.org/>`_ and the core team for the project will review your code. If there are any changes that should be made they will let you know.

12. When all is good the review site  will automatically merge your code.


(This tutorial is based on: http://www.linuxjedi.co.uk/2012/03/real-way-to-start-hacking-on-openstack.html)

Testing
-------

Please, don't hesitate to write tests ;)


Unit tests
^^^^^^^^^^

*Files: /tests/unit/**

The goal of unit tests is to ensure that internal parts of the code work properly.
All internal methods should be fully covered by unit tests with a reasonable mocks usage.


About Rally unit tests:

- All `unit tests <http://en.wikipedia.org/wiki/Unit_testing>`_ are located inside /tests/unit/*
- Tests are written on top of: *testtools* and *mock* libs
- `Tox <https://tox.readthedocs.org/en/latest/>`_ is used to run unit tests


To run unit tests locally:

.. code-block:: console

  $ pip install tox
  $ tox

To run py34, py27 or pep8 only:

.. code-block:: console

  $ tox -e <name>

  #NOTE: <name> is one of py34, py27 or pep8

To run a single unit test e.g. test_deployment

.. code-block:: console

  $ tox -e <name> -- <test_name>

  #NOTE: <name> is one of py34, py27 or pep8
  #      <test_name> is the unit test case name, e.g tests.unit.test_osclients

To debug issues on the unit test:

- Add breakpoints on the test file using ``import pdb;`` ``pdb.set_trace()``
- Then run tox in debug mode:

.. code-block:: console

  $ tox -e debug <test_name>
  #NOTE: use python 2.7
  #NOTE: <test_name> is the unit test case name

  or 

.. code-block:: console

  $ tox -e debug34 <test_name>
  #NOTE: use python 3.4
  #NOTE: <test_name> is the unit test case name

To get test coverage:

.. code-block:: console

  $ tox -e cover

  #NOTE: Results will be in /cover/index.html

To generate docs:

.. code-block:: console

  $ tox -e docs

  #NOTE: Documentation will be in doc/source/_build/html/index.html

Functional tests
^^^^^^^^^^^^^^^^

*Files: /tests/functional/**

The goal of `functional tests <https://en.wikipedia.org/wiki/Functional_testing>`_ is to check that everything works well together.
Functional tests use Rally API only and check responses without touching internal parts.

To run functional tests locally:

.. code-block:: console

  $ source openrc
  $ rally deployment create --fromenv --name testing
  $ tox -e cli

  #NOTE: openrc file with OpenStack admin credentials

Output of every Rally execution will be collected under some reports root in
directory structure like: reports_root/ClassName/MethodName_suffix.extension
This functionality implemented in tests.functional.utils.Rally.__call__ method.
Use 'gen_report_path' method of 'Rally' class to get automatically generated file
path and name if you need. You can use it to publish html reports, generated
during tests.
Reports root can be passed throw environment variable 'REPORTS_ROOT'. Default is
'rally-cli-output-files'.

Rally CI scripts
^^^^^^^^^^^^^^^^

*Files: /tests/ci/**

This directory contains scripts and files related to the Rally CI system.

Rally Style Commandments
^^^^^^^^^^^^^^^^^^^^^^^^

*Files: /tests/hacking/*

This module contains Rally specific hacking rules for checking commandments.

For more information about Style Commandments, read the `OpenStack Style Commandments manual <http://docs.openstack.org/developer/hacking/>`_.
