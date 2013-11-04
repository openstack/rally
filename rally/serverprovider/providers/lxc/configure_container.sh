#!/bin/sh

CONTAINER=$1
NAMESERVER=$2

mkdir -p $CONTAINER/root/.ssh
cp ~/.ssh/authorized_keys $CONTAINER/root/.ssh/
echo "nameserver $NAMESERVER" > $CONTAINER/etc/resolv.conf
cat > $CONTAINER/etc/network/interfaces <<EOF
auto lo
iface lo inet loopback
EOF
