ansible-lint module stubs
=========================

This directory holds lint-only stub implementations of the ``synchronize`` and
``zuul_return`` modules. Zuul injects both as custom action plugins when it
runs the playbooks in ``tests/ci/playbooks``, so they are never installed as
regular Ansible modules or collections.

The ``zuul-ansible-lint`` tox environment points ``ANSIBLE_LIBRARY`` at this
directory so that ansible-lint can resolve the bare module names during its
syntax check. The stubs deliberately live outside the ``playbooks`` directory:
Ansible auto loads a ``library`` folder next to a playbook, and we do not want
these fakes picked up by a real run.

Why not ansible-lint's ``mock_modules``?

* ansible-lint does not export its bare module mocks to the child
  ``ansible-playbook --syntax-check`` process (only collection mocks reach it
  via ``ANSIBLE_COLLECTIONS_PATH``), so bare ``mock_modules`` entries are
  silently ignored by the syntax check.
* ansible-core redirects the bare ``synchronize`` to the collection module
  ``ansible.posix.synchronize``, so mocking the bare name has no effect anyway.
  Shadowing it with a plain local module also keeps ``fqcn[action]`` quiet,
  which matters because Zuul requires the bare name in the playbook.

The stubs declare the arguments used by the playbooks so the experimental
``args`` rule stays happy. Extend their argument specs if a playbook starts
passing new options to either module.
