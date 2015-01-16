Tasks Configuration Samples
===========================

To specify your tasks, use configuration files in json or yaml format.


General structure of configuration file:
::

    {
        "ScenarioClass.scenario_method":
            "args": {
                ...
            },
            "runner": {
                ...
            },
            "context": {
                ...
            }
            "sla": {
                ...
            }
        }
    }

ScanarioClass should be a subclass of the base Scenario class
and scenario_method specifies what benchmark task should be run. Section
"args" is also related to scenario. To learn more about scenarios
configuration, see samples in `doc/samples/tasks/scenarios
<https://github.com/stackforge/rally/tree/master/doc/samples/tasks/scenarios>`_.

Section "runners" specifies the way, how task should be run. To learn
more about runners configurations, see samples in `doc/samples/tasks/runners
<https://github.com/stackforge/rally/tree/master/doc/samples/tasks/runners>`_.

Section "context" defines different types of environments in which task can
be launched. Look at `doc/samples/tasks/contexts
<https://github.com/stackforge/rally/tree/master/doc/samples/tasks/contexts>`_
for samples.

Section "sla" defines details for determining compliance with contracted values
such as maximum error rate or minimum response time.
Look at `doc/samples/tasks/sla
<https://github.com/stackforge/rally/tree/master/doc/samples/tasks/sla>`_ for
samples.

See a `detailed description of benchmark scenarios, contexts & runners
<https://github.com/stackforge/rally/tree/master/doc/source/concepts.rst>`_.
