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

How plugins work
----------------

Rally provides an opportunity to create and use a **custom benchmark scenario, runner or context** as a **plugin**:

.. image:: ./images/Rally-Plugins.png
   :align: center

Plugins can be quickly written and used, with no need to contribute them to the actual Rally code. Just place a python module with your plugin class into the **/opt/rally/plugins** or **~/.rally/plugins** directory (or it's subdirectories), and it will be autoloaded.


Example: Benchmark scenario as a plugin
---------------------------------------

Let's create as a plugin a simple scenario which list flavors.

Creation
^^^^^^^^

Inherit a class for your plugin from the base *Scenario* class and implement a scenario method inside it as usual. In our scenario, let us first list flavors as an ordinary user, and then repeat the same using admin clients:

.. code-block:: none

    from rally.benchmark.scenarios import base


    class ScenarioPlugin(base.Scenario):
        """Sample plugin which lists flavors."""

        @base.atomic_action_timer("list_flavors")
        def _list_flavors(self):
            """Sample of usage clients - list flavors

            You can use self.context, self.admin_clients and self.clients which are
            initialized on scenario instance creation"""
            self.clients("nova").flavors.list()

        @base.atomic_action_timer("list_flavors_as_admin")
        def _list_flavors_as_admin(self):
            """The same with admin clients"""
            self.admin_clients("nova").flavors.list()

        @base.scenario()
        def list_flavors(self):
            """List flavors."""
            self._list_flavors()
            self._list_flavors_as_admin()


Placement
^^^^^^^^^

Put the python module with your plugin class into the **/opt/rally/plugins** or **~/.rally/plugins** directory or it's subdirectories and it will be autoloaded. You can also use a script **unpack_plugins_samples.sh** from **samples/plugins** which will automatically create the **~/.rally/plugins** directory.


Usage
^^^^^

You can refer to your plugin scenario in the benchmark task configuration files just in the same way as to any other scenarios:

.. code-block:: none

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

.. code-block:: none

    from rally.benchmark.context import base
    from rally.common import log as logging
    from rally import consts
    from rally import osclients

    LOG = logging.getLogger(__name__)


    @base.context(name="create_flavor", order=1000)
    class CreateFlavorContext(base.Context):
        """This sample create flavor with specified options before task starts and
        delete it after task completion.

        To create your own context plugin, inherit it from
        rally.benchmark.context.base.Context
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
                # use rally.osclients to get nessesary client instance
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



Placement
^^^^^^^^^

Put the python module with your plugin class into the **/opt/rally/plugins** or **~/.rally/plugins** directory or it's subdirectories and it will be autoloaded. You can also use a script **unpack_plugins_samples.sh** from **samples/plugins** which will automatically create the **~/.rally/plugins** directory.


Usage
^^^^^

You can refer to your plugin context in the benchmark task configuration files just in the same way as to any other contexts:

.. code-block:: none

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

Inherit a class for your plugin from the base *SLA* class and implement its API (the *check()* method):

.. code-block:: none

    from rally.benchmark import sla


    class MaxDurationRange(sla.SLA):
        """Maximum allowed duration range in seconds."""
        OPTION_NAME = "max_duration_range"
        CONFIG_SCHEMA = {"type": "number", "minimum": 0.0,
                         "exclusiveMinimum": True}

        @staticmethod
        def check(criterion_value, result):
            durations = [r["duration"] for r in result if not r.get("error")]
            durations_range = max(durations) - min(durations)
            success = durations_range <= criterion_value
            msg = (_("Maximum duration range per iteration %ss, actual %ss")
                   % (criterion_value, durations_range))
            return sla.SLAResult(success, msg)



Placement
^^^^^^^^^

Put the python module with your plugin class into the **/opt/rally/plugins** or **~/.rally/plugins** directory or it's subdirectories and it will be autoloaded. You can also use a script **unpack_plugins_samples.sh** from **samples/plugins** which will automatically create the **~/.rally/plugins** directory.


Usage
^^^^^

You can refer to your SLA in the benchmark task configuration files just in the same way as to any other SLA:

.. code-block:: none

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

.. code-block:: none

    import random

    from rally.benchmark import runner
    from rally import consts


    class RandomTimesScenarioRunner(runner.ScenarioRunner):
        """Sample of scenario runner plugin.

        Run scenario random number of times, which is chosen between min_times and
        max_times.
        """

        __execution_type__ = "random_times"

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



Placement
^^^^^^^^^

Put the python module with your plugin class into the **/opt/rally/plugins** or **~/.rally/plugins** directory or it's subdirectories and it will be autoloaded. You can also use a script **unpack_plugins_samples.sh** from **samples/plugins** which will automatically create the **~/.rally/plugins** directory.


Usage
^^^^^

You can refer to your scenario runner in the benchmark task configuration files just in the same way as to any other runners. Don't forget to put you runner-specific parameters to the configuration as well (*"min_times"* and *"max_times"* in our example):

.. code-block:: none

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
