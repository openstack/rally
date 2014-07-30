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

.. _installation:

Installation
============


Rally setup
-----------

The simplest way to start using Rally is to install it together with OpenStack using DevStack. If you already have an existing OpenStack installation and/or don't want to install DevStack, then the preferable way to set up Rally would be to install it manually. Both types of installation are described below in full detail.

**Note: Running Rally on OSX is not advised as some pip dependencies will fail to install**.

Automated installation
^^^^^^^^^^^^^^^^^^^^^^

**NOTE: Please ensure that you have installed either the Python 2.6 or the Python 2.7 version in the system that you are planning to install Rally**.

The installation script of Rally supports 2 installation methods:

    * system-wide (default)
    * in a virtual environment using the virtualenv tool


On the target system, get the source code of Rally:

.. code-block:: none

   git clone https://git.openstack.org/stackforge/rally

**As root, or as a normal user using sudo**, execute the installation script. If you define the -v switch, Rally will be installed in a virtual environment, otherwise, it will be installed system-wide.

**Install system-wide**:

.. code-block:: none

   ./rally/install_rally.sh

**Or install in a virtual environment**:

.. code-block:: none

   ./rally/install_rally.sh -v

Now you are able to :ref:`use Rally <usage>`!

Rally with DevStack all in one installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To install Rally with DevStack, you should first clone the corresponding repositories and copy the files necessary to integrate Rally with DevStack:

.. code-block:: none

   git clone https://github.com/openstack-dev/devstack
   git clone https://github.com/stackforge/rally

To configure DevStack to run Rally:

.. code-block:: none

   cp rally/contrib/devstack/lib/rally devstack/lib/
   cp rally/contrib/devstack/extras.d/70-rally.sh devstack/extras.d/
   cd devstack
   echo "enable_service rally" >> localrc

Finally, run DevStack as usually:

.. code-block:: none

   ./stack.sh

And finally you are able to :ref:`use Rally <usage>`!


Manual installation
^^^^^^^^^^^^^^^^^^^

Prerequisites
"""""""""""""

Start with installing some requirements that Rally needs to be set up correctly. The specific requirements depend on the environment you are going to install Rally in:

**Ubuntu**

.. code-block:: none

   sudo apt-get update
   sudo apt-get install libpq-dev git-core python-dev libevent-dev libssl-dev libffi-dev libsqlite3-dev
   curl -o /tmp/get-pip.py https://raw.github.com/pypa/pip/master/contrib/get-pip.py
   sudo python /tmp/get-pip.py
   sudo pip install pbr

**CentOS**

.. code-block:: none

   sudo yum install gcc git-core postgresql-libs python-devel libevent-devel openssl-devel libffi-devel sqlite
   #install pip on centos:
   curl -o /tmp/get-pip.py https://raw.github.com/pypa/pip/master/contrib/get-pip.py
   sudo python /tmp/get-pip.py
   sudo pip install pbr

**VirtualEnv**

Another option is to install Rally in virtualenv; you should then install this package, create a virtualenv and activate it:

.. code-block:: none

   sudo pip install -U virtualenv
   virtualenv .venv
   . .venv/bin/activate  # NOTE: Make sure that your current shell is either bash or zsh (otherwise it will fail)
   sudo pip install pbr

Installing Rally
""""""""""""""""

The next step is to clone & install rally:

.. code-block: none

   git clone https://github.com/stackforge/rally.git && cd rally
   sudo python setup.py install

Now you are ready to configure Rally (in order for it to be able to use the database):

.. code-block:: none

   sudo mkdir /etc/rally
   sudo cp etc/rally/rally.conf.sample /etc/rally/rally.conf
   sudo vim /etc/rally/rally.conf
   # Change the "connection" parameter, For example to this:
   connection="sqlite:////a/path/here/rally.sqlite"

After the installation step has been completed, you need to create the Rally database:

.. code-block:: none

   rally-manage db recreate

And finally you are able to :ref:`use Rally <usage>`!


Running Rally's Unit Tests
--------------------------

Rally should be tested with tox, but is not compatible with the current version of tox, so install tox 1.6.1 then run it.

.. code-block:: none

   pip install 'tox<=1.6.1'
   tox
