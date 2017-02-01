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

========================================================
HowTo migrate from Verification component 0.7.0 to 0.8.0
========================================================

.. note:: This document describes migration process from 0.7.0 to 0.8.0 Rally
    version. You can apply this instruction for migration to later versions,
    but check all references and release notes before trying to do it.


Verification Component was introduced long time ago even before the first Rally
release. It started as a small helper thing but became a big powerful tool.
Since it was not designed to all features that were implemented there later,
it contained a lot of workarounds and hacks.

New Verification Component, which we are happy to introduce, should fix all
architecture issues and improve user-experience. Unfortunately, fixing all
those obsolete architecture decisions could not be done in a
backward-compatible way, or it would produce much more workarounds. That is why
we decided to redesign the whole component in a clear way - remove old code and
write a new one from scratch.

Migration to New Verification Component should be simple and do not take too
much time. You can find description of made changes below.

.. contents::
  :depth: 2
  :local:

Reports
-------

We completely reworked verification reports and merged comparison to main
report. Now you can build one report for multiple number of verifications.

For more details follow :ref:`verification-reports`

Verification statuses
---------------------

+------------+------------+---------------------------------------------------+
| Old Status | New Status | Description                                       |
+============+============+===================================================+
| init       | init       | Initial state. It appears instantly after calling |
|            |            | ``rally verify start`` command before the actual  |
|            |            | run of verifier's tool.                           |
+------------+------------+---------------------------------------------------+
| running    |            | It was used right after checking status of        |
|            |            | verifier. It is redundant in terms of new design. |
+------------+------------+---------------------------------------------------+
| verifying  | running    | Identifies the process of tool execution.         |
+------------+------------+---------------------------------------------------+
| finished   | finished   | Previously, "finished" state was used for an      |
|            |            | identification of just finished verification. By  |
|            |            | "finished" meant that verification has any test   |
|            |            | result. Now it means that verification was        |
|            |            | executed and doesn't have failures, unexpected    |
|            |            | success or any kind of errors.                    |
|            +------------+---------------------------------------------------+
|            | failed     | Old purpose is an identification of "errors",     |
|            |            | situations when results are empty. The right use  |
|            |            | is an identification of finished verification     |
|            |            | with tests in "failed" and "uxsuccess"            |
|            |            | (unexpected success) statuses.                    |
+------------+------------+---------------------------------------------------+
| failed     | crashed    | Something went wrong while launching verification.|
+------------+------------+---------------------------------------------------+

The latest information about verification statuses you can find at
:ref:`verification_statuses`.

Command Line Interface
----------------------

You can find the latest information about Verification Component CLI here -
:ref:`rally-verify-cli-reference`.

Installing verifier
"""""""""""""""""""

Command for Rally 0.7.0 - `rally verify install
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-install>`_

.. code-block:: console

  $ rally verify install --deployment <uuid> --source <url> --version <vers> \
    --system-wide

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify create-verifier --type "tempest" --source <url> \
    --version <version> --system-wide --name <name>

Here you can find several important improvements:

1) Rally team introduced new entity - :ref:`verifiers`. Verifier stores all
   information about installed tool (i.e., source, version, system-wide) in a
   database. You do not need to transmit the same arguments into
   all ``rally verify`` commands as it was previously with ``--system-wide``
   flag.

2) You can use particular verifier for multiple deployments. ``--deployment``
   flag moved to ``rally verify start`` command. Also, you can run it
   simultaneously (checking in parallel different sets, different cloud, etc)

3) Verification Component can use not only Tempest for verifying system. Check
   :ref:`known-verifier-types` for full list of supported tools.

4) You can have unlimited number of verifiers.

Re-install verifier aka update
""""""""""""""""""""""""""""""

Command for Rally 0.7.0 - `rally verify reinstall
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-reinstall>`_

.. code-block:: console

  $ rally verify reinstall --deployment <uuid> --source <url> --version <vers> \
    --system-wide

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify update-verifier --id <id> --source <url> --version <vers> \
    --system-wide --no-system-wide --update-venv

Changes:

1) ``rally verify update-verifier`` doesn't require deployment id

2) You can switch between usage of system-wide installation and virtual
   environment.

3) You can update just virtual environment without cloning verifier code again

Uninstall
"""""""""

Command for Rally 0.7.0 - `rally verify uninstall
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-uninstall>`_

.. code-block:: console

  $ rally verify uninstall --deployment <uuid>

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify delete-verifier --id <id> --deployment-id <id> --force

Changes:

1) As it was mentioned before, Verifier doesn't have an alignment to any
   particular deployment, so deployment argument is optional now.
   If --deployment-id argument is specified only deployment specific data will
   be removed (i.e, configurations).

2) New --force flag for removing all verifications results for that verifier.

Installation extensions
"""""""""""""""""""""""

Command for Rally 0.7.0 - `rally verify installplugin
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-installplugin>`_

.. code-block:: console

  $ rally verify installplugin --deployment <uuid> --source <url> \
    --version <vers> --system-wide

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify add-verifier-ext --id <id> --source <url> --version <vers> \
    --extra-settings <data>

Changes:

1) --system-wide flag is removed. Rally checks the verifier information to
   identify where to install the extension - in a system-side way or use
   virtual environment.

2) New --extra-settings flag. In case of Tempest, it is redundant, but for
   other verifiers allows to transmit some extra installation settings for
   verifier extension.

Uninstall extensions
""""""""""""""""""""

Command for Rally 0.7.0 - `rally verify uninstallplugin
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-uninstallplugin>`_


.. code-block:: console

  $ rally verify uninstallplugin --deployment <uuid> --repo-name <repo_name> \
    --system-wide

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify delete-verifier-ext --id <id> --name <name>

Changes:

1) It is one more place where you do not need to pass --system-wide flag
   anymore.

2) --deployment flag is gone.

3) --repo-name is renamed to just --name.

List extensions
"""""""""""""""

Command for Rally 0.7.0 - `rally verify listplugins
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-listplugins>`_

.. code-block:: console

  $ rally verify listplugins --deployment <uuid> --system-wide

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify list-verifier-exts --id <id>

Changes:

1) No need to specify --system-wide flag.

2) --deployment flag is gone.

Discover available tests
""""""""""""""""""""""""

Command for Rally 0.7.0 - `rally verify discover
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-discover>`_

.. code-block:: console

  $ rally verify discover --deployment <uuid> --system-wide --pattern <pattern>

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify list-verifier-tests --id <id> --pattern <pattern>

Changes:

1) No need to specify --system-wide flag.

2) --deployment flag is gone.

Configuring
"""""""""""

Commands for Rally 0.7.0:

* The command for generating configs `rally verify genconfig
  <http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-genconfig>`_

  .. code-block:: console

    $ rally verify genconfig --deployment <uuid> --tempest-config <path> \
      --add-options <path> --override

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify configure-verifier --id <id> --deployment-id <uuid> \
    --extend <path/json/yaml> --override <path> --reconfigure --show

Changes:

1) The argument ``--override`` replaces old ``--tempest-config`` name. First
   of all, argument name "override" is a unified word without alignment to any
   tool. Also, it describes in the best way the meaning of the action: use
   client specified configuration file.

2) The argument ``--extend`` replaces old ``--add-options``. It accepts a path
   to config in INI format or JSON/YAML string. In future, it will be extended
   with the ability to specify a path to JSON/YAML file.

3) The argument ``--reconfigure`` replaces old ``--override``. It means that
   existing file will be ignored and new one will be used/created.

Show config
"""""""""""

Command for Rally 0.7.0 - `rally verify showconfig
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-showconfig>`_

.. code-block:: console

  $ rally verify showconfig --deployment <uuid>

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify configure-verifier --id <id> --deployment-id <uuid> --show

Changes:

  We do not have a separate command for that task.
  ``rally verify configure-verifier --show`` shows an existing configuration
  (if it exists) if ``--reconfigure`` argument is not specified.

Running verification
""""""""""""""""""""

Command for Rally 0.7.0 - `rally verify start
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-start>`_

.. code-block:: console

  $ rally verify start --deployment <uuid> --set <set_name> --regex <regex> \
    --load-list <path> --tests-file <path> --skip-list <path> \
    --tempest-config <path> --xfail-list <path> --system-wide \
    --concurrency <N> --failing --no-use

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify start --id <id> --deployment-id <uuid> --pattern <pattern> \
    --load-list <path> --skip-list <path> --xfail-list <path> \
    --concurrency <N> --no-use --detailed

Changes:

1) You need to pass verifier id

2) Arguments ``--set`` and ``--regex`` are merged in the new model to single
   ``--pattern`` argument. Name of tests set should be specified like
   ``--pattern set=<set_name>``. It was done to provide a way for each
   verifier to support custom arguments.

3) The argument ``--tests-file`` was deprecated in Rally 0.6.0 and
   we are ready to remove it.
4) Arguments ``--skip-list`` and ``--xfail-list`` accept path to file in
   JSON/YAML format. Content should be a dictionary, where keys are tests
   names (full name with id and tags) and values are reasons.
5) The argument ``--tempest-config`` is gone. Use
   ``rally verify configure-verifier --id <id> --deployment-id <uuid>
   --override <path>`` instead.
6) The argument ``--system-wide`` is gone like in most of other commands.
7) In case of specified ``--detailed`` arguments, traces of failed tests will
   be displayed (default behaviour in old verification design)

Show verification result
""""""""""""""""""""""""

Commands for Rally 0.7.0:

* The command for showing results of verification `rally verify show
  <http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-show>`_

  .. code-block:: console

    $ rally verify show --uuid <uuid> --sort-by <query> --detailed

* Separate command which calls ``rally verify show`` with hardcoded
  ``--detailed`` flag `rally verify detailed
  <http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-detailed>`_

  .. code-block:: console

    $ rally verify detailed --uuid <uuid> --sort-by <query>


Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify show --uuid <uuid> --sort-by <query> --detailed

Changes:

1) Redundant ``rally verify detailed`` command is removed

2) Sorting tests via ``--sort-by`` argument is extended to name/duration/status

Listing all verifications
"""""""""""""""""""""""""

Command for Rally 0.7.0 - `rally verify list
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-list>`_

.. code-block:: console

  $ rally verify list

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify list --id <id> --deployment-id <id> --status <status>

Changes:

  You can filter verifications by verifiers, by deployments and results
  statuses.

Importing results
"""""""""""""""""

Command for Rally 0.7.0 - `rally verify import
<http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-import>`_

.. code-block:: console

  $ rally verify import --deployment <uuid> --set <set_name> --file <path> --no-use

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify import --id <id> --deployment-id <uuid> --file <path> \
    --run-args <run_args> --no-use

Changes:

1) You need to specify verifier to import results for.

2) The argument ``--set`` is merged into unified ``--run-args``.

Building reports
""""""""""""""""

Commands for Rally 0.7.0:

* The command for building HTML/JSON reports of verification
  `rally verify results
  <http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-results>`_

  .. code-block:: console

    $ rally verify results --uuid <uuid> --html --json --output-file <path>

* The command for comparison two verifications `rally verify compare
  <http://rally.readthedocs.io/en/0.7.0/cli/cli_reference.html#rally-verify-compare>`_

  .. code-block:: console

    $ rally verify compare --uuid-1 <uuid_1> --uuid-2 <uuid_2> --csv --html \
      --json --output-file <output_file> --threshold <threshold>

Command since Rally 0.8.0:

.. code-block:: console

  $ rally verify report --uuid <uuid> --type <type> --to <destination> --open

Changes:

1) Building reports becomes pluggable. You can extend reporters types.
   See :ref:`verification-reports` for more details.

2) The argument ``--type`` expects type of report (HTML/JSON). There are no
   more separate arguments for each report type.

   .. hint:: You can list all supported types, executing ``rally plugin list
     --plugin-base VerificationReporter`` command.

3) Reports are not aligned to only local types, so the argument ``--to``
   replaces ``--output-file``. In case of HTML/JSON reports, it can include a
   path to the local file like it was previously or URL to some external system
   with credentials like ``https://username:password@example.com:777``.

4) The comparison is embedded into main reports and it is not limited by two
   verifications results. There are no reasons for the separate command for
   that task.

The End
"""""""

Have nice verifications!
