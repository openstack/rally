#!/bin/sh

DEVSTACK_REPO=$1
DEVSTACK_BRANCH=$2

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

useradd rally -m || echo "Warning: user rally is already exists" >&2
mkdir -m 700 /home/rally/.ssh || true
cp /root/.ssh/authorized_keys /home/rally/.ssh/ || true
chown -R rally /home/rally/.ssh || true
cat >> /etc/sudoers <<EOF
rally ALL=(root) NOPASSWD:ALL
Defaults:rally !requiretty
EOF

/sbin/iptables -F || echo "Warning: iptables not found" >&2
echo "export PATH=$PATH:/sbin/" >> /home/rally/.bashrc

cd /home/rally

if [ -d devstack ]; then
    cd devstack
    su rally -c "git pull"
else
    su rally -c "git clone -b $DEVSTACK_BRANCH $DEVSTACK_REPO"
fi

