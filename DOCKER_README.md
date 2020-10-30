# What is Rally/xRally

Rally is tool & framework that allows one to write simple plugins and combine
them in complex tests scenarios that allows to perform all kinds of testing!

# The purpose of xrally image or how to use it

**xrally** image bases on the latest LTS release of *ubuntu* which is 18.04 at
the moment. It provides raw xrally framework with only in-tree plugins (no
pre-installed plugins for Kubernetes, OpenStack, etc).

You can use this image as a base image and extend it with installation of
additional plugins:

    # It is an example of Dockerfile for xrally/xrally_docker image. There are
    #   only 2 critical lines: `FROM instruction` and the last line is a check
    #   for rally user is used.
    #
    # Tags of the image are the same as releases of xRally/Rally
    FROM xrally/xrally:3.2.0
    
    # "rally" user (which is selected by-default) is owner of "/rally" directory,
    #   so there is no need to call chown or switch the user
    COPY . /rally/xrally_docker
    WORKDIR /rally/xrally_docker
    
    # to install package system-wide, we need to temporary switch to root user
    USER root
    # disabling cache since we do not expect to install other packages
    RUN pip3 install . --no-cache-dir
    
    # switch back to rally user for avoid permission conflicts
    USER rally

or launch workloads based on in-tree plugins (see the next section for more
details)

# How to run xrally container

First of all, you need to pull the container. We suggest to use the last
tagged version:

    # pull the 3.2.0 image (the latest release at the point of writing the note)
    $ docker pull xrally/xrally:3.2.0

**WARNING: never attach folders and volumes to `/rally` inside the container. It can break everything.**

The default configuration file is located at `/etc/rally/rally.conf`. You
should not be aware of it. If you want to override some options, use
`/home/rally/.rally/rally.conf` location instead. Rally does not load all
configuration files, so the primary one will be used.

The default place for rally database file is `/home/rally/.rally/rally.sqlite`.
To make the storage persistent across all container runs, you may want to use
docker volumes or mount the directory.

* use docker volumes. It is the easiest way. You just need to do something like:

      $ docker volume create --name rally_volume
      $ docker run -v rally_volume:/home/rally/.rally xrally/xrally:3.2.0 env create --name "foo"


* mount outer directory inside the container

      # you can create directory in whatever you want to place, but you
      # may wish to make the data available for all users
      $ sudo mkdir /var/lib/rally_container
      
      # In order for the directory to be accessible by the Rally user
      # (uid: 65500) inside the container, it must be accessible by UID
      # 65500 *outside* the container as well, which is why it is created
      # in ``/var/lib/rally_container``. Creating it in your home directory is
      # only likely to work if your home directory has excessively open
      # permissions (e.g., ``0755``), which is not recommended.
      $ sudo chown 65500 /var/lib/rally_container

      # As opposed to mounting docker image, you must initialize rally database*
      $ docker run -v /var/lib/rally_container:/home/rally/.rally xrally/xrally db create

      # And finally, you can start doing your things.*
      $ docker run -v /var/lib/rally_container:/home/rally/.rally xrally/xrally env create --name "foo"

Have fun!

# Links

* Free software: Apache license
* Documentation: https://xrally.org
* Source: https://github.com/openstack/rally
* Bugs: https://bugs.launchpad.net/rally
* Gitter chat: https://gitter.im/xRally/Lobby
