..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

=========================
Consistent Resource Names
=========================

To facilitate better cleanup of ephemeral resources created by Rally,
random resource names need to be consistently used across all
scenarios and all plugins. Additionally, to support Rally's use
against systems other than OpenStack, plugins need greater control
over both the format and the list of characters used in generating
resource names.

Problem description
===================

Currently we use a few different cleanup mechanisms, some of which
(Keystone) use resource names, while most others use tenant
membership. As a result, if Rally is interrupted before cleanup
completes it may not be possible to know which resources were created
by Rally (and thus should be cleaned up after the fact).

Random names are generated from a fairly limited set of digits and
ASCII letters. This should be configurable by each plugin, along with
all other parts of the random name, in order to support benchmarking
systems other than OpenStack, which may have different naming
restrictions.

Finally, each Rally task should include some consistent element in its
resource names, distinct from other Rally tasks, to support multiple
independent Rally runs and cleanup.

Proposed change
===============

Random names will consist of three components:

* A random element derived from the task ID that is the same for all
  random names in the task;
* A random element that should be different for all names in the task;
  and
* Any amount of formatting as determined by the plugin.

The format of the random name will be given by a class variable,
``RESOURCE_NAME_FORMAT``, on each scenario and context plugin. This
variable is a ``mktemp(1)``-like string that describes the format; the
default for scenario plugins will be::

    RESOURCE_NAME_FORMAT = "s_rally_XXXXXXXX_XXXXXXXX"

And for context plugins::

    RESOURCE_NAME_FORMAT = "c_rally_XXXXXXXX_XXXXXXXX"

The format must have two separate sets of at least three consecutive
'X's. (That is, they must match:
``^.*(?<!X)X{3,}(?!X).*(?<!X)X{3,}(?!X)``. This marks a slight
departure from ``mktemp(1)``, which requires a single set of three or
more 'X's at the end.) Three 'X's is likely dangerously few --
offering only 1000 unique names per task -- but necessary in order to
support systems with eight-character name limits.

Another variable will control the allowed characters in the random
portions. The default will be::

    RESOURCE_NAME_ALLOWED_CHARACTERS = \
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

We will attempt to use the task ID, stripped of dashes, for the first
random portion. If ``RESOURCE_NAME_ALLOWED_CHARACTERS`` does not allow
all of the characters in the task ID (lowercase letters and digits),
then we will use a random string generated from the allowed
characters, with the pRNG seeded with the task ID.

Alternatives
------------

The resources could be recorded as they are created to a database or
file, and then that information used to perform cleanup later. This is
insufficient for recovering from a massive Rally failure, though, so
while it would be simpler in many ways, it does not meet the
requirements for out-of-band cleanup. It also doesn't support the two
other goals of this spec -- broader application support and multiple
concurrent runs -- both of which would still require most of the work
described herein. It would also not scale well for distributed load
generation.

The format and allowed characters could be configured in
``rally.conf``, but this does not permit a single Rally installation
to be used for multiple applications with divergent naming
requirements, and it offloads responsibility for understanding naming
limitations to the Rally user, not the plugin author.

Implementation
==============

Assignee(s)
-----------

Primary assignee:
  stpierre aka Chris St. Pierre

Other contributors:
  rvasilets aka Roman Vasilets
  wtakase aka Wataru Takase

Work Items
----------

* Overhaul `rally.common.utils.generate_random_name()` and
  `rally.task.scenarios.base.Scenario._generate_random_name()`. Early
  proof of concept that implements some of the points in this spec:
  https://review.openstack.org/#/c/184888/

* Find and fix resources that are created without
  generate_random_name().

Dependencies
============

None.
