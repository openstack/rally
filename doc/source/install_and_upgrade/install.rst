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

Installation process
====================

Automated installation
----------------------

The easiest way to install Rally is by executing its `installation script`_

.. code-block:: bash

    wget -q -O- https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh | bash
    # or using curl
    curl https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh | bash

The installation script will also check if all the software required
by Rally is already installed in your system; if run as **root** user
and some dependency is missing it will ask you if you want to install
the required packages.

By default it will install Rally in a virtualenv in ``~/rally`` when
run as standard user, or install system wide when run as root. You can
install Rally in a **venv** by using the option ``--target``:

.. code-block:: bash

    ./install_rally.sh --target /foo/bar

You can also install Rally system wide by running script as root and
without ``--target`` option:

.. code-block:: bash

    sudo ./install_rally.sh


Run ``./install_rally.sh`` with option ``--help`` to have a list of all
available options:

.. code-block:: console

     $ ./install_rally.sh --help
     Usage: install_rally.sh [options]

     This script will install rally either in the system (as root) or in a virtual environment.

    Options:
      -h, --help             Print this help text
      -v, --verbose          Verbose mode
      -s, --system           Install system-wide.
      -d, --target DIRECTORY Install Rally virtual environment into DIRECTORY.
                             (Default: /root/rally if not root).
      --url                  Git repository public URL to download Rally from.
                             This is useful when you have only installation script and want
                             to install Rally from custom repository.
                             (Default: https://git.openstack.org/openstack/rally).
                             (Ignored when you are already in git repository).
      --branch               Git branch name, tag (Rally release), commit hash, ref, or other
                             tree-ish to install. (Default: master)
                             Ignored when you are already in git repository.
      -f, --overwrite        Deprecated. Use -r instead.
      -r, --recreate         Remove target directory if it already exist.
                             If neither '-r' nor '-R' is set default behaviour is to ask.
      -R, --no-recreate      Do not remove target directory if it already exist.
                             If neither '-r' nor '-R' is set default behaviour is to ask.
      -y, --yes              Do not ask for confirmation: assume a 'yes' reply
                             to every question.
      -D, --dbtype TYPE      Select the database type. TYPE can be one of
                             'sqlite', 'mysql', 'postgresql'.
                             Default: sqlite
      --db-user USER         Database user to use. Only used when --dbtype
                             is either 'mysql' or 'postgresql'.
      --db-password PASSWORD Password of the database user. Only used when
                             --dbtype is either 'mysql' or 'postgresql'.
      --db-host HOST         Database host. Only used when --dbtype is
                             either 'mysql' or 'postgresql'
      --db-name NAME         Name of the database. Only used when --dbtype is
                             either 'mysql' or 'postgresql'
      -p, --python EXE       The python interpreter to use. Default: /usr/bin/python.
      --develop              Install Rally with editable source code try. (Default: false)
      --no-color             Disable output coloring.


**Notes:** the script will check if all the software required by Rally
is already installed in your system. If this is not the case, it will
exit, suggesting you the command to issue **as root** in order to
install the dependencies.

You also have to set up the **Rally database** after the installation is
complete:

.. code-block:: bash

   rally db recreate

.. include:: ../../../devstack/README.rst

Rally & Docker
--------------

First you need to install Docker; Docker supplies `installation
instructions for various OSes`_.

You can either use the official Rally Docker image, or build your own
from the Rally source. To do that, change directory to the root directory of
the Rally git repository and run:

.. code-block:: bash

    docker build -t myrally .

If you build your own Docker image, substitute ``myrally`` for
``xrally/xrally-openstack`` in the commands below.

The Rally Docker image is configured to store the database in the user's home
directory - ``/home/rally/data/rally.sqlite``. For persistence of these data,
you may want to keep this directory outside of the container. This may
be done via 2 ways:

* use a docker image. In this case you do not need to initialize the database

  .. code-block:: bash

    docker volume create --name rally_volume
    docker run -v rally_volume:/home/rally/data xrally/xrally-openstack deployment create --name "foo"

* mount the directory to container. In this case, there is ability to transmit
  task files inside the container, but you will need to initialize the database
  by yourself

  .. code-block:: bash

    sudo mkdir /var/lib/rally_container
    sudo chown 65500 /var/lib/rally_container
    docker run -v /var/lib/rally_container:/home/rally/data xrally/xrally-openstack db create
    docker run -v /var/lib/rally_container:/home/rally/data xrally/xrally-openstack deployment create --name "foo"

  .. note::

    In order for the volume to be accessible by the Rally user
    (uid: 65500) inside the container, it must be accessible by UID
    65500 *outside* the container as well, which is why it is created
    in ``/var/lib/rally_container``. Creating it in your home directory is only
    likely to work if your home directory has excessively open
    permissions (e.g., ``0755``), which is not recommended.

You can find all task samples, docs and pre created tasks at /home/rally/source
In case you have SELinux enabled and Rally fails to create the
database, try executing the following commands to put SELinux into
Permissive Mode on the host machine

.. code-block:: bash

   sed -i 's/SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config
   setenforce permissive

Rally currently has no SELinux policy, which is why it must be run in
Permissive mode for certain configurations. If you can help create an
SELinux policy for Rally, please contribute!

More about docker: https://www.docker.com/

.. references:

.. _installation script: https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh
.. _installation instructions for various OSes: https://docs.docker.com/install/
