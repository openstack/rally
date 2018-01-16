FROM ubuntu:16.04

RUN apt-get update && apt-get install --yes sudo python python-pip vim git-core && \
    pip install --upgrade pip && \
    useradd -u 65500 -m rally && \
    usermod -aG sudo rally && \
    echo "rally ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/00-rally-user

COPY . /home/rally/source
WORKDIR /home/rally/source

RUN pip install . --constraint upper-constraints.txt && \
    mkdir /etc/rally && \
    echo "[database]" > /etc/rally/rally.conf && \
    echo "connection=sqlite:////home/rally/data/rally.db" >> /etc/rally/rally.conf
RUN echo '[ ! -z "$TERM" -a -r /etc/motd ] && cat /etc/motd' \
            >> /etc/bash.bashrc; echo '\
╔═════════════════════════════════════════════════════════════════════════════╗\n\
║ Welcome to Rally Docker container!                                          ║\n\
║                                                                             ║\n\
║  WARNING: DO NOT OVERRIDE /home/rally DIRECTORY                             ║\n\
║                                                                             ║\n\
║  /home/rally/data      - a default place with rally database. Use it for    ║\n\
║      mounting own directories and synchronizing rally database.             ║\n\
║  /home/rally/source    - a directory with documentation, pre created tasks, ║\n\
║      sampes and source code                                                 ║\n\
║  /etc/rally/rally.conf - a default configuration file of rally. To override ║\n\
║      it, mount custom configuration file to /home/rally/.rally/rally.conf    ║\n\
║                                                                             ║\n\
║  Rally at readthedocs - http://rally.readthedocs.org                        ║\n\
║  How to contribute - http://rally.readthedocs.org/en/latest/contribute.html ║\n\
║  If you have any questions, you can reach the Rally team by:                ║\n\
║    * e-mail - openstack-dev@lists.openstack.org with tag [Rally] in subject ║\n\
║    * gitter - https://gitter.im/xRally/Lobby room                           ║\n\
║    * irc - "#openstack-rally" channel at freenode.net                       ║\n\
╚═════════════════════════════════════════════════════════════════════════════╝\n' > /etc/motd

USER rally
ENV HOME /home/rally
RUN mkdir /home/rally/data && rally db recreate

# Docker volumes have specific behavior that allows this construction to work.
# Data generated during the image creation is copied to volume only when it's
# attached for the first time (volume initialization)
VOLUME ["/home/rally/data"]
ENTRYPOINT ["rally"]
