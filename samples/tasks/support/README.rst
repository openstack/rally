instance_linpack.sh
=============
instance_linpack.sh, will kick off a CPU intensive workload within a OpenStack instance.
This script will return the avg gflops and max gflops Linpack reports in a JSON format.
To run this workload, the VM must have linpack installed prior to running.

instance_dd_test.sh
=============
instance_dd_test.sh, will kick off a IO intesnive workload within a OpenStack instance.
This script will return the write and read performance dd was able to achieve in a
JSON format.

ping_test.sh
=============
ping_test.sh, will ping "www.google.com" five times, confirming that IP connectivity to the instance works, IP connectivity from the instance to the Internet works, name resolution works and SSH key-injection is functional. Keep in mind that the Rally tasks apply a dedicated security group allowing access to all ports (1:65000) to the newly spawned instance(s), then use injected ssh keys to login and execute the ping command. Because of this, it is recommended that the image used by Rally not be Cirros or other image with known credentials (Ubuntu is preferred because it only allows ssh key-based access by default).
