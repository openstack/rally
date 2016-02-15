..
      Copyright 2015 Mirantis Inc. All Rights Reserved.

      Licensed under the Apache License, Version 2.0 (the "License"); you may
      not use this file except in compliance with the License. You may obtain
      a copy of the License at

          http://www.apache.org/licenses/LICENSE-2.0

      Unless required by applicable law or agreed to in writing, software
      distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
      WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
      License for the specific language governing permissions and limitations
      under the License.

.. _tutorial_step_0_installation:

Step 0. Installation
====================

The easiest way to install Rally is by running its `installation script
<https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh>`_:

.. code-block:: bash

    wget -q -O- https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh | bash
    # or using curl:
    curl https://raw.githubusercontent.com/openstack/rally/master/install_rally.sh | bash

If you execute the script as regular user, Rally will create a new
virtual environment in ``~/rally/`` and install in it Rally, and will
use `sqlite` as database backend. If you execute the script as root,
Rally will be installed system wide. For more installation options,
please refer to the :ref:`installation <install>` page.

**Note:** Rally requires Python version 2.7 or 3.4.

Now that you have rally installed, you are ready to start :ref:`benchmarking OpenStack with it <tutorial_step_1_setting_up_env_and_running_benchmark_from_samples>`!
