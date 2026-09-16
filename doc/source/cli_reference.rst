.. _cli-reference:


Command Line Interface
======================

.. note::

   A few things are common for all commands, so they are not repeated for
   every command below.

   * Every command and every category accepts ``--help``, i.e.
     ``rally task --help`` and ``rally task start --help``.
   * Values can be passed as ``--opt value`` or as ``--opt=value``.
   * Flags take no value. Some of them have a negative form, i.e. ``--use``
     and ``--no-use``.
   * Shell completion is available. Run ``rally --install-completion`` once
     for your shell, or ``rally --show-completion`` to print the script and
     install it yourself.

.. contents::
  :depth: 1
  :local:

.. make_cli_reference::
