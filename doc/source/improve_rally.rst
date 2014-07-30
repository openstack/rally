..
      Copyright 2014 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.



.. _improve_rally:

Improve Rally
=============

Main directions of work
-----------------------

    * **Benchmarks**. Improvements in the benchmarking engine & developing new benchmark scenarios.
    * **Deployments**. Making Rally able to support multiple cloud deployment facilities, e.g. Fuel.
    * **CLI**. Enriching the command line interface for Rally.
    * **API**. Work around making Rally to be a Benchmark-as-a-Service system & developing rally-pythonclient.
    * **Incubation**. Efforts to make Rally an integrated project in OpenStack.
    * **Share system**. Benchmark results visualization and paste.openstack.org-like sharing system.
    * **Tempest**. Integration of Tempest tests in Rally for deployment verification.


Where to begin
--------------

It is extremetly simple to participate in different Rally development lines mentioned above. The **Good for start** section of our `Trello board <https://trello.com/b/DoD8aeZy/rally>`_ contains a wide range of tasks perfectly suited for you to quickly and smoothly start contributing to Rally. As soon as you have chosen a task, just log in to Trello, join the corresponding card and move it to the **In progress** section.

The most Trello cards contain basic descriptions of what is to be done there; in case you have questions or want to share your ideas, be sure to contanct us at the ``#openstack-rally`` IRC channel on **irc.freenode.net**.

If you want to grasp a better understanding of several main design concepts used throughout the Rally code (such as **benchmark scenarios**, **contexts** etc.), please read this :ref:`article <main_concepts>`.


How to contribute
-----------------

1. You need a `Launchpad <https://launchpad.net/>`_ account and need to be joined to the `Openstack team <https://launchpad.net/openstack>`_. You can also join the `Rally team <https://launchpad.net/rally>`_ if you want to. Make sure Launchpad has your SSH key, Gerrit (the code review system) uses this.

2. Sign the CLA as outlined in section 3 of the `How To Contribute wiki page <https://wiki.openstack.org/wiki/HowToContribute#If_you.27re_a_developer>`_.

3. Tell git your details:

.. code-block:: none

    git config --global user.name "Firstname Lastname"
    git config --global user.email "your_email@youremail.com"

4. Install git-review. This tool takes a lot of the pain out of remembering commands to push code up to Gerrit for review and to pull it back down to edit it. It is installed using:

.. code-block:: none

    pip install git-review

Several Linux distributions (notably Fedora 16 and Ubuntu 12.04) are also starting to include git-review in their repositories so it can also be installed using the standard package manager.

5. Grab the Rally repository:

.. code-block:: none

    git clone git@github.com:stackforge/rally.git

6. Checkout a new branch to hack on:

.. code-block:: none

    git checkout -b TOPIC-BRANCH

7. Start coding

8. Run the test suite locally to make sure nothing broke, e.g.:

.. code-block:: none

    tox

**(NOTE you should have installed tox<=1.6.1 )**

If you extend Rally with new functionality, make sure you also have provided unit tests for it.

9. Commit your work using:

.. code-block:: none

    git commit -a


Make sure you have supplied your commit with a neat commit message, containing a link to the corresponding blueprint / bug, if appropriate.

10. Push the commit up for code review using:

.. code-block:: none

    git review -R

That is the awesome tool we installed earlier that does a lot of hard work for you.

11. Watch your email or `review site <http://review.openstack.org/>`_, it will automatically send your code for a battery of tests on our `Jenkins setup <http://jenkins.openstack.org/>`_ and the core team for the project will review your code. If there are any changes that should be made they will let you know.

12. When all is good the review site  will automatically merge your code.


(This tutorial is based on: http://www.linuxjedi.co.uk/2012/03/real-way-to-start-hacking-on-openstack.html)
