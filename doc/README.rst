========================
Content of doc directory
========================

This directory contains everything that is related to documentation and
bureaucracy. You can find here 4 subdirectories:


feature_request
~~~~~~~~~~~~~~~

If some use case is not covered by Rally, it is the right place to request it.
To request new feature you should just explain use case on high level.
Technical details and writing code are not required at all.


source
~~~~~~

Source of documentation. Latest version of documentation_.

.. _documentation: https://rally.readthedocs.io/en/latest/


specs
~~~~~

Specs are detailed description of proposed changes in project.
Usually they answer on what, why, how to change in project and who is going to work on change.


user_stories
~~~~~~~~~~~~

Place where you can share any of Rally user experience. E.g. fixing some bugs,
measuring performance of different architectures or comparing different
hardware and so on..


release_notes
~~~~~~~~~~~~~

Notes for all releases since 1.0.0 are written in a single CHANGELOG.rst_ file
in the root of the repository. The changelog.rst symlink here is what pulls it
into the built documentation.

Releases older than 1.0.0 have a separate page each, you could find them in
archive_.

.. _CHANGELOG.rst: https://github.com/openstack/rally/blob/master/CHANGELOG.rst
.. _archive: https://github.com/openstack/rally/tree/master/doc/release_notes/archive
