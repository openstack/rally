============================
OpenStack Certification Task
============================

How To Validate & Run Task
--------------------------

To validate task with your own parameters run:

.. code-block:: console

  $ rally task validate task.yaml --task-args-file task_arguments.yaml


To start task with your own parameters run:

.. code-block:: console

  $ rally task start task.yaml --task-args-file task_arguments.yaml


Task Arguments
--------------

File task_arguments.yaml contains all task options:

+------------------------+----------------------------------------------------+
| Name                   | Description                                        |
+------------------------+----------------------------------------------------+
| service_list           | List of services which should be tested            |
| smoke                  | Dry run without load from 1 user                   |
| use_existing_users     | In case of testing cloud with r/o Keystone e.g. AD |
| image_name             | Images name that exist in cloud                    |
| flavor_name            | Flavor name that exist in cloud                    |
| glance_image_location  | URL of image that is used to test Glance upload    |
| users_amount           | Expected amount of users                           |
| tenants_amount         | Expected amount of tenants                         |
| controllers_amount     | Amount of OpenStack API nodes (controllers)        |
+------------------------+----------------------------------------------------+

All options have default values, hoverer user should change them to reflect
configuration and size of tested OpenStack cloud.
