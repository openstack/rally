cat <<EOF >/usr/local/bin/orchest_trunk_scale.sh
#
set -x
mknat() {
    ip route add 192.168.0.0/16 via 192.168.0.1
    NOOFVLANS=\$1
    VID=101
    VLANCOUNT=\$(expr "\$NOOFVLANS" + 100)
    while [ \$VID -le \$VLANCOUNT ]
    do
        HEXVID=\$(printf "%x\n" \$VID)
        ip netns add "cust-\$VID"
        ip link add link eth1 name eth1.\$VID type vlan id \$VID
        ip link set eth1.\$VID netns "cust-\$VID"
        ip netns exec "cust-\$VID" ifconfig eth1.\$VID hw ether fa:16:3e:1b:a1:\$HEXVID
        ip netns exec "cust-\$VID" /sbin/udhcpc -i eth1.\$VID
	    VID=\$(expr "\$VID" + 1)
    done
}
# Execute from here
if [ \$# -lt 1 ] ; then
    echo "\$0: NO_OF_CUSTOMERS <1-64>"
else
    mknat "\$@"
fi
EOF
chmod +x /usr/local/bin/orchest_trunk_scale.sh
cat <<EOF >/root/traffic.sh
#
set -x
    NOOFVLANS=\$1
    VID=101
    VLANCOUNT=\$(expr "\$NOOFVLANS" + 100)
    while [ \$VID -le \$VLANCOUNT ]
    do
        ip netns exec "cust-\$VID" ping -c 3 192.168.\$VID.101
        ping -c 3 192.168.\$VID.102
        ping -c 3 192.168.\$VID.101
	VID=\$(expr "\$VID" + 1)
    done
EOF
chmod +x /root/traffic.sh
