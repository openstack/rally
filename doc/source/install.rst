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

=========================
Installation and upgrades
=========================

Every Rally release is published as Python packages on
`PyPI <https://pypi.org/project/rally/>`_ and as images on
`Docker Hub <https://hub.docker.com/u/xrally>`_.

From PyPI
---------

Rally needs Python :package:`requires-python | min` or newer.
To test an OpenStack cloud, add the OpenStack plugins:

.. tab-set::
   :sync-group: installer

   .. tab-item:: pip
      :sync: pip

      .. code-block:: console

         $ pip install rally
         $ pip install rally-openstack  # for OpenStack

   .. tab-item:: uv
      :sync: uv

      .. code-block:: console

         $ uv tool install rally
         $ uv tool install rally --with rally-openstack  # for OpenStack

Then create the database (see `Database`_ below):

.. code-block:: console

   $ rally db create

Rally runs without a configuration file. All the options you can set are
listed in :ref:`configuration`.

With Docker
-----------

``xrally/xrally`` has Rally with its own plugins; its tags are Rally
releases. ``xrally/xrally-openstack`` adds the OpenStack plugins; its tags
are rally-openstack releases. The image runs ``rally`` and already has a
database in ``/home/rally/.rally``; keep that directory in a volume so your
results outlive the container:

.. tab-set::
   :sync-group: image

   .. tab-item:: Rally
      :sync: rally

      .. parsed-literal::

         $ docker volume create rally
         $ docker run --rm -v rally:/home/rally/.rally xrally/xrally:|stable_release| env create --name local

   .. tab-item:: OpenStack
      :sync: openstack

      .. parsed-literal::

         $ docker volume create rally
         $ docker run --rm -v rally:/home/rally/.rally xrally/xrally-openstack:|openstack_release| env create --name local

The image keeps the Rally source tree, with all the sample tasks, in
``/rally/source`` (the OpenStack image adds rally-openstack's in
``/rally/xrally_openstack``). Do not mount anything over ``/rally``, or
these files are hidden.

How to mount a host directory instead of a volume, where the configuration
file is inside the container and how to build your own image on top are
described on the `image page <https://hub.docker.com/r/xrally/xrally>`_.

Database
--------

Rally keeps environments, tasks and verifications in a database. By default,
the database is an SQLite file, ``rally.sqlite`` in the system temporary
directory (for example, ``/tmp/rally.sqlite``), which many systems clear on
reboot. To keep your results, or to share them between several machines,
set another location or another database in the ``connection`` option of the
``[database]`` section of the configuration file (see :ref:`configuration`):

.. code-block:: ini

    [database]
    connection = postgresql+psycopg://user:password@db.example.com/rally

The option takes a
`SQLAlchemy URL <https://docs.sqlalchemy.org/en/20/core/engines.html#database-urls>`_.
For a database server, install the driver with an extra of the ``rally``
package and create an empty database; ``rally db create`` then creates the
tables in it.

.. list-table::
   :header-rows: 1

   * - Database
     - Extra
     - ``connection``
   * - SQLite (default)
     - none
     - ``sqlite:////home/user/.rally/rally.sqlite``
   * - MySQL or MariaDB
     - ``mysql``
     - ``mysql+pymysql://user:password@host/rally``
   * - PostgreSQL
     - ``postgres``
     - ``postgresql+psycopg://user:password@host/rally``

.. tab-set::
   :sync-group: installer

   .. tab-item:: pip
      :sync: pip

      .. code-block:: console

         $ pip install "rally[postgres]"

   .. tab-item:: uv
      :sync: uv

      .. code-block:: console

         $ uv tool install "rally[postgres]"

      ``uv tool install`` replaces the whole environment, so add
      ``--with rally-openstack`` if you use the OpenStack plugins.

The ``mysql`` extra installs :package:`extra mysql` and the ``postgres``
extra installs :package:`extra postgres`. These are the drivers Rally is
tested with, and the ``connection`` URLs above use them.

.. _upgrade:

Upgrades
--------

A new release may change the database schema. After you upgrade the package
or switch to a newer image, bring the database up to date; your data is
kept:

.. tab-set::
   :sync-group: installer

   .. tab-item:: pip
      :sync: pip

      .. code-block:: console

         $ pip install --upgrade rally
         $ rally db upgrade

   .. tab-item:: uv
      :sync: uv

      .. code-block:: console

         $ uv tool upgrade rally
         $ rally db upgrade

   .. tab-item:: Docker
      :sync: docker

      Run the upgrade with the new image and the same volume:

      .. parsed-literal::

         $ docker run --rm -v rally:/home/rally/.rally xrally/xrally:|stable_release| db upgrade

``rally db revision`` shows which schema version the database has.

.. warning::

   Rally cannot downgrade the database. Back it up before an upgrade if you
   may need to go back to the older release.

Changing the schema in Rally's code is covered in the
:rally-file:`developer notes on migrations <rally/common/db/migrations/README.rst>`.
