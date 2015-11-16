..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode


====================
 Re-organize Plugins
====================

Move all plugins under rally/plugins to simplify Rally code base


Problem description
===================

Rally code is coupled with Rally engine and infra as well as OpenStack specific
code. This makes contribution harder as new-comers need to understand Rally
code as well as many different plugins. It also makes reviewing much harder.

Proposed change
===============

Moving all plugins under a single directory, with "OpenStack" as its
sub-directory would make everything simpler.

Alternatives
------------

None comes to mind.

Implementation
==============


.. code-block:: shell

  rally/
   |
   +-- plugins/
           |
           +-- common/
           |     |
           |     +-- runners/
           |     +-- sla/
           |     +-- contexts/
           |     +-- scenarios/
           |
           +-- openstack/
                 |
                 +-- runners/
                 +-- sla/
                 +-- contexts/
                 +-- scenarios/


NOTE: looking at the current code base we can see that:

#. All ``runners`` and ``sla`` will go under ``common``.
#. All ``contexts`` will go under ``openstack``.
#. Most of ``scenarios`` (except for ``dummy``) will go under ``openstack``.

Assignee(s)
-----------

  - yfried

  - boris-42

Work Items
----------

- Move all OpenStack related plugins and code under ``plugins/openstack/`` and
  all other plugins code under ``plugins/common/``.


Dependencies
============

- Plugin unification
