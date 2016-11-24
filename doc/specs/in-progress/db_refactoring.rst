..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==============================
Scaling & Refactoring Rally DB
==============================

There are a lot of use cases that can't be done because of DB schema that we
have. This proposal describes what and why we should change in DB.

Problem description
===================

There are 3 use cases that requires DB refactoring:

1. scalable task engine

   Run benchmarks with billions iterations
   Generate distributed load 10k-100k RPS
   Generate all reports/aggregated based on that data

2. multi scenario load generation

   Running multiple scenarios as a part of single subtask requires changes
   in the way how we are storing subtask results.

3. task debugging and profiling

   Store complete results of validation in DB (e.g. what validators were run,
   what validators passed, what didn't passed and why).

   Store durations of all steps (validation/task) as well as  other execution
   stats needed by CLI and to generate graphs in reports.

   Store statuses, duration, errors of context cleanup steps.

Current schema doesn't work for those cases.

Proposed change
===============

Changes in DB
-------------

Existing DB schema
~~~~~~~~~~~~~~~~~~

.. code-block::

    +------------+    +-------------+
    | Task       |    | TaskResult  |
    +------------+    +-------------+
    |            |    |             |
    |  id        |    |  id         |
    |  uuid   <--+----+- task_uuid  |
    |            |    |             |
    +------------+    +-------------+

* Task - stores task status, tags, validation log

* TaskResult - stores all information about workloads, including
  configuration, conext, sla, results etc.


New DB schema
~~~~~~~~~~~~~

.. code-block::

    +------------+    +-------------+    +--------------+    +---------------+
    | Task       |    | Subtask     |    | Workload     |    | WorkloadData  |
    +------------+    +-------------+    +--------------+    +---------------+
    |            |    |             |    |              |    |               |
    |  id        |    |  id    <----+--+ |  id    <-----+--+ |  id           |
    |  uuid   <--+----+- task_uuid  |  +-+- subtask_id  |  +-+- workload_id  |
    |   ^        |    |  uuid       |    |  uuid        |    |  uuid         |
    +---+--------+    +---^---------+    |              |    |               |
        +--------------------------------+- task_uuid   |    |               |
        |                 |              +--------------+    |               |
        +----------------------------------------------------+- task_uuid    |
        |                 |                                  +---------------+
        +-------+---------+
                |
    +--------+  +
    | Tag    |  |
    +--------+  |
    |        |  |
    |  id    |  |
    |  uuid -+--+
    |  type  |
    |  tag   |
    +--------+

* Task - stores information about task, when it was started/updated/finished,
  it's status, description, and so on. As well it used to aggregate all
  subtasks related to this task

* SubTask - stores information about subtask, when it was started/updated/
  finished, it's status, description, configuration, aggregated information
  about workloads. Without subtasks we won't be able to track information
  about task execution, and run many subtasks in single task.

* Workload - aggregated information about some specific workload (required
  for reports) as well as information how these workloads are executed in
  parallel/serial and status of each workload.  Without workloads table we
  won't be able to support multiple workloads per single subtas

* WorkloadData - contains chunks of raw data for future data analyze and
  reporting. This is complete information that we don't need always, as well
  for getting overview of what happened. As we have multiple chunks per
  Workload, we won't be able to store them without creating this table.

* Tag - contains tags binded to tasks and subtasks by uuid and type


Task table
~~~~~~~~~~

.. code-block::

    id                      : INT, PK
    uuid                    : UUID

    # Optional
    deployment_uuid         : UUID

    # Full input task configuration
    input_task              : TEXT

    title                   : String
    description             : TEXT

    # Structure of verification results:
    # [
    #    {
    #        "name": <name>,      # full validator function name,
    #                             # validator plugin name (in the future)
    #        "input": <input>,    # smallest part of
    #        "message": <msg>,    # message with description
    #        "success": <bool>,   # did validatior pass
    #        "duration": <float>  # duration of validation process
    #    },
    #   .....
    # ]
    validation_result       : TEXT

    # Duration of verification can be used to tune verification process.
    validation_duration     : FLOAT

    # Duration of benchmarking part of task
    task_duration           : FLOAT

    # All workloads in the task are passed
    pass_sla                : BOOL

    # Current status of task
    status                  : ENUM(init, validating, validation_failed,
                                   aborting, soft_aborting, aborted,
                                   crashed, validated, running, finished)


Task.status diagram of states
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block::

    INIT -> VALIDATING -> VALIDATION_FAILED
                       -> ABORTING -> ABORTED
                       -> SOFT_ABORTING -> ABORTED
                       -> CRASHED
                       -> VALIDATED -> RUNNING -> FINISHED
                                               -> ABORTING -> ABORTED
                                               -> SOFT_ABORTING -> ABORTED
                                               -> CRASHED


Subtask table
~~~~~~~~~~~~~

.. code-block::

    id                      : INT, PK
    uuid                    : UUID
    task_uuid               : UUID
    title                   : String
    description             : TEXT

    # Position of Subtask in Input Task
    position                : INT

    # Context and SLA could be defined both Subtask-wide and per workload
    context                 : JSON
    sla                     : JSON

    run_in_parallel         : BOOL
    duration                : FLOAT

    # All workloads in the task are passed
    pass_sla                : BOOL

    # Current status of task
    status                  : ENUM(running, finished, crashed)


Workload table
~~~~~~~~~~~~~~

.. code-block::

    id                      : INT, PK
    uuid                    : UUID
    subtask_id              : INT
    task_uuid               : UUID

    # Unlike Task's and Subtask's title which is arbitrary
    # Workload's name defines scenario being executed
    name                    : String

    # Scenario plugin docstring
    description             : TEXT

    # Position of Workload in Input Task
    position                : INT

    runner                  : JSON
    runner_type             : String

    # Context and SLA could be defined both Subtask-wide and per workload
    context                 : JSON
    sla                     : JSON

    args                    : JSON

    # SLA structure that contains all detailed info looks like:
    # [
    #   {
    #       "name": <full_name_of_validator>,
    #       "duration": <duration_of_validation>,
    #       "success": <boolean_pass_or_not>,
    #       "message": <description_of_what_happened>,
    #   }
    #]
    #
    sla_results             : TEXT

    # Context data structure (order makes sense)
    #[
    #   {
    #      "name": string
    #      "setup_duration": FLOAT,
    #      "cleanup_duration": FLOAT,
    #      "exception": LIST          # exception info
    #      "setup_extra": DICT        # any custom data
    #      "cleanup_extra": DICT      # any custom data
    #
    #   }
    #]
    context_execution       : TEXT

    starttime               : TIMESTAMP

    load_duration           : FLOAT
    full_duration           : FLOAT

    # Shortest and longest iteration duration
    min_duration            : FLOAT
    max_duration            : FLOAT

    total_iteration_count   : INT
    failed_iteration_count  : INT

    # Statictics data structure (order makes sense)
    #   {
    #      "<action_name>": {
    #        "min_duration": FLOAT,
    #        "max_duration": FLOAT,
    #        "median_duration": FLOAT,
    #        "avg_duration": FLOAT,
    #        "percentile90_duration": FLOAT,
    #        "percentile95_duration": FLOAT,
    #        "success_count": INT,
    #        "total_count": INT
    #      },
    #      ...
    # }
    statistics              : JSON  # Aggregated information about actions

    # As for SLA result
    pass_sla                : BOOL

    # Profile information collected during the run of scenario
    # This is internal data and format of it can be changed over time
    # _profiling_data       : Text


WorkloadData
~~~~~~~~~~~~

.. code-block::

    id                      : INT, PK
    uuid                    : UUID
    workload_id             : INT
    task_uuid               : UUID

    # Chunk order it's used to be able to sort output data
    chunk_order             : INT

    # Amount of iterations, can be useful for some of algorithms
    iteration_count         : INT

    # Number of failed iterations
    failed_iteration_count  : INT

    # Full size of results in bytes
    chunk_size              : INT

    # Size of zipped results in bytes
    zipped_chunk_size       : INT

    started_at              : TIMESTAMP
    finished_at             : TIMESTAMP

    # Chunk_data structure
    # [
    #   {
    #     "duration": FLOAT,
    #     "idle_duration": FLOAT,
    #     "timestamp": FLOAT,
    #     "errors": LIST,
    #     "output": {
    #       "complete": LIST,
    #       "additive": LIST,
    #     },
    #     "actions": LIST
    #   },
    #   ...
    # ]
    chunk_data             : BLOB  # compressed LIST of JSONs


Tag table
~~~~~~~~~

.. code-block::

    id                      : INT, PK
    uuid                    : UUID of task or subtask
    type                    : ENUM(task, subtask)
    tag                     : TEXT

- (uuid, type, tag) is unique and indexed


Open questions
~~~~~~~~~~~~~~

None.


Alternatives
------------

None.


Implementation
==============

Assignee(s)
-----------

- boris-42 (?)
- ikhudoshyn

Milestones
----------

Target Milestone for completion: N/A

Work Items
----------

TBD

Dependencies
============

- There should be smooth transition of code to work with new data structure
