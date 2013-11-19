#!/bin/sh

if command -v apt-get
    then
        apt-get update
        apt-get install -y --force-yes git sudo
elif command -v yum
    then
        yum install -y git sudo
else
    echo "Unable to install git and sudo"
    exit 2
fi

useradd rally -m
mkdir -m 700 /home/rally/.ssh
cp /root/.ssh/authorized_keys /home/rally/.ssh/
chown -R rally /home/rally/.ssh
cat >> /etc/sudoers <<EOF
rally ALL=(root) NOPASSWD:ALL
Defaults:rally !requiretty
EOF

/sbin/iptables -F
echo "export PATH=$PATH:/sbin/" >> /home/rally/.bashrc
chmod 440 /etc/sudoers.d/42_rally

exit 0
