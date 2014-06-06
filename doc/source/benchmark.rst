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

.. _benchmark:

The Benchmark Layer
===================

Represents a core of benchmarking, a base class of scenarios and scenarios.
The core itself consists of an engine that performs a benchmark and a runner of
scenarios.

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

The Benchmark Scenarios
=======================

There is a set of scenarios that available for benchmarking. Scenarios was
decomposed per a service.

The :mod:`rally.benchmark.scenarios.utils` Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: rally.benchmark.scenarios.utils
    :members:
    :undoc-members:
    :show-inheritance:

The Cinder Scenarios
--------------------

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
----------------------

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
------------------

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
