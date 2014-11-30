Rally Style Commandments
========================

- Step 1: Read the OpenStack Style Commandments
  http://docs.openstack.org/developer/hacking/
- Step 2: Read on

Rally Specific Commandments
---------------------------
* [N30x] - Reserved for rules related to ``mock`` library
 * [N301] - Ensure that ``assert_*`` methods from ``mock`` library is used correctly
 * [N302] - Ensure that nonexistent "assert_called" is not used
 * [N303] - Ensure that  nonexistent "assert_called_once" is not used
* [N310-N314] - Reserved for rules related to logging
 * [N310] - Ensure that ``rally.log`` is used instead of ``rally.openstack.common.log``
 * [N311] - Validate that debug level logs are not translated
* [N32x] - Reserved for rules related to assert* methods
 * [N320] - Ensure that ``assertTrue(isinstance(A, B))``  is not used
 * [N321] - Ensure that ``assertEqual(type(A), B)`` is not used
 * [N322] - Ensure that ``assertEqual(A, None)`` and ``assertEqual(None, A)`` are not used
 * [N323] - Ensure that ``assertTrue/assertFalse(A in/not in B)`` are not used with collection contents
