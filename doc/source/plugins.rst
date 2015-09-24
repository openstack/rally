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

.. _plugins:

Rally Plugins
=============

Rally Plugin Reference
---------------------------

Rally has a plugin oriented architecture - in other words Rally team is trying
to make all places of code pluggable. Such architecture leds to the big amount
of plugins. :ref:`Rally Plugins Reference page <plugin_reference>` contains a
full list with detailed descriptions of all official Rally plugins.


How plugins work
----------------

Rally provides an opportunity to create and use a **custom benchmark
scenario, runner or context** as a **plugin**:

.. image:: ./images/Rally-Plugins.png
   :align: center

Placement
---------

Plugins can be quickly written and used, with no need to contribute
them to the actual Rally code. Just place a python module with your
plugin class into the ``/opt/rally/plugins`` or ``~/.rally/plugins``
directory (or its subdirectories), and it will be
autoloaded. Additional paths can be specified with the
``--plugin-paths`` argument, or with the ``RALLY_PLUGIN_PATHS``
environment variable, both of which accept comma-delimited
lists. Both ``--plugin-paths`` and ``RALLY_PLUGIN_PATHS`` can list
either plugin module files, or directories containing plugins. For
instance, both of these are valid:

.. code-block:: bash

    rally --plugin-paths /rally/plugins ...
    rally --plugin-paths /rally/plugins/foo.py,/rally/plugins/bar.py ...

You can also use a script ``unpack_plugins_samples.sh`` from
``samples/plugins`` which will automatically create the
``~/.rally/plugins`` directory.


Example: Benchmark scenario as a plugin
---------------------------------------

Let's create as a plugin a simple scenario which list flavors.

Creation
^^^^^^^^

Inherit a class for your plugin from the base *Scenario* class and implement a scenario method inside it as usual. In our scenario, let us first list flavors as an ordinary user, and then repeat the same using admin clients:

.. code-block:: python

    from rally.task import atomic
    from rally.task import scenario


    class ScenarioPlugin(scenario.Scenario):
        """Sample plugin which lists flavors."""

        @atomic.action_timer("list_flavors")
        def _list_flavors(self):
            """Sample of usage clients - list flavors

            You can use self.context, self.admin_clients and self.clients which are
            initialized on scenario instance creation"""
            self.clients("nova").flavors.list()

        @atomic.action_timer("list_flavors_as_admin")
        def _list_flavors_as_admin(self):
            """The same with admin clients"""
            self.admin_clients("nova").flavors.list()

        @scenario.configure()
        def list_flavors(self):
            """List flavors."""
            self._list_flavors()
            self._list_flavors_as_admin()


Usage
^^^^^

You can refer to your plugin scenario in the benchmark task configuration files just in the same way as to any other scenarios:

.. code-block:: json

    {
        "ScenarioPlugin.list_flavors": [
            {
                "runner": {
                    "type": "serial",
                    "times": 5,
                },
                "context": {
                    "create_flavor": {
                        "ram": 512,
                    }
                }
            }
        ]
    }

This configuration file uses the *"create_flavor"* context which we'll create as a plugin below.


Example: Context as a plugin
----------------------------

Let's create as a plugin a simple context which adds a flavor to the environment before the benchmark task starts and deletes it after it finishes.

Creation
^^^^^^^^

Inherit a class for your plugin from the base *Context* class. Then, implement the Context API: the *setup()* method that creates a flavor and the *cleanup()* method that deletes it.

.. code-block:: python

    from rally.task import context
    from rally.common import log as logging
    from rally import consts
    from rally import osclients

    LOG = logging.getLogger(__name__)


    @context.configure(name="create_flavor", order=1000)
    class CreateFlavorContext(context.Context):
        """This sample create flavor with specified options before task starts and
        delete it after task completion.

        To create your own context plugin, inherit it from
        rally.task.context.Context
        """

        CONFIG_SCHEMA = {
            "type": "object",
            "$schema": consts.JSON_SCHEMA,
            "additionalProperties": False,
            "properties": {
                "flavor_name": {
                    "type": "string",
                },
                "ram": {
                    "type": "integer",
                    "minimum": 1
                },
                "vcpus": {
                    "type": "integer",
                    "minimum": 1
                },
                "disk": {
                    "type": "integer",
                    "minimum": 1
                }
            }
        }

        def setup(self):
            """This method is called before the task start"""
            try:
                # use rally.osclients to get necessary client instance
                nova = osclients.Clients(self.context["admin"]["endpoint"]).nova()
                # and than do what you need with this client
                self.context["flavor"] = nova.flavors.create(
                    # context settings are stored in self.config
                    name=self.config.get("flavor_name", "rally_test_flavor"),
                    ram=self.config.get("ram", 1),
                    vcpus=self.config.get("vcpus", 1),
                    disk=self.config.get("disk", 1)).to_dict()
                LOG.debug("Flavor with id '%s'" % self.context["flavor"]["id"])
            except Exception as e:
                msg = "Can't create flavor: %s" % e.message
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning(msg)

        def cleanup(self):
            """This method is called after the task finish"""
            try:
                nova = osclients.Clients(self.context["admin"]["endpoint"]).nova()
                nova.flavors.delete(self.context["flavor"]["id"])
                LOG.debug("Flavor '%s' deleted" % self.context["flavor"]["id"])
            except Exception as e:
                msg = "Can't delete flavor: %s" % e.message
                if logging.is_debug():
                    LOG.exception(msg)
                else:
                    LOG.warning(msg)


Usage
^^^^^

You can refer to your plugin context in the benchmark task configuration files just in the same way as to any other contexts:

.. code-block:: json

    {
        "Dummy.dummy": [
            {
                "args": {
                    "sleep": 0.01
                },
                "runner": {
                    "type": "constant",
                    "times": 5,
                    "concurrency": 1
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 1
                    },
                     "create_flavor": {
                        "ram": 1024
                    }
                }
            }
        ]
    }

Example: SLA as a plugin
------------------------

Let's create as a plugin an SLA (success criterion) which checks whether the range of the observed performance measurements does not exceed the allowed maximum value.

Creation
^^^^^^^^

Inherit a class for your plugin from the base *SLA* class and implement its API (the *add_iteration(iteration)*, the *details()* method):

.. code-block:: python

    from rally.task import sla
    from rally.common.i18n import _

    @sla.configure(name="max_duration_range")
    class MaxDurationRange(sla.SLA):
        """Maximum allowed duration range in seconds."""

        CONFIG_SCHEMA = {
            "type": "number",
            "minimum": 0.0,
        }

        def __init__(self, criterion_value):
            super(MaxDurationRange, self).__init__(criterion_value)
            self._min = 0
            self._max = 0

        def add_iteration(self, iteration):
          # Skipping failed iterations (that raised exceptions)
            if iteration.get("error"):
                return self.success   # This field is defined in base class

            # Updating _min and _max values
            self._max = max(self._max, iteration["duration"])
            self._min = min(self._min, iteration["duration"])

            # Updating successfulness based on new max and min values
            self.success = self._max - self._min <= self.criterion_value
            return self.success

        def details(self):
            return (_("%s - Maximum allowed duration range: %.2f%% <= %.2f%%") %
                    (self.status(), self._max - self._min, self.criterion_value))


Usage
^^^^^

You can refer to your SLA in the benchmark task configuration files just in the same way as to any other SLA:

.. code-block:: json

    {
        "Dummy.dummy": [
            {
                "args": {
                    "sleep": 0.01
                },
                "runner": {
                    "type": "constant",
                    "times": 5,
                    "concurrency": 1
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 1
                    }
                },
                "sla": {
                    "max_duration_range": 2.5
                }
            }
        ]
    }


Example: Scenario runner as a plugin
------------------------------------

Let's create as a plugin a scenario runner which runs a given benchmark scenario for a random number of times (chosen at random from a given range).

Creation
^^^^^^^^

Inherit a class for your plugin from the base *ScenarioRunner* class and implement its API (the *_run_scenario()* method):

.. code-block:: python

    import random

    from rally.task import runner
    from rally import consts


    @runner.configure(name="random_times")
    class RandomTimesScenarioRunner(runner.ScenarioRunner):
        """Sample of scenario runner plugin.

        Run scenario random number of times, which is chosen between min_times and
        max_times.
        """

        CONFIG_SCHEMA = {
            "type": "object",
            "$schema": consts.JSON_SCHEMA,
            "properties": {
                "type": {
                    "type": "string"
                },
                "min_times": {
                    "type": "integer",
                    "minimum": 1
                },
                "max_times": {
                    "type": "integer",
                    "minimum": 1
                }
            },
            "additionalProperties": True
        }

        def _run_scenario(self, cls, method_name, context, args):
            # runners settings are stored in self.config
            min_times = self.config.get('min_times', 1)
            max_times = self.config.get('max_times', 1)

            for i in range(random.randrange(min_times, max_times)):
                run_args = (i, cls, method_name,
                            runner._get_scenario_context(context), args)
                result = runner._run_scenario_once(run_args)
                # use self.send_result for result of each iteration
                self._send_result(result)

Usage
^^^^^

You can refer to your scenario runner in the benchmark task configuration files just in the same way as to any other runners. Don't forget to put you runner-specific parameters to the configuration as well (*"min_times"* and *"max_times"* in our example):

.. code-block:: json

    {
        "Dummy.dummy": [
            {
                "runner": {
                    "type": "random_times",
                    "min_times": 10,
                    "max_times": 20,
                },
                "context": {
                    "users": {
                        "tenants": 1,
                        "users_per_tenant": 1
                    }
                }
            }
        ]
    }




Different plugin samples are available `here <https://github.com/openstack/rally/tree/master/samples/plugins>`_.
