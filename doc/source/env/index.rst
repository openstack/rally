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

.. _env-component:

=====================
Environment Component
=====================

Rally always tests something outside of itself. It can be an OpenStack cloud,
a Kubernetes cluster or just an HTTP endpoint. An environment is how you tell
Rally about that target.

The environment is stored in the database. Tasks and verifications use it to
know what they run against.

.. warning::

   Environments replace the old **Deployment Component**. The
   ``rally deployment`` commands still work, but they are deprecated and print
   a warning. Use ``rally env`` instead.

.. contents::
  :depth: 2
  :local:

What an environment is
----------------------

An environment owns a set of **platforms**. A platform is an instance of a
platform plugin. The plugin is the code that knows how to talk to one kind of
target.

The environment itself is generic. Everything specific to OpenStack,
Kubernetes or anything else lives in the plugin.

Each environment has:

* a UUID and a name. You can use either one to refer to it.
* a description and an ``extras`` field for your own metadata
* a :ref:`status <env-lifecycle>`
* a :ref:`spec <env-spec>`, which is the input that described how to build it
* data that platforms produced while they were created

Rally itself ships no platform plugins, so a plain ``pip install rally`` gives
you environments without platforms. Such an environment is still valid: it is
enough to run the scenarios that need no specific target, for example the ones
that send HTTP requests. To test something more complex, install a package
with platform plugins for it, like ``rally-openstack`` for OpenStack clouds.

.. _env-spec:

The environment spec
--------------------

A spec is a mapping, written in JSON or YAML. It has two kinds of keys:

* Reserved keys start with ``!`` and configure the environment itself. These
  are ``!version``, ``!description``, ``!extras`` and ``!config``, see
  `Reserved keys`_ below.
* Every other key is the name of a platform plugin, and its value is the
  configuration of that plugin.

For example, a spec with a single platform plugin:

.. code-block:: json

    {
        "existing@openstack": {
            "auth_url": "http://example.net:5000/v3/",
            "admin": {
                "username": "admin",
                "password": "myadminpass",
                "project_name": "admin"
            }
        }
    }

Plugin keys look like ``<plugin-name>@<platform>``. If you write a bare name
without ``@``, Rally turns it into ``existing@<name>``. So this spec means
exactly the same as the one above:

.. code-block:: json

    {
        "openstack": {
            "auth_url": "http://example.net:5000/v3/",
            "admin": {
                "username": "admin",
                "password": "myadminpass",
                "project_name": "admin"
            }
        }
    }

One environment can hold several platforms. But only one plugin per platform.
A spec with two different plugins for ``openstack`` is rejected.

Reserved keys
~~~~~~~~~~~~~

Keys that start with ``!`` configure the environment record itself, not a
platform.

``!version``
  Version of the spec format. Only ``1`` is accepted.

``!description``
  Description of the environment. Same as the ``--description`` argument of
  ``rally env create``. If you pass both, the argument wins.

``!extras``
  Any object you want. Rally stores it and never looks inside. Use it for
  your own metadata, for example a link to the job that built the target.
  Same as ``--extras``.

``!config``
  Reserved for a future feature that will override Rally config options per
  environment. Rally accepts and stores it, but it does nothing yet. Do not
  rely on it.

An empty spec ``{}`` is fine. You get an environment without platforms.

Creating an environment
-----------------------

``rally env create`` needs a name. The spec can come in three ways.

From a file, with ``--spec``:

.. code-block:: console

   $ rally env create --name=my-cloud --spec existing.json

By discovery, with ``--from-sysenv``. Rally asks every installed platform
plugin to look at your shell environment and build a spec from the
credentials it recognizes. Then it tells you what each plugin found:

.. code-block:: console

   $ rally env create --name=my-cloud --from-sysenv
   Your system environment includes specifications of 1 platform(s).
   Discovery information:
        - existing@openstack : Available.

Or with no spec at all. You get an environment with no platforms:

.. code-block:: console

   $ rally env create --name=self

You cannot use ``--spec`` and ``--from-sysenv`` together.

A new environment becomes the default one. Pass ``--no-use`` if you want to
keep the current default. ``--json`` prints the output as JSON, which is
useful in scripts.

If the spec is not valid, Rally prints it together with the errors and exits
with a non-zero code. Nothing is created.

Note that a valid spec does not mean a working target. Creating an
environment checks the shape of the spec, but it does not always talk to the
target. Plugins that only describe something that already exists usually do
not connect at all, so an environment with wrong credentials is still created
and still gets the ``READY`` status. Use ``rally env check`` to find out if it
really works.

.. _env-lifecycle:

Lifecycle and statuses
----------------------

An environment can be in one of these statuses:

``INITIALIZING``
  The record exists and platforms are being created.

``READY``
  All platforms were created. Only in this status the environment can be used
  by tasks and verifications.

``FAILED TO CREATE``
  At least one platform failed. Platforms that were not even tried are marked
  as ``SKIPPED``.

``CLEANING``
  ``rally env cleanup`` is running. The environment goes back to ``READY``
  when it finishes.

``DESTROYING``, ``DESTROYED``, ``FAILED TO DESTROY``
  Statuses of ``rally env destroy``. A failed destroy can be retried.

Allowed transitions:

.. code-block:: text

    INITIALIZING       -> READY, FAILED TO CREATE
    READY              -> CLEANING, DESTROYING
    CLEANING           -> READY
    FAILED TO CREATE   -> DESTROYING
    DESTROYING         -> DESTROYED, FAILED TO DESTROY
    FAILED TO DESTROY  -> DESTROYING

Each platform has its own status of the same kind. That is why ``rally env
show`` can tell you that one platform is fine while another one is broken.

Using environments
------------------

The default environment
~~~~~~~~~~~~~~~~~~~~~~~

Commands that work with an environment accept ``--env <uuid-or-name>``. If
you skip it, Rally uses the default environment. You can also set it with the
``RALLY_ENV`` variable.

``rally env create`` sets the default, unless you passed ``--no-use``. To
change it later use ``rally env use``:

.. code-block:: console

   $ rally env use my-cloud
   Using environment: 4251b491-73b2-422a-aecb-695a94165b5e

The choice is remembered between calls. Rally keeps it in the
``~/.rally/globals`` file.

``rally env list`` marks the current default with ``*``.

The default environment also filters what you see. ``rally task list`` shows
only the tasks that ran against it. Pass ``--all-envs`` to get all of them:

.. code-block:: console

   $ rally task list
   $ rally task list --all-envs

Checking that the target works
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``rally env check`` asks every platform if it is alive and usable. It exits
with a non-zero code if any platform is not available, so you can use it as a
gate in a CI job:

.. code-block:: console

   $ rally env check
   Env `my-cloud (87c1dada-de7b-4627-aa12-fb5f127da9fa)' :-)
   +-----------+-----------+---------+
   | Available | Platform  | Message |
   +-----------+-----------+---------+
   | :-)       | openstack | OK!     |
   +-----------+-----------+---------+

Add ``--detailed`` to see which plugin stands behind each platform and to get
the traceback of whatever failed.

Finding out what the target offers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``rally env check`` only answers "is it alive". ``rally env info`` asks each
platform to describe itself. What you get back is up to the plugin. For an
OpenStack cloud it is the list of available services.

.. code-block:: console

   $ rally env info

Looking at the record
~~~~~~~~~~~~~~~~~~~~~

``rally env show`` prints the stored record. ``rally env show --only-spec``
prints only the spec. The second one is handy when you want to copy an
environment to another machine:

.. code-block:: console

   $ rally env show --only-spec > existing.json

Cleaning up leaked resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tasks usually delete everything they create. Sometimes they do not. A run can
be interrupted, or the target can become unreachable in the middle of a task.
In such cases ``rally env cleanup`` asks each platform to find and delete the
leftovers:

.. code-block:: console

   $ rally env cleanup

It prints how many resources were found, deleted and failed for each
platform. If any deletion failed, it exits with a non-zero code.

Destroying and deleting
~~~~~~~~~~~~~~~~~~~~~~~

These are two separate steps on purpose.

``rally env destroy`` works with the target itself. It undoes what the
platform plugins created. Before that it runs a cleanup, unless you pass
``--skip-cleanup``:

.. code-block:: console

   $ rally env destroy

If that cleanup fails, the destroy is not even started. Fix the problem and
run the command again, or pass ``--skip-cleanup`` if you do not care about
the leftovers.

``rally env delete`` removes the records from the Rally database. It will not
delete an environment that was not destroyed. Use ``--force`` if you really
want that:

.. code-block:: console

   $ rally env delete

Some plugins only describe a target that already exists, like
``existing@openstack``. For them destroy has nothing to undo, so the two
commands are just a delete in two steps.

Several environments at once
----------------------------

You can have as many environments as you want. Make one per target and switch
between them:

.. code-block:: console

   $ rally env create --name=cloud-1 --spec cloud-1.json
   $ rally env create --name=cloud-2 --spec cloud-2.json
   $ rally env list

Then either point each command to the environment you need:

.. code-block:: console

   $ rally env check --env=cloud-1
   $ rally task start --env=cloud-2 task.yaml

or move the default and let the next commands follow it:

.. code-block:: console

   $ rally env use cloud-1

Adding support for a new target
-------------------------------

To teach Rally about a new kind of target you write a platform plugin. See
:ref:`plugins_platform_plugin`.

CLI References
--------------

For the full list of arguments of each command see the
`env category <../cli_reference.html#category-env>`_ of the CLI reference.
