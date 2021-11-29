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

.. _install:

Installation process
====================

Automated installation
----------------------

The easiest way to install Rally is to use ``pip``. The following command will
install rally framework part of the latest released version.

.. code-block:: bash

    pip install rally

If you want to install package with rally plugins (for example, OpenStack
plugins), you can ignore the step of installation rally framework step since
it plugins package should include it as a dependency.

.. code-block:: bash

    # this should install Rally framework and Rally plugins for OpenStack
    # platform
    pip install rally-openstack

Rally & Docker
--------------

There are official docker images for Rally package and plugins. Check
`Docker Hub <https://hub.docker.com/r/xrally/>`_ for more details.
