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

.. _configuration:

=============
Configuration
=============

Rally runs fine without any configuration file. You need one only when the
defaults do not fit you, for example when you want another database, custom
logging or a different task engine behaviour.

The file is called ``rally.conf`` and it is in the INI format that
`oslo.config <https://docs.openstack.org/oslo.config/latest/>`_ uses.

.. contents::
  :depth: 1
  :local:

Where Rally looks for the file
------------------------------

If you do not say which file to use, Rally checks these directories in this
order:

1. ``<sys.prefix>/etc/rally/``
2. ``~/.rally/``
3. ``/etc/rally/``

The first ``rally.conf`` it finds wins. The others are ignored, there is no
merging between them. If none of them exists, Rally just uses the built-in
defaults.

Pointing Rally at a file
------------------------

Use ``--config-file`` to name a file yourself:

.. code-block:: console

   $ rally --config-file ./my-rally.conf task start task.yaml

The option can be repeated. The files are merged option by option: when two
files set the same option, the later file wins, while an option set only in
an earlier file keeps its value. Once ``--config-file`` is given, the
``rally.conf`` from the directories above is not read.

Use ``--config-dir`` to point at a directory. Rally reads every ``*.conf``
file in it in alphabetical order and merges them the same way. These files
are read after all the ``--config-file`` ones, so they win over them. Unlike
``--config-file``, it does not replace the ``rally.conf`` found in the
directories above, the directory is merged on top of it.

Both are global options, so they go **before** the category:

.. code-block:: console

   $ rally --config-file ./my-rally.conf task start ...   # works
   $ rally task start --config-file ./my-rally.conf ...   # No such option

See :ref:`cli-reference` for the rest of the global options.

Available options
-----------------

All options with their descriptions and default values are listed in the
:rally-file:`sample configuration file <etc/rally/rally.conf.sample>`:

.. literalinclude:: ../../etc/rally/rally.conf.sample
   :language: ini
