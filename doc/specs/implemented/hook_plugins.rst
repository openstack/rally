..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=======================
New Plugins Type - Hook
=======================

Problem description
===================

Rally lacks a plugin type that would run some code on specified iteration.
New plugin type is required for reliability testing of OpenStack. This type of
plugin would give an ability to activate factors on some iteration and provide
timestamps and some info about executed actions to rally report.

Proposed change
===============

Add a new section to task config:

Schema of hook section allows to specify number of iteration and a list
of hook plugins that should be executed on this iteration.

.. code:: json

    {
        "KeystoneBasic.create_delete_user": [
            {
                "args": {},
                "runner": {
                    "type": "constant",
                    "times": 100,
                    "concurrency": 10
                },
                "hook": [       # new section
                    {
                        "name": "example_hook",
                        "args": {
                            "cmd": "bash enable_factor_1"
                        },
                        "trigger: {
                            "name": "event",
                            "args": {
                                "unit": "time",
                                "at": [1, 50, 100]  # seconds since start
                            }
                        }
                    },
                    {
                        "name": "example_hook",
                        "args": {
                            "cmd": "bash enable_factor_2"
                        },
                        "trigger: {
                            "name": "event",
                            "args": {
                                "unit": "iteration",
                                "at": [35, 40, 45]  # iteration numbers
                            }
                        }
                    },
                    {
                        "name": "example_hook",
                        "args": {
                            "cmd": "bash enable_factor_3"
                        },
                        "trigger: {
                            "name": "periodic",
                            "args": {
                                "unit": "iteration",
                                "step": 20,   # execute hook each 20 iterations
                                "start": 0,
                                "end": 1000
                            }
                        }
                    },
                    {
                        "name": "example_hook",
                        "args": {
                            "cmd": "bash enable_factor_4"
                        },
                        "trigger: {
                            "name": "periodic",
                            "args": {
                                "unit": "time",
                                "step": 15,   # execute hook each 15 seconds
                                "start": 100,
                                "end": 200
                            }
                        }
                    }
                ]
            }
        ]
    }


Add a new base class for such plugins, that should:
    - contain common logic for schema validation
    - save timestamps when "run" method started/finished
    - provide abstract method 'run' which should be implemented in plugins
      this method should be called after specified iteration has been executed

Add new classes for trigger plugins, that should:
    - contain validation schema for its configuration
    - contain "get_listening_event" and "on_event" methods

Trigger plugin classes should:
    - implement "get_listening_event" methods that return events to listen
    - implement "on_event" methods that check event type and value;
      launch hook if needed


Add HookExecuter class to run hook plugins, that should:
    - control when to run a hook specified in config
    - receive result of hook execution from hook plugin
    - return a full result of hook execution in the following format:

.. code:: json

    [{
        # this is config of specific hook; it should not be empty!
        "config": {...},
        "results":[
            {
                # value is time in seconds
                "triggered_by": {"event_type": "iteration", "value": 20},
                "started_at": 1470331269.134323,
                "finished_at": 1470331319.761103,
                "status": "success",
                # same output format as in scenarios; this key can be missed
                # if no output was added
                "output": {}
            }
        ],
        "summary": {"success": 1}
    }]

Modify ResultConsumer, that should:
    - control HookExecuter and provide info about iterations
    - add a full result to TaskResult

Example code of base class:

.. code:: python

    @plugin.base()
    @six.add_metaclass(abc.ABCMeta)
    class Hook(plugin.Plugin):

        @classmethod
        def validate(cls, config):
            # schema validation
            pass

        def __init__(self, config):
            self.config = config

        @abc.abstractmethod
        def run(self):
            pass


example_hook class:

.. code:: python

    @hook.configure(name="example_hook")
    class ExampleHook(hook.Hook):

        CONFIG_SCHEMA = {
            "type": "object",
            "$schema": consts.JSON_SCHEMA,
            "properties": {
                "cmd": {
                    "type": "string"
            },
            "required": [
                "cmd",
            ],
            "additionalProperties": False,
        }

        def __init__(self, config):
            super(ExampleHook, self).__init__(config)
            self.cmd = self.config["cmd"]

        def run(self):
            # do some action
            rc = os.system(self.cmd)


Example of hook result that goes to TaskResult (list of dicts):

.. code:: python

    [{
        # this is config of specific hook; it should not be empty!
        "config": {...},
        "results":[
            {
                "triggered_by": {"event_type": "iteration", "value": 20},
                "started_at": 1470331269.134323,
                "finished_at": 1470331319.761103,
                "status": "success",
                # same output format as in scenarios; this key can be missed
                # if no output was added
                "output": {}
            },
            {
                # value is time in seconds
                "triggered_by": {"event_type": "time", "value": 150.0},
                "started_at": 1470331270.352342,
                "finished_at": 1470331333.623303,
                "status": "failed",
                "error": {
                    "etype": "Exception",  # type of exception
                    "msg": "exception message",
                    # additional information to help (for example, traceback)
                    "details": ""
                }
            }
        ],
        "summary": {"success": 1, "failed": 1}
    }]


Alternatives
------------

Use sla section for such plugins, but this looks weird


Implementation
==============

Assignee(s)
-----------

Primary assignee:

- astudenov <astudenov@mirantis.com>
- ylobankov <ylobankov@mirantis.com>
- amaretskiy <amaretskiy@mirantis.com>


Work Items
----------

- Implement new section in task config
- Add example of hook plugin that runs specified command as subprocess
- Add trigger plugins for iterations
- Add trigger plugins for time
- Add hooks results into HTML report

Dependencies
============

None
