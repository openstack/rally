..
      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _verifiers:

=========
Verifiers
=========

.. contents::
  :depth: 1
  :local:

What is it?
-----------

Verifier Plugin is a compatibility layer between Rally and the specific tool
(such as Tempest) which runs tests. It implements features like installation,
configuration, upgrades, running, etc in terms of the tool. It is a driver in
other words.
It is a pluggable entity, which means that you can easily add support for
whatever tool you want (see :ref:`howto-add-support-for-new-tool` page for
more information). Even more, you can deliver such plugin separately from Rally
itself, but we firmly recommend to push a change to Rally upstream (see
:ref:`contribute` guide), so Rally core-team will able to review it and help
to improve.

Verifier is an instance of the Verifier Plugin. It is an installed tool.
For example, "Tempest" is a set of functional tests, it is Verifier Plugin
(we have a plugin for it). Installed Tempest 12.0 from
https://github.com/openstack/tempest in a virtual environment is the verifier.

Verifier is not aligned to any particular deployment like it was in the past,
you can use one verifier for testing unlimited number of deployments (each
deployment will have separate configuration files for the tool).

Verifier & Verifier Plugin are the main entities which Verification component
operates with. Another one is the verifications results.

Verifier statuses
-----------------

All verifiers can be in next statuses:

* *init* - Initial state. It appears while you call ``rally verify
  create-verifier`` command and installation step is not yet started.
* *installing* - Installation of the verifier is not a quick task. It is about
  cloning tool, checking packages or installing virtual environments with all
  required packages. This state indicates that this step is in the process.
* *installed* - It should be one of your favourite states. It means that
  everything is ok and you can start verifying your cloud.
* *updating* - This state identifies the process of updating verifier (version,
  source, packages, etc.).
* *extending* - The process of extending a verifier by its plugins.
* *failed* - Something went wrong while installation.

.. _verification_statuses:

Verification statuses
---------------------

* *init* - Initial state. It appears instantly after calling
  ``rally verify start`` command before the actual run of verifier's tool.
* *running* - Identifies the process of execution tool.
* *finished*- Verification is finished without errors and failures.
* *failed* - Verification is finished, but there are some failed tests.
* *crashed* - Unexpected error had happened while running verification.


.. _known-verifier-types:

Known verifier types
--------------------

Out of the box
""""""""""""""

You can execute command ``rally verify list-plugins`` locally to check
available verifiers in your environment.

Cut down from Global :ref:`plugin-reference` page:

.. generate_plugin_reference::
  :base_cls: Verifier Manager

Third-party
"""""""""""

Nothing here yet.

