FROM python:3.11-slim

RUN apt-get update && apt-get install --yes sudo vim git-core build-essential && \
    apt clean && \
    python3 -m pip --no-cache-dir install --upgrade pip setuptools && \
    useradd -u 65500 -m rally && \
    usermod -aG sudo rally && \
    echo "rally ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/00-rally-user && \
    mkdir /rally && chown -R rally:rally /rally

COPY ./ /rally/source
WORKDIR /rally/source

RUN python3 -m pip install . --constraint upper-constraints.txt --no-cache-dir && \
    python3 -m pip install pymysql psycopg2-binary --no-cache-dir && \
    mkdir -p /etc/rally && \
    echo "[database]" > /etc/rally/rally.conf && \
    echo "connection=sqlite:////home/rally/.rally/rally.db" >> /etc/rally/rally.conf

COPY ./etc/motd_for_docker /etc/motd
RUN echo '[ ! -z "$TERM" -a -r /etc/motd ] && cat /etc/motd' >> /etc/bash.bashrc

USER rally
ENV HOME /home/rally
RUN mkdir -p /home/rally/.rally && rally db recreate

# Docker volumes have specific behavior that allows this construction to work.
# Data generated during the image creation is copied to volume only when it's
# attached for the first time (volume initialization)
VOLUME ["/home/rally/.rally"]
ENTRYPOINT ["rally"]
