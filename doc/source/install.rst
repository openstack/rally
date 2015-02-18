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

.. _install:

Installation
============

Automated installation
----------------------

.. code-block:: none

   git clone https://git.openstack.org/stackforge/rally
   ./rally/install_rally.sh

**Notes:** The installation script should be run as root or as a normal user using **sudo**. Rally requires either the Python 2.6 or the Python 2.7 version.


**Alternatively**, you can install Rally in a **virtual environment**:

.. code-block:: none

   git clone https://git.openstack.org/stackforge/rally
   ./rally/install_rally.sh -v



Rally with DevStack all-in-one installation
-------------------------------------------

It is also possible to install Rally with DevStack. First, clone the corresponding repositories:

.. code-block:: none

   git clone https://git.openstack.org/openstack-dev/devstack
   git clone https://github.com/stackforge/rally

Then, configure DevStack to run Rally:

.. code-block:: none

   cp rally/contrib/devstack/lib/rally devstack/lib/
   cp rally/contrib/devstack/extras.d/70-rally.sh devstack/extras.d/
   cd devstack
   echo "enable_service rally" >> localrc

Finally, run DevStack as usually:

.. code-block:: none

   ./stack.sh



Rally & Docker
--------------

First you need to install docker. Installing docker in ubuntu may be done by following:

.. code-block:: none

    $ sudo apt-get update
    $ sudo apt-get install docker.io
    $ sudo usermod -a -G docker `id -u -n` # add yourself to docker group

NOTE: re-login is required to apply users groups changes and actually use docker.

Pull docker image with rally:

.. code-block:: none

   $ docker pull rallyforge/rally

Or you may want to build rally image from source:

.. code-block:: none

    # first cd to rally source root dir
    docker build -t myrally .

Since rally stores local settings in user's home dir and the database in /var/lib/rally/database,
you may want to keep this directories outside of container. This may be done by the following steps:

.. code-block:: none

   cd
   mkdir rally_home rally_db
   docker run -t -i -v ~/rally_home:/home/rally -v ~/rally_db:/var/lib/rally/database rallyforge/rally

You may want to save last command as an alias:

.. code-block:: none

   echo 'alias dock_rally="docker run -t -i -v ~/rally_home:/home/rally -v ~/rally_db:/var/lib/rally/database rallyforge/rally"' >> ~/.bashrc

After executing ``dock_rally`` alias, or ``docker run`` you got bash running inside container with
rally installed. You may do anytnig with rally, but you need to create db first:

.. code-block:: none

   user@box:~/rally$ dock_rally
   rally@1cc98e0b5941:~$ rally-manage db recreate
   rally@1cc98e0b5941:~$ rally deployment list
   There are no deployments. To create a new deployment, use:
   rally deployment create
   rally@1cc98e0b5941:~$

More about docker: `https://www.docker.com/ <https://www.docker.com/>`_
