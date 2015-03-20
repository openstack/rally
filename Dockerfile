FROM ubuntu:14.04
MAINTAINER Sergey Skripnick <sskripnick@mirantis.com>
COPY . /tmp/rally
RUN apt-get update && \
    apt-get -y install git python2.7 bash-completion python-dev libffi-dev \
                       libxml2-dev libxslt1-dev libssl-dev &&\
    cd /tmp/rally &&\
    ./install_rally.sh &&\
    sed 's|#*connection *=.*|connection = sqlite:////home/rally/.rally.sqlite|' -i /etc/rally/rally.conf &&\
    apt-get -y remove libssl-dev libffi-dev python-dev libxml2-dev \
                      libxslt1-dev build-essential gcc-4.8 python3 && \
    apt-get -y autoremove &&\
    apt-get clean &&\
    mv doc /usr/share/doc/rally &&\
    rm -fr /tmp/* &&\
    rm -rf /var/lib/apt/lists/* &&\
    update-alternatives --install /usr/bin/python python /usr/bin/python2.7 10 &&\
    useradd -u 65500 -m rally &&\
    ln -s /usr/share/doc/rally /home/rally/rally-docs
USER rally
CMD bash --login
ENV HOME /home/rally
WORKDIR /home/rally
