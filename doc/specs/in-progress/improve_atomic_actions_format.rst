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


=============================================
New Atomic actions format in workload results
=============================================

Currently atomic actions data in workload results is insufficient,
therefore some new features can not be implemented.

Problem description
===================

The main problem is that current format does not support nested
atomic actions.

Also, atomic actions data does not include timestamps for each action
start and end time. Having this data will allow us to inspect atomic
actions runtime better and generate detailed reports.

Since word "atomic" means something that can not be splitted into parts
and we introduce nested atomic actions, we should use different term
instead of "atomic actions".

Proposed change
===============

Term "atomic actions" should be renamed to just "actions".

Change actions results schema from type "object" to "array"
and extend it with timestamps and nested actions.

Nested actions will be represented by "children" key and have
single level of nesting, since there is no need of more nested levels.
We could implement deeper nesting at any time later, if required.

With timestamps, there is no need to save durations anymore,
so get rid of this value.

Since this change is not backward compatible, we need to create
a database migration script. The migration will use iteration start
timestamp as start timestamp for first action and then calculate
further timestamps based on actions order and their durations.

Benefits of new format
----------------------

Nested actions will make actions measurement more detailed and flexible
since we could have data what sub-actions were run during specific action
runtime, without complicated changes at code.

Start and end timestamps will provide us with accurate information
about action runtime within the whole iteration and ability to create
`Gantt charts <https://en.wikipedia.org/wiki/Gantt_chart>`_.

Schema modification
-------------------

Schema location is *rally.common.objects.task.TASK_RESULT_SCHEMA
["properties"]["result"]["properties"]["atomic_actions"]*

should be moved to *rally.common.objects.task.TASK_RESULT_SCHEMA
["properties"]["result"]["properties"]["actions"]*

and changed:

AS IS:

.. code-block:: python

  {
      "type": "object"
  }

Here keys are actions names, and values are their durations.
Actions data is actually represented by collections.OrderedDict,
so we have real order saved.

Example:

.. code-block:: python

  OrderedDict([("keystone.create_tenant", 0.1234),
               ("keystone.create_users", 1.234)])

TO BE:

.. code-block:: python

  {
      "type": "array",
      "items": {
          "type": "object",
          "properties": {
              "name": {"type": "string"},  # name of action
              "started_at": {"type": "number"},  # float UNIX timestamp
              "finished_at": {"type": "number"},  # float UNIX timestamp
              "children": {  # nested actions, single level
                  "type": "array",
                  "items": {
                      "type": "object",
                      "properties": {
                          "name": {"type": "string"},
                          "started_at": {"type": "number"},
                          "finished_at": {"type": "number"}
                      },
                      "required": ["name", "started_at", "finished_at"],
                      "additionalProperties": False
                  },
                  "minItems": 0
              }
          },
          "required": ["name", "started_at", "finished_at", "children"],
          "additionalProperties": False
      },
      "minItems": 0
  }

Example how this data can be represented:

.. code-block:: python

  [{"name": "keystone.create_tenant",
    "started_at": 1455281370.288397,
    "finished_at": 1455281372.672342,
    "children": []},
   {"name": "keystone.create_users",
    "started_at": 1455281372.931324,
    "finished_at": 1455281373.375184,
    "children": []}]

Alternatives
------------

None


Implementation
==============

Assignee(s)
-----------

Primary assignee:
  Alexander Maretskiy <amaretskiy@mirantis.com>


Work Items
----------

 - Rename atomic actions into actions
 - Improve actions results format
 - Create a DB migartion that transforms results to new format

Dependencies
============

None
