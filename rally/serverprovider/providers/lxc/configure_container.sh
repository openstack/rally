#!/bin/sh

CONTAINER=$1
IP=$2
NETMASK=$3
GATEWAY=$4
NAMESERVER=$5

mkdir -p $CONTAINER/root/.ssh
cp ~/.ssh/authorized_keys $CONTAINER/root/.ssh/
echo "nameserver $NAMESERVER" > $CONTAINER/etc/resolv.conf
cat > $CONTAINER/etc/network/interfaces <<EOF
auto lo
auto eth0
iface lo inet loopback
iface eth0 inet static
 address $IP
 netmask $NETMASK
 gateway $GATEWAY
EOF
