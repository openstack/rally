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

The easiest way to install Rally is by executing its `installation script
<https://raw.githubusercontent.com/stackforge/rally/master/install_rally.sh>`_

.. code-block:: none

    wget -q -O- https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh | bash
    # or using curl
    curl https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh | bash

The installation script will also check if all the software required
by Rally is already installed in your system; if run as **root** user
and some dependency is missing it will ask you if you want to install
the required packages.

By default it will install Rally in a virtualenv in ``~/rally`` when
ran as standard user, or install system wide when ran as root. You can
install Rally in a venv by using the option ``--target``:

.. code-block:: none

    ./install_rally.sh --target /foo/bar

You can also install Rally system wide by running script as root and
without ``--target`` option:

.. code-block:: none

    sudo ./install_rally.sh


Run ``./install_rally.sh`` with option ``--help`` to have a list of all
available options:

.. code-block:: node

     $ ./install_rally.sh --help
     Usage: install_rally.sh [options]

     This script will install rally either in the system (as root) or in a virtual environment.

    Options:
      -h, --help             Print this help text
      -v, --verbose          Verbose mode
      -s, --system           Instead of creating a virtualenv, install as
                             system package.
      -d, --target DIRECTORY Install Rally virtual environment into DIRECTORY.
                             (Default: $HOME/rally).
      -f, --overwrite        Remove target directory if it already exists.
      -y, --yes              Do not ask for confirmation: assume a 'yes' reply
                             to every question.
      -D, --dbtype TYPE      Select the database type. TYPE can be one of
                             'sqlite', 'mysql', 'postgres'.
                             Default: sqlite
      --db-user USER         Database user to use. Only used when --dbtype
                             is either 'mysql' or 'postgres'.
      --db-password PASSWORD Password of the database user. Only used when
                             --dbtype is either 'mysql' or 'postgres'.
      --db-host HOST         Database host. Only used when --dbtype is
                             either 'mysql' or 'postgres'
      --db-name NAME         Name of the database. Only used when --dbtype is
                             either 'mysql' or 'postgres'
      -p, --python EXE       The python interpreter to use. Default: /usr/bin/python.


**Notes:** the script will check if all the software required by Rally
is already installed in your system. If this is not the case, it will
exit, suggesting you the command to issue **as root** in order to
install the dependencies.

You also have to set up the **Rally database** after the installation is complete:

.. code-block:: none

   rally-manage db recreate


Rally with DevStack all-in-one installation
-------------------------------------------

It is also possible to install Rally with DevStack. First, clone the corresponding repositories:

.. code-block:: none

   git clone https://git.openstack.org/openstack-dev/devstack
   git clone https://github.com/openstack/rally

Then, configure DevStack to run Rally:

.. code-block:: none

   cp rally/contrib/devstack/lib/rally devstack/lib/
   cp rally/contrib/devstack/extras.d/70-rally.sh devstack/extras.d/
   cd devstack
   cp samples/local.conf local.conf
   echo "enable_service rally" >> local.conf

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
   mkdir rally_home
   sudo chown 65500 rally_home
   docker run -t -i -v ~/rally_home:/home/rally rallyforge/rally

You may want to save last command as an alias:

.. code-block:: none

   echo 'alias dock_rally="docker run -t -i -v ~/rally_home:/home/rally rallyforge/rally"' >> ~/.bashrc

After executing ``dock_rally`` alias, or ``docker run`` you got bash running inside container with
rally installed. You may do anything with rally, but you need to create db first:

.. code-block:: none

   user@box:~/rally$ dock_rally
   rally@1cc98e0b5941:~$ rally-manage db recreate
   rally@1cc98e0b5941:~$ rally deployment list
   There are no deployments. To create a new deployment, use:
   rally deployment create
   rally@1cc98e0b5941:~$

In case you have SELinux enabled and rally fails to create database, try
executing the following commands to put SELinux into Permissive Mode on the host machine.

.. code-block:: none

   $ sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config
   $ setenforce permissive

Rally currently has no SELinux policy, which is why it must be run in Permissive mode
for certain configurations. If you can help create an SELinux policy for Rally, please contribute!

More about docker: `https://www.docker.com/ <https://www.docker.com/>`_
