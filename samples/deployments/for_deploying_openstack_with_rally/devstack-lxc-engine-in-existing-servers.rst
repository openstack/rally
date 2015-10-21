Devstack-LXC-engine-in-dummy
============================

How to deploy cloud

Assume we have 1 server with lots of RAM and linux. It is strongly recommended
to use btrfs for lxc containers. Please note root access is mandatory.

So, we need one controller node and 64 computes. All nodes can be deployed by DevstackEngine


Controller
----------
::

    "type": "DevstackEngine",
    "local_conf": {
        "MULTI_HOST": "1",
        "VIRT_DRIVER": "fake",
        "ENABLED_SERVICES+": ",-n-cpu",
    },

Look carefully at ENABLED_SERVICES. Such syntax is translated to 'ENABLED_SERVICES+=,-n-cpu'
in local.conf. This means 'remove n-cpu from ENABLED_SERVICES'.

Please note: VIRT_DRIVER=fake on controller node is mandatory.

This node should be deployed in lxc container, so we use the LxcProvider::

    "provider": {
        "type": "LxcProvider",
        "containers_per_host": 1,
        "container_name_prefix": "controller",
        "distribution": "ubuntu",
        "host_provider": {
            "name": "ExistingServers",
            "credentials": [{"user": "root", "host": "localhost"}]
        }
    }

ExistingServers is used as sub-provider, because we already have a linux box (localhost).


Computes
--------

Next we need 64 compute nodes. This can be done by LxcEngine. LxcEngine deploys the first
compute instance via the devstack engine, then makes N clones using lxc-clone.

::

    "type": "LxcEngine",
    "distribution": "ubuntu",
    "container_name": "devstack-compute",
    "nodes_per_server": 64,
    "provider": {
        "type": "ExistingServers",
        "credentials": [{"user": "root", "host": "localhost"}]
    },
    "engine": {
        "name": "DevstackEngine",
        "local_conf": {
            "VIRT_DRIVER": "fake",
            "DATABASE_TYPE": "mysql",
            "MYSQL_HOST": "{controller_ip}",
            "RABBIT_HOST": "{controller_ip}",
            "GLANCE_HOSTPORT": "{controller_ip}:9292",
            "ENABLED_SERVICES": "n-cpu,n-net",
        }
    }

This is very similar to LxcProvider configuration: ExistingServers as sub-provider and DevstackEngine
as sub-engine. Please note controller's ip isn't known at the moment of configuratoin, so
MultihostEngine will replace {contoller_ip} pattern with actual address after first node is deployed.

Also DATABASE_DRIVER is necessary because of bug in devstack.


MultihostEngine
---------------

The MultihostEngine configuration contains sections for configuring the controller and compute
nodes, for example::

    "type": "MultihostEngine",
    "controller": {
        // CONTROLLER CONFIGURATION HERE
    }
    "nodes": [
        {
            // NODES CONFIGURATION HERE
        }
    ]

Here is an example of a complete configuration file, assembled from the snippets above::

    {
        "type": "MultihostEngine",
        "controller": {
            "type": "DevstackEngine",
            "local_conf": {
                "MULTI_HOST": "1",
                "VIRT_DRIVER": "fake",
                "API_RATE_LIMIT": "False",
                "ENABLED_SERVICES+": ",-n-cpu",
                "SCREEN_LOGDIR": "$DEST/logs/screen"
            },
            "provider": {
                "type": "LxcProvider",
                "containers_per_host": 1,
                "container_name_prefix": "controller",
                "distribution": "ubuntu",
                "host_provider": {
                    "type": "ExistingServers",
                    "credentials": [{"user": "root", "host": "localhost"}]
                }
            }
        },
        "nodes": [
            {
                "type": "LxcEngine",
                "distribution": "ubuntu",
                "container_name": "devstack-compute",
                "nodes_per_server": 64,
                "provider": {
                    "type": "ExistingServers",
                    "credentials": [{"user": "root", "host": "localhost"}]
                },
                "engine": {
                    "name": "DevstackEngine",
                    "local_conf": {
                        "VIRT_DRIVER": "fake",
                        "DATABASE_TYPE": "mysql",
                        "MYSQL_HOST": "{controller_ip}",
                        "RABBIT_HOST": "{controller_ip}",
                        "GLANCE_HOSTPORT": "{controller_ip}:9292",
                        "API_RATE_LIMIT": "False",
                        "ENABLED_SERVICES": "n-cpu,n-net",
                        "SCREEN_LOGDIR": "$DEST/logs/screen"
                    }
                }
            }
        ]
    }

Please note each compute node uses from 90M to 120M of RAM.


SSH Access
----------

The target host (localhost in this case) should be accessible via a password-less ssh key.
If necessary ssh keys can be setup as follows::

    $ cd
    $ ssh-keygen  # just hit enter when asked for password
    $ sudo mkdir /root/.ssh
    $ sudo cat .ssh/id_rsa.pub >> /root/.ssh/authorized_keys
    $ ssh root@localhost
    # id
    uid=0(root) gid=0(root) groups=0(root)

Rally uses ssh for communication as most deployments are spread across multiple nodes.


Tunneling
---------

Both LxcProvider and LxcEngine have 'tunnel_to' configuration option. This is used
for cases when using more then one hardware nodes::

                                                           +--------------------------+
                                                           |         computes-1       |
                                                           |                          |
                                           +---------------| lxcbr0  10.100.1.0/24    |
 +--------------------------+              |               | eth0    192.168.10.1     |
 |                          |              |               |                          |
 |        rally             |              |               +--------------------------+
 |                          |---------+    |
 |   eth0      10.1.1.20    |         |    |
 |                          |         v    v               +--------------------------+
 +--------------------------+     +---------------+        |         computes-2       |
                                  |               |        |                          |
                                  |               |<-------| lxcbr0  10.100.2.0/24    |
 +--------------------------+     |  IP NETWORK   |        | eth0    192.168.10.2     |
 |        controller        |     |               |        |                          |
 |                          |---->|               |        +--------------------------+
 |       eth0  192.168.1.13 |     +---------------+
 |                          |              ^
 |tunnels:                  |              |                        ...........
 |10.100.1/24->192.168.10.1 |              |
 |10.100.2/24->192.168.10.2 |              |
 |10.100.x/24->192.168.10.x |              |               +--------------------------+
 |                          |              |               |         computes-n       |
 +--------------------------+              |               |                          |
                                           +---------------| lxcbr0  10.100.x.0/24    |
                                                           | eth0    192.168.10.x     |
                                                           |                          |
                                                           +--------------------------+

Each box is a separate hardware node. All nodes can access each other via ip, but lxc containers
are only connected to isolated virtual networks within each node. For communication between
lxc containers ipip tunneling is used. In this example we need to connect all the lxc-containers
to controller node. So, we add the option "tunnel_to": ["192.168.1.13"]::

    "type": "LxcEngine",
    "distribution": "ubuntu",
    "container_name": "devstack-compute",
    "nodes_per_server": 64,
    "start_lxc_network": "10.100.1.0/24",
    "tunnel_to": ["10.1.1.20", "192.168.1.13"]:
    "provider": {
        //SOME PROVIDER WHICH RETURNS N NODES
        //LxcEngine will create internal lxc
        //network starts from 10.100.1.0/24 (see start_lxc_network)
        //e.g 10.100.1.0/24, 10.100.2.0/24, ...,  10.100.n.0/24
    },
    "engine": {
        "name": "DevstackEngine",
        "local_conf": {
            "VIRT_DRIVER": "fake",
            "DATABASE_TYPE": "mysql",
            "MYSQL_HOST": "{controller_ip}",
            "RABBIT_HOST": "{controller_ip}",
            "GLANCE_HOSTPORT": "{controller_ip}:9292",
            "ENABLED_SERVICES": "n-cpu,n-net",
        }
    }
