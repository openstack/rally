Tasks Configuration Samples
===========================

To specify your tasks, use configuration files in json or yaml format.


JSON schema of input task format:

::


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
                            "type": "object"
                        },
                    },
                    "additionalProperties": False
                }
            }
        }
    }


For humans:

::
    {
        "ScenarioClass.scenario_method": [
            {
                "args": {
                    ...
                },
                "runner": {
                    ...
                },
                "context": {
                    ...
                },
                "sla": {
                    ...
                }
            }
        ]
    }


ScanarioClass should be a subclass of the base Scenario class
and scenario_method specifies what benchmark task should be run. Section
"args" is also related to scenario. To learn more about scenarios
configuration, see samples in `samples/tasks/scenarios
<https://github.com/openstack/rally/tree/master/samples/tasks/scenarios>`_.

Section "runners" specifies the way, how task should be run. To learn
more about runners configurations, see samples in `samples/tasks/runners
<https://github.com/openstack/rally/tree/master/samples/tasks/runners>`_.

Section "context" defines different types of environments in which task can
be launched. Look at `samples/tasks/contexts
<https://github.com/openstack/rally/tree/master/samples/tasks/contexts>`_
for samples.

Section "sla" defines details for determining compliance with contracted values
such as maximum error rate or minimum response time.
Look at `samples/tasks/sla
<https://github.com/openstack/rally/tree/master/samples/tasks/sla>`_ for
samples.

See a `detailed description of benchmark scenarios, contexts & runners
<https://github.com/openstack/rally/tree/master/source/concepts.rst>`_.
