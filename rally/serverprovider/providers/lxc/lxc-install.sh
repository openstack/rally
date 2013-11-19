#!/bin/sh

apt-get update
apt-get install -yq btrfs-tools

# configure btrfs storage
if [ -d "/var/lib/lxc" ]; then
    echo "Directory exists. Assume btrfs is available."
else
    mkdir /var/lib/lxc
    if df -t btrfs /var/lib/lxc > /dev/null 2>&1; then
        echo "Btrfs is already available."
    else
        echo "Creating btrfs volume."
        SIZE=`df -h /var | awk '/[0-9]%/{print $(NF-2)}'`
        truncate -s $SIZE /var/rally-btrfs-volume
        losetup /dev/loop0 /var/rally-btrfs-volume
        mkfs.btrfs /dev/loop0
        mount /dev/loop0 /var/lib/lxc
    fi
fi

# install lxc
DEBIAN_FRONTEND='noninteractive' apt-get install -yq lxc

#configure lxc
if [ -f "/etc/lxc/lxc.conf" ]; then
    CONFIG="/etc/lxc/lxc.conf"
else
    CONFIG="/etc/lxc/default.conf"
fi
cat > $CONFIG <<EOF
lxc.network.type=veth
lxc.network.link=br0
lxc.network.flags=up
EOF

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


