FROM ubuntu:16.04

RUN apt-get update && apt-get install --yes sudo python python-pip vim git-core && \
    pip install --upgrade pip && \
    useradd -u 65500 -m rally && \
    usermod -aG sudo rally && \
    echo "rally ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/00-rally-user

COPY . /home/rally/source
WORKDIR /home/rally/source

RUN pip install .
RUN echo '[ ! -z "$TERM" -a -r /etc/motd ] && cat /etc/motd' \
            >> /etc/bash.bashrc; echo '\
╔═════════════════════════════════════════════════════════════════════════════╗\n\
║ Welcome to Rally Docker container!                                          ║\n\
║  Rally pre created tasks, samples and docs are located at ~/source/         ║\n\
║  Rally configuration and DB are in ~/.rally/                                ║\n\
║  Rally at readthedocs - http://rally.readthedocs.org                        ║\n\
║  How to contribute - http://rally.readthedocs.org/en/latest/contribute.html ║\n\
║  If you have any questions, you can reach the Rally team by:                ║\n\
║    * e-mail - openstack-dev@lists.openstack.org with tag [Rally] in subject ║\n\
║    * irc - "#openstack-rally" channel at freenode.net                       ║\n\
╚═════════════════════════════════════════════════════════════════════════════╝\n' > /etc/motd

USER rally
ENV HOME /home/rally
WORKDIR /home/rally
RUN mkdir .rally && \
    cp ./source/etc/rally/rally.conf.sample .rally/rally.conf && \
    sed -i "s|#connection *=.*|connection = \"sqlite:////home/rally/.rally/rally.db\"|" .rally/rally.conf && \
    rally db recreate

# Docker volumes have specific behavior that allows this construction to work.
# Data generated during the image creation is copied to volume only when it's
# attached for the first time (volume initialization)
VOLUME ["/home/rally"]
ENTRYPOINT ["rally"]
