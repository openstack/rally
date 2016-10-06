instance_linpack.sh
===================

instance_linpack.sh, will kick off a CPU intensive workload within a OpenStack instance.
This script will return the avg gflops and max gflops Linpack reports in a JSON format.
To run this workload, the VM must have linpack installed prior to running.

instance_test.sh
================

instance_test.sh loads server by spawning processes. Finally, it outputs
JSON data for HTML report charts, with values of CPU, memory and disk usage.
