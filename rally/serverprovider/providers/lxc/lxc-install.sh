#!/bin/sh

DEBIAN_FRONTEND='noninteractive' apt-get install -yq lxc

# configure virtual network

if /sbin/ip link show br0 2> /dev/null
then
    echo "br0 already exists"
else
    modprobe bridge
    ip link add br0 type bridge
    ip link set br0 up
    ip=`ip addr list dev eth0 | grep "inet "| awk '{ print $2}'`
    gw=`ip route | grep default | awk '{print $3}'`
    (
     ip addr del $ip dev eth0
     ip addr add $ip dev br0
     ip route add default via $gw
     ip link set eth0 master br0
    )
fi
