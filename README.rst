=====
Rally
=====

Introduction
------------

Rally is a Benchmark-as-a-Service project for OpenStack.

Rally is intended for providing the community with a benchmarking tool that is capable of performing **specific**, **complicated** and **reproducible** test cases on **real deployment** scenarios.

In the OpenStack ecosystem there are currently several tools that are helpful in carrying out the benchmarking process for an OpenStack deployment. To name a few, there are *DevStack* and *FUEL* which are intended for deploying and managing OpenStack clouds, the *Tempest* testing framework that validates OpenStack APIs, some tracing facilities like *Tomograph* with *Zipkin*, and so on. The challenge, however, is to compile all these tools together on a reproducible basis. That can be a rather difficult task since the number of compute nodes in a practical deployment can be really huge and also because one may be willing to use lots of different deployment strategies that pursue different goals (e.g., while benchmarking the Nova Scheduler, one usually does not care of virtualization details, but is more concerned with the infrastructure topologies; while in other specific cases it may be the virtualization technology that matters). Compiling a bunch of already existing benchmarking facilities into one project, making it flexible to user requirements and ensuring the reproducibility of test results, is exactly what Rally does.


Architecture
------------

Rally is basically split into 4 main components:

1. **Deployment Engine**, which is responsible for processing and deploying VM images (using DevStack or FUEL according to user’s preferences). The engine can do one of the following:

    + deploying an OS on already existing VMs;
    + starting VMs from a VM image with pre-installed OS and OpenStack;
    + delpoying multiply VMs inside each has OpenStack compute node based on a VM image.
2. **VM Provider**, which interacts with cloud provider-specific interfaces to load and destroy VM images;
3. **Benchmarking Tool**, which carries out the benchmarking process in several stages:

    + runs *Tempest* tests, reduced to 5-minute length (to save the usually expensive computing time);
    + runs the used-defined test scenarios (using the Rally testing framework);
    + collects all the test results and processes the by *Zipkin* tracer;
    + puts together a benchmarking report and stores it on the machine Rally was lauched on.
4. **Orchestrator**, which is the central component of the system. It uses the Deployment Engine to run control and compute nodes and to launch an OpenStack distribution and, after that, calls the Benchmarking Tool to start the benchmarking process.


Implementation details
----------------------

The only thing that has to be implemented by the Rally user in order for the system to work correctly is the *VM Provider* class. An object of this class will be used by the Orchestrator during the virtual machines initialization process and thus should have different implementations for each specific cloud provider (like Amazon or SoftLayer). Each *VM Provider* class implementation should inherit from the base *VM_Provider* class and implement 4 basic methods with the following signatures:

* *run_n_vms(image_id): vm_ids*
* *destroy_vms(vm_ids)*
* (optional) *load_image(image_file): image_id*
* (optional) *destroy_image(image_id)*
