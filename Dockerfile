FROM ubuntu:16.04

RUN sed -i s/^deb-src.*// /etc/apt/sources.list

RUN apt-get update && apt-get install --yes sudo python python-pip vim git-core && \
    pip install --upgrade pip && \
    useradd -u 65500 -m rally && \
    usermod -aG sudo rally && \
    echo "rally ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/00-rally-user

COPY . /home/rally/source
COPY etc/motd /etc/motd
WORKDIR /home/rally/source

RUN pip install . --constraint upper-constraints.txt && \
    mkdir /etc/rally && \
    echo "[database]" > /etc/rally/rally.conf && \
    echo "connection=sqlite:////home/rally/data/rally.db" >> /etc/rally/rally.conf
RUN echo '[ ! -z "$TERM" -a -r /etc/motd ] && cat /etc/motd' >> /etc/bash.bashrc
# Cleanup pip
RUN rm -rf /root/.cache/

USER rally
ENV HOME /home/rally
RUN mkdir -p /home/rally/data && rally db recreate

# Docker volumes have specific behavior that allows this construction to work.
# Data generated during the image creation is copied to volume only when it's
# attached for the first time (volume initialization)
VOLUME ["/home/rally/data"]
ENTRYPOINT ["rally"]
