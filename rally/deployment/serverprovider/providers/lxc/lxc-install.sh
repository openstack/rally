#!/bin/sh

apt-get update
apt-get install -yq btrfs-tools

#configure networking
[ grep lxctun /etc/iproute2/rt_tables ] || echo "16 lxctun" >> /etc/iproute2/rt_tables

sysctl net.ipv4.conf.all.rp_filter=0
sysctl net.ipv4.conf.default.rp_filter=0

for iface in `ls /sys/class/net/ | grep -v "lo"` ; do
    sysctl net.ipv4.conf."$iface".rp_filter=0 > /dev/null 2> /dev/null || true
done


# configure btrfs storage
if [ ! -d "/var/lib/lxc" ]; then
    mkdir /var/lib/lxc
    if ! df -t btrfs /var/lib/lxc > /dev/null 2>&1; then
        echo "Creating btrfs volume."
        SIZE=`df -h /var | awk '/[0-9]%/{print $(NF-2)}'`
        truncate -s $SIZE /var/rally-btrfs-volume
        LOOPDEV=`losetup -f`
        losetup $LOOPDEV /var/rally-btrfs-volume
        mkfs.btrfs $LOOPDEV
        mount $LOOPDEV /var/lib/lxc
    fi
fi

# install lxc
if [ dpkg -s lxc > /dev/null 2>&1 ]; then
 echo "Lxc already installed"
else
 DEBIAN_FRONTEND='noninteractive' apt-get install -yq lxc
 service lxc stop
 cat /tmp/.lxc_default >> /etc/default/lxc || true
 rm /tmp/.lxc_default || true
 service lxc start
fi
