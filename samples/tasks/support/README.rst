instance_linpack.sh
=============
instance_linpack.sh, will kick off a CPU intensive workload within a OpenStack instance.
This script will return the avg gflops and max gflops Linpack reports in a JSON format.
To run this workload, the VM must have linpack installed prior to running.

instance_dd_test.sh
=============
instance_dd_test.sh, will kick off a IO intensive workload within an OpenStack instance.
This script will return the write and read performance dd was able to achieve in a
JSON format.
