=============================================================================
Installation script: ``--pypi-mirror``, ``--package-mirror`` and ``--venv-mirror``
=============================================================================


Use case
--------

Installation is pretty easy when there is an Internet connection available.
And there is surely a number of OpenStack uses when whole environment is isolated.
In this case, we need somehow specify where installation script should take 
required libs and packages.


Problem description
-------------------

    #. Installation script can't work without direct Internet connection


Possible solution #1
--------------------

    #. Add ``--pypi-mirror`` option to installation script.
    #. Add ``--package-mirror`` option to installation script.
    #. Add ``--venv-mirror`` option to installation script.
