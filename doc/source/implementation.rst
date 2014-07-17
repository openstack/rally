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

.. _implementation:

Implementation
==============


Benchmark engine
----------------

The :mod:`rally.benchmark.engine` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.engine
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.benchmark.runners` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.runners
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.benchmark.context` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.context
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.benchmark.processing` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.processing
    :members:
    :undoc-members:
    :show-inheritance:


Benchmark scenarios
-------------------

The :mod:`rally.benchmark.scenarios.utils` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.utils
    :members:
    :undoc-members:
    :show-inheritance:

The Cinder Scenarios
^^^^^^^^^^^^^^^^^^^^

The :mod:`rally.benchmark.scenarios.cinder.volumes` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.cinder.volumes
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.benchmark.scenarios.cinder.utils` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.cinder.utils
    :members:
    :undoc-members:
    :show-inheritance:

The Keystone Scenarios
^^^^^^^^^^^^^^^^^^^^^^

The :mod:`rally.benchmark.scenarios.keystone.basic` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.keystone.basic
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.benchmark.scenarios.keystone.utils` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.keystone.utils
    :members:
    :undoc-members:
    :show-inheritance:

The Nova Scenarios
^^^^^^^^^^^^^^^^^^

The :mod:`rally.benchmark.scenarios.nova.servers` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.nova.servers
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.benchmark.scenarios.nova.utils` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.nova.utils
    :members:
    :undoc-members:
    :show-inheritance:



Deploy engines
--------------

The :mod:`rally.deploy.engine` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.engine
    :members:
    :undoc-members:
    :show-inheritance:

The DevStack Engine
^^^^^^^^^^^^^^^^^^^

The :mod:`rally.deploy.engines.devstack` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.engines.devstack
    :members:
    :undoc-members:
    :show-inheritance:

The Dummy Engine
^^^^^^^^^^^^^^^^

The :mod:`rally.deploy.engines.existing` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.engines.existing
    :members:
    :undoc-members:
    :show-inheritance:


Database
--------

Represents a high level database abstraction interface which is used as persistent
storage for Rally. The storage operations implemented in driver abstractions.

The :mod:`rally.db.api` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.db.api
    :members:
    :undoc-members:
    :show-inheritance:

The SQLAlchemy Driver
^^^^^^^^^^^^^^^^^^^^^

The driver uses the sqlalchemy library and provides flexible range of supported
 SQL storages.

The :mod:`rally.db.sqlalchemy.api` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.db.sqlalchemy.api
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.db.sqlalchemy.models` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.db.sqlalchemy.models
    :members:
    :undoc-members:
    :show-inheritance:


Server providers
----------------

The :mod:`rally.deploy.serverprovider.provider` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.serverprovider.provider
    :members:
    :undoc-members:
    :show-inheritance:

The Dummy Server Provider
^^^^^^^^^^^^^^^^^^^^^^^^^

The :mod:`rally.deploy.serverprovider.providers.dummy` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.serverprovider.providers.existing
    :members:
    :undoc-members:
    :show-inheritance:

The OpenStack Server Provider
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :mod:`rally.deploy.serverprovider.providers.openstack` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.serverprovider.providers.openstack
    :members:
    :undoc-members:
    :show-inheritance:

The LXC Server Provider
^^^^^^^^^^^^^^^^^^^^^^^

The :mod:`rally.deploy.serverprovider.providers.lxc` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.serverprovider.providers.lxc
    :members:
    :undoc-members:
    :show-inheritance:

The Virsh Server Provider
^^^^^^^^^^^^^^^^^^^^^^^^^

The :mod:`rally.deploy.serverprovider.providers.virsh` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.deploy.serverprovider.providers.virsh
    :members:
    :undoc-members:
    :show-inheritance:


Objects
-------

Represents a high level abstraction of persistent database objects and
operations on them.

The :mod:`rally.objects.task` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.objects.task
    :members:
    :undoc-members:
    :show-inheritance:

The :mod:`rally.objects.deploy` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.objects.deploy
    :members:
    :undoc-members:
    :show-inheritance:


OpenStack Clients
-----------------

The :mod:`rally.osclients` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.osclients
    :members:
    :undoc-members:
    :show-inheritance:
