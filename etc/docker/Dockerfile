FROM ubuntu:18.04

RUN sed -i s/^deb-src.*// /etc/apt/sources.list

RUN apt-get update && apt-get install --yes sudo python3-dev python3-pip vim git-core && \
    pip3 install --upgrade pip && \
    useradd -u 65500 -m rally && \
    usermod -aG sudo rally && \
    echo "rally ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/00-rally-user && \
    mkdir /rally && chown -R rally:rally /rally

COPY ./src /rally/source
COPY ./motd /etc/motd
WORKDIR /rally/source

RUN pip3 install . --constraint upper-constraints.txt && \
    pip3 install pymysql && \
    pip3 install psycopg2-binary && \
    mkdir -p /etc/rally && \
    echo "[database]" > /etc/rally/rally.conf && \
    echo "connection=sqlite:////home/rally/.rally/rally.db" >> /etc/rally/rally.conf
RUN echo '[ ! -z "$TERM" -a -r /etc/motd ] && cat /etc/motd' >> /etc/bash.bashrc
# Cleanup pip
RUN rm -rf /root/.cache/

USER rally
ENV HOME /home/rally
RUN  mkdir -p /home/rally/.rally && rally db recreate

# Docker volumes have specific behavior that allows this construction to work.
# Data generated during the image creation is copied to volume only when it's
# attached for the first time (volume initialization)
VOLUME ["/home/rally/.rally"]
ENTRYPOINT ["rally"]
