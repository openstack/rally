..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

..
 This template should be in ReSTructured text. The filename in the git
 repository should match the launchpad URL, for example a URL of
 https://blueprints.launchpad.net/heat/+spec/awesome-thing should be named
 awesome-thing.rst .  Please do not delete any of the sections in this
 template.  If you have nothing to say for a whole section, just write: None
 For help with syntax, see http://sphinx-doc.org/rest.html
 To test out your formatting, see http://www.tele3.cz/jbar/rest/rest.html


====================================
Make the new Rally input task format
====================================

Current Rally format is not flexible enough to cover all use cases that are
required. Let's change it!


Problem description
===================

 Why do we need such fundamental change?

-   Multi scenarios load generation support.
    This is very important, because it will allow to use Rally for more
    real life load generation. Like making load on different components
    and HA testing (where one scenario tries for example to authenticate
    another is disabling controller)

-   Ability to add require meta information like (title and descriptions)
    That are required to generate clear reports

-   Fixing UX issues. Previous format is very hard for understanding and
    end users have issues with understanding how it works exactly.


Proposed change
===============

Make a new format that address all issues.


Old format JSON schema:

.. code-block:: python

    {
        "type": "object",
        "$schema": "http://json-schema.org/draft-04/schema",
        "patternProperties": {
            ".*": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "args": {
                            "type": "object"
                        },
                        "runner": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"}
                            },
                            "required": ["type"]
                        },
                        "context": {
                            "type": "object"
                        },
                        "sla": {
                            "type": "object",
                        },
                    },
                    "additionalProperties": False
                }
            }
        }
    }


Old format sample:

.. code-block:: yaml

    ---
        <ScenarioName>:
        -
            args: <dict_with_scenario_args>
            runner: <dict_with_runner_type_and_args>
            context:
                <context_name>: <dict_with_context_args>
                ...
            sla:
                <sla_name>: <sla_arguments>
        -
            -//-
        -
            -//-
        <AnotherScenarioName>:
            -//-

    Every element of list corresponding to <ScenarioName> is separated task,
    that generates environment according to context, generates load using
    specified runner that runs multiple times <ScenarioName> with it's args.


New format JSON schema:

.. code-block:: python

    {
        "type": "object",
        "$schema": "http://json-schema.org/draft-04/schema",
        "properties": {
            "version": {"type": "number"},
            "title": {"type": "string"},
            "description": {"type": "string"},
            "tags": {
                "type": "array",
                "items": {"type": "string"}
            },

            "subtasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"}
                        },

                        "run_in_parallel": {"type": "boolean"},
                        "workloads": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},

                                    "args": {
                                        "type": "object"
                                    },

                                    "runner": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string"}
                                        },
                                        "required": ["type"]
                                    },

                                    "sla": {
                                        "type": "object"
                                    },

                                    "context": {
                                        "type": "object"
                                    }
                                },
                                "required": ["name", "runner"]
                            }
                        },
                        "context": {
                            "type": "object"
                        }
                    },
                    "required": ["title", "workloads"]
                }
            }
        },
        "required": ["title", "tasks"]
    }


New format sample:

.. code-block:: yaml

    ---

      # Having Dictionary on top level allows us in future to add any new keys.
      # Keeping the schema of format more or less same for end users.

      # Version of format
      version: 1

      # Allows to set title of report. Which allows end users to understand
      # what they can find in task report.
      title: "New Input Task format"

      # Description allows us to put all required information to explain end
      # users what kind of results they can find in reports.
      description: "This task allows you to certify that your cloud works"

      # Explicit usage "rally task start --tag" --tag attribute
      tags: ["periodic", "nova", "cinder", "ha"]

      subtasks:
      # Note every task is executed serially (one by one)
      #
      # Using list for describing what benchmarks (tasks) to run is much
      # better idea then using Dictionary. It resolves at least 3 big issues:
      #
      # 1) Bad user experience
      # 1.1) Users do not realize that Rally can run N benchmarks
      # 1.2) Keys of Dictionary were Scenario names (reasonable question why?!)
      # 1.3) Users tried to put N times same k-v (to run one benchmark N times)
      # 2) No way to specify order of scenarios execution, especially in case
      #    where we need to do chain like: ScenarioA -> SecnearioB -> ScenarioA
      # 3) No way to support multi scenario load, because we used scenario name
      #    as a identifier of single task
      -
        # title field is required because in case of multi scenario load
        # we can't use scenario name for it's value.
        title: "First task to execute"
        description: "We will stress Nova"  # optional

        # Tags are going to be used in various rally task reports for filtering
        # and grouping.
        tags: ["nova", "my_favorite_task", "do it"]

        # The way to execute scenarios (one by one or all in parallel)
        run_in_parallel: False

        # Single scenario load can be generated by specifying only one element
        # in "workloads" section.
        workloads:
          -
            # Full name of scenario plugin
            name: "NovaServers.boot_and_delete"
            # Arguments that are passed to "NovaServers.boot_and_delete" plugin
            args:
              image:
                name: "^cirros$"
              flavors:
                name: "m1.small"
            # Specification of load that will be generated
            runner:
              type: "constant"
              times: 100
              concurrency: 10
            # Benchmark success of criteria based on results
            sla:
              # Every key means SLA plugin name, values are config of plugin
              # Only if all criteria pass task is marked as passed
              failure_rate:
                max: 0
        # Specification of context that creates env for benchmark scenarios
        # E.g. it creates users, tenants, sets quotas, uploads images...
        context:
          # Each key is the name of context plugin

          # This context creates temporary users and tenants
          users:
            # These k-v will be passed as arguments to this `users` plugin
            tenants: 2
            users_per_tenant: 10

          # This context set's quotas for created by `users` context tenants
          quotas:
            nova:
              cpu: -1

      -
        title: "Second task to execute"
        description: "Multi Scenario load generation with common context"

        run_in_parallel: True

        # If we put 2 or more scenarios to `scenarios` section we will run
        # all of them simultaneously which allows us to generate more real life
        # load
        workloads:
          -
            name: "CinderVolumes.create_and_delete"
            args:
              size: 10
            runner:
              type: "constant"
              times: 100
              concurrency: 10
            sla:
              failure_rate:
                max: 0
          -
            name: "KeystoneBasic.create_and_delete_users"
            args:
              name_length: 20
            runner:
                type: "rps"
                rps: 1
                times: 1000
            sla:
              max_seconds_per_iteration: 10
          -
            name: "PhysicalNode.restart"
            args:
              ip: "..."
              user: "..."
              password: "..."
            runner:
                type: "rps"
                rps: 10
                times: 10
            sla:
              max_seconds_per_iteration: 100
            # This scenario is called in own independent and isolated context
            context: {}

        # Global context that is used if scenario doesn't specify own
        context:
          users:
            tenants: 2
            users_per_tenant: 10


Alternatives
------------

No way


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  boris-42 aka Boris Pavlovic


Work Items
----------

- Implement OLD -> NEW format converter

- Switch benchmark engine to use new format.
  This should affect only benchmark engine

- Implement new DB schema format, that will allow to store multi-scenario
  output data

- Add support for multi scenario results processing in rally task
  detailed|sla_check|report

- Add timestamps to task, scenarios and atomics

- Add support for usage multi-runner instance in single task with
  common context

- Add support for scenario's own context

- Add ability to use new format in rally task start.

- Deprecate  OLD format


Dependencies
============

None
