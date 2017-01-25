..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/rally/+spec/awesome-thing should be named
 awesome-thing.rst .  Please do not delete any of the sections in this
 template.  If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://sphinx-doc.org/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html

===============================
Refactor Verification Component
===============================

Rally Verification was introduced long time ago as an easy way to launch
Tempest. It allows to manage(install, uninstall, configure and etc),
launch Tempest and process the results(store, compare, displaying in different
formats).

There is a lot of code related to Verification which can be used not only for
Tempest. Since `rally verify` was implemented to launch subunit-based
applications(Tempest is a such tool), our code is ready to launch whatever we
want subunit-frameworks by changing only one var - path to tests.

Problem description
===================

Rally is a good framework for any kind of testing (performance, functional and
etc), so it is pretty sad when we have a lot of hardcode and binding to
specific application.

* non-pluggable architecture

  Most of Rally components (for example Task or Deployment) are pluggable. You
  can easily extend Rally framework for such components. But we cannot say the
  same about Verification.

* subunit-trace

  ``subunit-trace`` library is used to display the live progress and summary at
  user-friendly way for each launch of Verification.
  There are several issues across this library:

  1. It is Tempest requirements.

     It is second time when Rally Verification component uses dependency
     from Tempest. ``tools/colorizer.py`` was used from Tempest repo
     before ``subunit-trace``. This script was removed from Tempest which led
     to breakage of whole Verification stuff.
     Also, ``rally verify install`` supports ``--source`` option for installing
     Tempest from non-default repos which can miss ``subunit-trace``
     requirement.

  2. Bad calculation(for example, skip of whole TestCase means 1 skipped test)

* Code duplication

  To simplify usage of Tempest, it is required to check existence of images,
  roles, networks and other resources. While implementing these checks, we
  re-implemented ... "Context" class which is used in Tasks.
  It was called TempestResourcesContext.

* Inner storage based on deployment

  In case of several deployments and one type of verifier(one repo), Rally
  creates several directories in ``~/.rally/tempest`` (``for-tempest-<uuid>``
  where <uuid> is a UUID of deployment). Each of these directories will
  include same files. The difference only in config files which can be stored
  wherever we want.
  Also, we have one more directory with the same data - cache directory
  (``~/.rally/tempest/base``).

* Word "Tempest" hardcoded in logging, help messages, etc.

Proposed change
===============

Most of subunit-based frameworks can be launched in the same way, but they can
accept different arguments, different setup steps and so on.

.. note:: In further text, we will apply labels "old" for code which was
  implemented before this spec and "new" for proposed change. Also, all
  references for old code will be linked to `0.3.3`__ release which is latest
  release at the time of writing this spec.

__ http://rally.readthedocs.org/en/0.3.3/release_notes/archive/v0.3.3.html

Declare base Verification entities
----------------------------------

Lets talk about all entities which represents Verification.

Old model
~~~~~~~~~

Old implementation uses only one entity - results of a single verification
launch.

**DB Layer**

* `Verification`__

  It represents a summary of a single verification launch results. Also, it
  is linked to full results (see next entity - VerificationResult).

__ https://github.com/openstack/rally/blob/0.3.3/rally/common/db/sqlalchemy/models.py#L186

* `VerificationResult`__

  The full results of a single launch.

  Since support of migrations was added
  recently, not all places are cleared yet, so ``VerificationResults`` can
  store results in two formats(old and current format). It would be nice to
  fix it and support only 1 format.

__ https://github.com/openstack/rally/blob/0.3.3/rally/common/db/sqlalchemy/models.py#L217

**Object layer**

It is a bad practise to provide an access to db stuff directly and we don't do
that. ``rally.common.objects`` layer was designed to hide all db related stuff.

* `Verification`__

  Just represents results.

__ https://github.com/openstack/rally/blob/0.3.3/rally/common/objects/verification.py#L28

New model
~~~~~~~~~

We want to support different verifiers and want to identify them, so let's
declare three entities:

* **Verifier type**. The name of entity is a description it self. Each type
  should be represented by own plugin which implements interface for
  verification tool. For example, Tempest, Gabbi should be such types.

* **Verifier**. An instance of ``verifier type``. I can be described with
  following options:

  * *source* - path to git repository of tool.

  * *system-wide* - whether or not to use the local env instead of virtual
    environment when installing verifier.

  * *version* - branch, tag or hash of commit to install verifier from. By
    default it is "master" branch.

* **Verification Results**. Result of a single launch.


**DB Layer**

* **Verifier**. We should add one more table to store different verifiers. New
  migration should be added, which check existence verification launches and
  create "default" verifier(type="Tempest", source="n/a") and map all of
  launches to it.

  .. code-block::

      class Verifier(BASE, RallyBase):
          """Represent a unique verifier."""

          __tablename__ = "verifiers"
          __table_args__ = (
              sa.Index("verification_uuid", "uuid", unique=True),
          )

          id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
          uuid = sa.Column(sa.String(36), default=UUID, nullable=False)

          deployment_uuid = sa.Column(
              sa.String(36),
              sa.ForeignKey(Deployment.uuid),
              nullable=False,
          )

          name = sa.Column(sa.String(255), unique=True)
          description = sa.Column(sa.String(1000))

          status = sa.Column(sa.Enum(*list(consts.VerifierStatus),
                             name="enum_verifier_status"),
                             default=consts.VerifierStatus.INIT,
                             nullable=False)
          started_at = sa.Column(sa.DateTime)
          updated_at = sa.Column(sa.DateTime)

          type = sa.Column(sa.String(255), nullable=False)
          settings = info = sa.Column(
              sa_types.MutableJSONEncodedDict,
              default={"system-wide": False,
                       "source": "n/a"},
              nullable=False,
          )

* `Verification`__

  It should be extended with a link to Verifier.

* `VerificationResult`__

  We can leave it as it is.


Move storage from deployment depended logic to verifier
-------------------------------------------------------

Old structure of ``~/.rally/tempest`` dir:

.. code-block:: yaml

  base:
    tempest_base-<hash>:
      # Cached Tempest repository
      tempest:
        api
        api_schema
        cmd
        ...
      ...
      requirements.txt
      setup.cfg
      setup.py
      ...
  for-deployment-<uuid>:
    # copy-paste of tempest_base-<hash> + files and directories listed below
    .venv           # Directory for virtual environment: exists if user didn't
                    # specify ``--system-wide`` argument while tempest
                    # installation (``rally verify install`` command).
    tempest.conf    # Only this file is unique for each deployment. It stores
                    # Tempest configuration.
    subunit.stream  # Temporary result-file produced by ``rally verify start``.

As you can see there are a lot of copy-pasted repositories and little unique
data.

New structure(should be located in ``~/.rally/verifiers``):

.. code-block:: yaml

  verifier-<uuid>:
    # Storage for unique verifier. <uuid> is a uuid of verifier.
    repo:
      # Verifier code repository. It is same for all deployments. Also one
      # virtual environment can be used across all deployment too.
      ...
    for-deployment-<uuid>:
      # Folder to store unique for deployment data. <uuid> is a deployment uuid
      # here. Currently we have only configuration file to store, but lets
      # reserve place to store more data.
      settings.conf
      ...

Each registered verifier is a unique entity for Rally and can be used by all
deployments. If there is deployment specific data(for example, configuration
file) required for verifier, it should be stored separately from verifier.

Command line interface
----------------------

`rally verify` commands are not so hardcoded as other parts of Verification
component, but in the same time they are not flexible.

Old commands:

.. code-block:: none

  compare         Compare two verification results.
  detailed        Display results table of a verification with detailed errors.
  discover        Show a list of discovered tests.
  genconfig       Generate Tempest configuration file.
  import          Import Tempest tests results into the Rally database.
  install         Install Tempest.
  list            List verification runs.
  reinstall       Uninstall Tempest and install again.
  results         Display results of a verification.
  show            Display results table of a verification.
  showconfig      Show configuration file of Tempest.
  start           Start verification (run Tempest tests).
  uninstall       Remove the deployment's local Tempest installation.
  use             Set active verification.

There is another problem of old CLI. Management is splitted across all commands
and you can do the same things via different commands. Moreover, you can
install Tempest in virtual environment via ``rally verify install`` and use
``--system-wide`` option in ``rally verify start``.

Lets provide more strict CLI. Something like:

.. code-block:: none

  list-types

  create-verifier
  delete-verifier
  list-verifiers
  update-verifier
  extend-verifier
  use-verifier

  configure
  discover
  start

  compare
  export
  import
  list
  show
  use

list-types
~~~~~~~~~~

Verifiers types should be implemented on base Rally plugin mechanism. It allow
to not create types manually, Rally will automatically load them and user will
need only interface to list them.

create-verifier
~~~~~~~~~~~~~~~

Just creates a new verifier based on type.

Example:

.. code-block:: bash

  $ rally verify create-verifier tempest-mitaka --type tempest --source "https://git.openstack.org/openstack/tempest" --version "10.0.0" --system-wide

This command should process next steps:

1. Clone Tempest repository from "https://git.openstack.org/openstack/tempest";
2. Call ``git checkout 10.0.0``;
3. Check that all requirements from requirements.txt are satisfied;
4. Put new verifier as default one

Also, it would be nice to store verifier statuses like "Init", "Ready-to-use",
"Failed", "Updating".

delete-verifier
~~~~~~~~~~~~~~~

Deletes verifier virtual environment(if it was created), repository, deployment
specific files(configuration files).

Also, it will remove verification results produced by this verifier.

list-verifiers
~~~~~~~~~~~~~~

List all available verifiers.

update-verifier
~~~~~~~~~~~~~~~

This command gives ability to update git repository(``git pull`` or
``git checkout``) or start/stop using virtual environment.

Also, configuration file can be update via this interface.

extend-verifier
~~~~~~~~~~~~~~~

Verifier can have an interface to extend itself. For example, Tempest supports
plugins. For verifiers which do not support any extend-mechanism, lets print
user-friendly message.

use-verifier
~~~~~~~~~~~~

Choose the default verifier.

configure
~~~~~~~~~

An interface to configure verifier for an specific deployment.

Usage examples:

.. code-block:: bash

  # At this step we assume that configuration file was not created yet.
  # Create configuration file and show it.
  $ rally verify configure

  # Configuration file already exists, so just show it.
  $ rally verify configure

  # Recreate configuration file and show it
  $ rally verify configure --renew

  # Recreate configuration file using predefined configuration options and
  # show it.
  # via json:
  $ rally verify configure --renew \
  > --options '{"section_name": {"some_key": "some_var"}}'

  # via config file, which can be json/yaml or ini format:
  $ rally verify configure --renew --options ~/some_file.conf

  # Replace configuration file by another file and show it
  $ rally verify configure --replace ./some_config.conf

Also, we can provide ``--silent`` option to disable ``show`` action.

discover
~~~~~~~~

Discover and list tests.

start
~~~~~

Start verification. Basically, there is no big difference between launching
different verifiers.

Current arguments: ``--set``, ``--regex``, ``--tests-file``, ``xfails-file``,
``--failing``.

Argument ``--set`` is specific for Tempest. Each verifier can have specific
search arguments. Lets introduce new argument ``--filter-by``. In this case,
set_name for Tempest can be specified like ``--filter-by set=smoke``.

compare
~~~~~~~

Compare two verification results.

export
~~~~~~

Part of `Export task and verifications into external services`__ spec

__ https://github.com/openstack/rally/blob/0.3.2/doc/specs/in-progress/task_and_verification_export.rst

import
~~~~~~

Import outer results in Rally database.

list
~~~~

List all verifications results.

show
~~~~

Show verification results in different formats.

Refactor base classes
---------------------

Old implementation includes several classes:

* Main class **Tempest**. This class combines manage and launch logic.

  .. code-block:: python

    # Description of a public interface(all implementation details are skipped)
    class Tempest(object):

        base_repo_dir = os.path.join(os.path.expanduser("~"),
                                     ".rally/tempest/base")

        def __init__(self, deployment, verification=None,
                     tempest_config=None, source=None, system_wide=False):
            pass

        @property
        def venv_wrapper(self):
            """This property returns the command for activation virtual
            environment. It is hardcoded on tool from Tempest repository:

            https://github.com/openstack/tempest/blob/10.0.0/tools/with_venv.sh

            We should remove this hardcode in new implementation."""

        @property
        def env(self):
            """Returns a copy of environment variables with addition of pathes
            to tests"""

        def path(self, *inner_path):
            """Constructs a path for inner files of
                            ~/.rally/tempest/for-deployment-<uuid>
            """

        @property
        def base_repo(self):
            """The structure of ~/.rally/tempest dir was changed several times.
            This method handles the difference."""

        def is_configured(self):
            pass

        def generate_config_file(self, override=False):
            """Generate configuration file of Tempest for current deployment.
            :param override: Whether or not to override existing Tempest
                             config file
            """

        def is_installed(self):
            pass

        def install(self):
            """Creates local Tempest repo and virtualenv for deployment."""

        def uninstall(self):
            """Removes local Tempest repo and virtualenv for deployment."""

        def run(self, testr_args="", log_file=None, tempest_conf=None):
            """Run Tempest."""

        def discover_tests(self, pattern=""):
            """Get a list of discovered tests.
            :param pattern: Test name pattern which can be used to match
            """

        def parse_results(self, log_file=None, expected_failures=None):
            """Parse subunit raw log file."""

        def verify(self, set_name, regex, tests_file, expected_failures,
                   concur, failing):
            """Launch verification and save results in database."""

        def import_results(self, set_name, log_file):
            """Import outer subunit-file to Rally database"""

        def install_plugins(self, *args, **kwargs):
            """Install Tempest plugin."""

* class ``TempestConfig`` was designed to obtain all required settings from
  OpenStack public API and generate configuration file. It has not-bad
  interface (just ``init`` and ``generate`` public methods), but implementation
  can be better(init method should not start obtaining data).

* class ``TempestResourcesContext`` looks like context which we have for Task
  component.

``TempestConfig`` and ``TempestResourcesContext`` are help classes and in new
implementation they will be optional.

New implementation should looks like:

* ``VerifierManager``. It is a main class which represents a type of Verifier
  and provide an interface for all management stuff(i.e. install, update,
  delete). Also, it should be an entry-point for configuration and
  extend-mechanism which are optional.

* ``VerifierLauncher``. It takes care about deployment's task - preparation
  and launching verification and so on.

* ``VerifierContext``. The inheritor of rally.task.context.Context class with
  hardcoded "hidden=True" value, since it should be inner helper class.

* ``VerifierSettings``. Obtains required data from public APIs and constructs
  deployment specific configuration files for Verifiers.

Proposed implementation will be described below in `Implementation`_ section.

Remove dependency from external libraries and scripts
-----------------------------------------------------

Currently our verification code has two redundant dependencies:

* subunit-trace
* <tempest repo>/tools/with_venv.sh

subunit-trace
~~~~~~~~~~~~~

It should not be a hard task to remove this dependency. With small
modifications ``rally.common.io.subunit.SubunitV2StreamResult`` can print live
progress. Also, we an print summary info based on parsed results.

with_venv.sh script
~~~~~~~~~~~~~~~~~~~

It is tempest in-tree script. Its logic is too simple - just activate virtual
environment and execute transmitted cmd in it. I suppose that we can rewrite
this script in python and put it to Verification component.

Alternatives
------------

Stop development of Rally Verification.

Implementation
==============

Implementation details
----------------------

Below you can find an example of implementation. It contains some
implementation details and notes for future development.

.. note:: Proposed implementation is not ideal and not finished. It should be
    reviewed without nits.

rally.common.objects.Verifier
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Basically, it will be the same design as `rally.common.objects.Verification`__.
There is no reasons to store old class. ``Verifier`` interface should be
enough.

__ https://github.com/openstack/rally/blob/0.3.3/rally/common/objects/verification.py#L28

VerifierManager
~~~~~~~~~~~~~~~

.. code-block:: python

  import os
  import shutil
  import subprocess

  from rally.common.plugin import plugin


  class VerifierManager(plugin.Plugin):

      def __init__(self, verifier):
          """Init manager

          :param verifier: `rally.common.objects.Verifier` instance
          """
          self.verifier = self.verifier

      @property
      def home_dir(self):
          """Home directory of verifier"""
          return "~/.rally/verifier-%s" % self.verifier.id

      @property
      def repo_path(self):
          """Path to local repository"""
          return os.path.join(self.home_dir, "repo")

      def mkdirs(self):
          """Create all directories"""
          if not self.home_dir:
              os.mkdir(self.home_dir)
          deployment_path = os.path.join(
              base_path, "for-deployment-%s" % self.deployment.id))
          if not deployment_path:
              os.mkdir(deployment_path)

      def _clone(self):
          """Clone and checkout git repo"""
          self.mkdirs()
          source = self.verifier.source or self._meta_get("default_repo")
          subprocess.check_call(["git", "clone", source, self.repo_path])

          version = self.verifier.version or self._meta_get("default_version")
          if version:
              subprocess.check_call(["git", "checkout", version],
                                    cwd=self.repo_path)

      def _install_virtual_env(self):
          """Install virtual environment and all requirement in it."""
          if os.path.exists(os.path.join(self.repo_path, ".venv")):
              # NOTE(andreykurilin): It is necessary to remove old env while
              #                      processing update action
              shutils.rmtree(os.path.join(self.repo_path, ".venv"))

          # TODO(andreykurilin): make next steps silent and print output only
          #                      on failure or debug
          subprocess.check_output(["virtualenv", ".venv"], cwd=self.repo_path)
          # TODO: install verifier and its requirements here.

      def install(self):
          if os.path.exists(self.home_dir):
              # raise a proper exception
              raise Exception()
          self._clone()
          if system_wide:
              # There are several ways to check requirements. It can be done
              # at least via two libraries: `pip`, `pkgutils`. The code below
              # bases on `pip`, but it can be changed for better solution while
              # implementation.
              import pip

              requirements = set(pip.req.parse_requirements(
                                     "%s/requirements.txt" % self.repo_path,
                                     session=False))
              installed_packages = set(pip.get_installed_distributions())
              missed_packages = requirements - installed_packages
              if missed_packages:
                  # raise a proper exception
                  raise Exception()
          else:
              self._install_virtual_env()


      def delete(self):
          """Remove all"""
          shutils.rmtree(self.home_dir)

      def update(self, update_repo=False, version=None, update_venv=False):
          """Update repository, version, virtual environment."""
          pass

      def extend(self, *args, **kwargs):
          """Install verifier extensions.

          .. note:: It is an optional interface, so it raises UnsupportedError
              by-default. If specific verifier needs this interface, it should
              just implement it.
          """
          raise UnsupportedAction("%s verifier is not support extensions." %
                                  self.get_name())

For example, the implementation of verifier for Tempest will need to
implement only one method ``extend``:

.. code-block:: python

  @configure("tempest_manager",
             default_repo="https://github.com/openstack/tempest",
             default_version="master",
             launcher="tempest_launcher")
  class TempestManager(VerifierManager):

      def extend(self, *args, **kwargs):
          """Install tempest-plugin."""
          pass

VerifierLauncher
~~~~~~~~~~~~~~~~

.. code-block:: python

  import os
  import subprocess

  from rally.common.io import subunit_v2
  from rally.common.plugin import plugin


  class EmptyContext(object):
      """Just empty default context."""

      def __init__(self, verifier, deployment):
          pass

      def __enter__(self):
          return

      def __exit__(self, exc_type, exc_value, exc_traceback):
          # do nothing
          return


  class VerifierLauncher(plugin.Plugin):
      def __init__(self, deployment, verifier):
          """Init launcher

          :param deployment: `rally.common.objects.Deployment` instance
          :param verifier: `rally.common.objects.Verifier` instance
          """
          self.deployment = deployment
          self.verifier = self.verifier

      @property
      def environ(self):
          """Customize environment variables."""
          return os.environ.copy()

      @property
      def _with_venv(self):
          """Returns arguments for activation virtual environment if needed"""
          if self.verifier.system_wide:
              return []
          # FIXME(andreykurilin): Currently, we use "tools/with_venv.sh" script
          #   from Tempest repository. We should remove this dependency.
          return ["activate-venv"]

      @property
      def context(self):
          ctx = self._meta_get("context")
          if ctx:
              ctx = VerifierContext.get(ctx)
          return ctx or EmptyContext

      def configure(self, override=False):
          # by-default, verifier doesn't support this method
          raise NotImplementedError

      def configure_if_necessary(self):
          """Check existence of config file and create it if necessary."""
          pass

      def transform_kwargs(self, **kwargs):
          """Transform kwargs into the list of testr arguments."""
          args = ["--subunit", "--parallel"]
          if kwargs.get("concurrency"):
              args.append("--concurrency")
              args.append(kwargs["concurrency"])
          if kwargs.get("re_run_failed"):
              args.append("--failing")
          if kwargs.get("file_with_tests"):
              args.append("--load-list")
              args.append(os.path.abspath(kwargs["file_with_tests"]))
          if kwargs.get("regexp"):
              args.append(kwargs["regexp"])
          return args

      def run(self, regexp=None, concurrency=None, re_run_failed=False,
              file_with_tests=None):
          self.configure_if_necessary()

          cmd = [self._with_venv, "testr", "run"]
          cmd.extend(self.transform_kwargs(
              regexp=regexp, concurrency=concurrency,
              re_run_failed=re_run_failed, file_with_tests=file_with_tests))

          with self.context(self.deployment, self.verifier):
              verification = subprocess.Popen(
                  cmd, env=self.environ(),
                  cwd=self.verifier.manager.home_dir,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.stdout)
              results = subunit_v2.parse(verification.stdout, live=True)
              verification.wait()
          return results

An example of VerifierLauncher for Tempest:

.. code-block:: python

  @configure("tempest_verifier")
  class TempestLauncher(VerifierLauncher):

      @property
      def configfile(self):
          return os.path.join(self.verifier.manager.home_dir,
                              "for-deployment-%s" % self.deployment.id,
                              "tempest.conf")

      @property
      def environ(self):
          """Customize environment variables."""
          env = super(TempestLauncher, self).environ

          env["TEMPEST_CONFIG_DIR"] = os.path.dirname(self.configfile)
          env["TEMPEST_CONFIG"] = os.path.basename(self.configfile)
          env["OS_TEST_PATH"] = os.path.join(self.verifier.manager.home_dir,
                                             "tempest", "test_discover")
          return env

      def configure(self, override=False):
          if os.path.exists(self.configfile):
              if override:
                  os.remove(self.configfile)
              else:
                  raise AlreadyConfiguredException()
          # Configure Tempest.

      def configure_if_necessary(self):
          try:
              self.configure()
          except AlreadyConfiguredException:
              # nothing to do. everything is ok
              pass

      def run(self, set_name, **kwargs):
          if set_name == "full":
              pass
          elif set_name in consts.TempestTestsSets:
              kwargs["regexp"] = set_name
          elif set_name in consts.TempestTestsAPI:
              kwargs["regexp"] = "tempest.api.%s" % set_name

          super(TempestLauncher, self).run(**kwargs)

VerifierContext
~~~~~~~~~~~~~~~

.. code-block:: python

  from rally import osclients
  from rally.task import context


  class VerifierContext(context.Context):

      def __init__(self, **ctx):
          super(VerifierContext, self).__init__(ctx)
          # There are no terms "task" and "scenario" in Verification
          del self.task
          del self.map_for_scenario
          self.clients = osclients(self.context["deployment"].credentials)

      @classmethod
      def _meta_get(cls, key, default=None):
          # It should be always hidden
          if key == "hidden":
              return True
          return super(VerifierContext, cls)._meta_get(key, default)


Example of context for Tempest:

.. code-block:: python

  @configure("tempest_verifier_ctx")
  class TempestContext(VerifierContext):

      def __init__(self, **kwargs):
          super(TempestContext, self).__init__(**kwargs)
          self.clients = osclients(self.context["deployment"].credentials)

      def setup(self):
          # create required resources and save them to self.context
          pass

      def cleanup(self):
          # remove created resources
          pass


Assignee(s)
-----------

Primary assignee:
  Andrey Kurilin <andr.kurilin@gmail.com>

Work Items
----------

1) CLI and API related changes.

   Lets provide new interface as soon as possible, even if some APIs will not
   be implemented. As soon we deprecate old interface as soon we will be able
   to remove it and provide clear new one.

2) Provide base classes for Verifiers

3) Rewrite Tempest verifier based on new classes.


Dependencies
============

None
