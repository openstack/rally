cat <<EOF >/usr/local/bin/orchest_nat.sh
#

set -x

gen_bird_conf(){
    myip=\`ifconfig eth0 | grep "inet " | awk -F'[: ]+' '{ print \$4 }'\`
    cat /etc/bird/bird-eth0.tmpl | sed -e "s/_MY_IP_TMPL/\$myip/" >/etc/bird/bird-eth0.conf
}

gen_customer_bird_conf(){
    #gen_customer_bird_conf cats 10 2010
    name=\$1
    vlanid=\$2
    asn=\$3

    myip=\`ip netns exec \$name ifconfig eth0.\$vlanid | grep "inet " | awk -F'[: ]+' '{ print \$4 }'\`
    cat /etc/bird/bird-cats.tmpl | sed -e "s/_MY_IP_TMPL/\$myip/" | sed -e "s/2010/\$asn/" >/etc/bird/bird-\$name.conf
}

nat() {
    # nat 1 pete1 2
    inst=\$1
    name=\$2
    peer=\$3

    ip link add veth\${inst}1 type veth peer name veth\${inst}2
    ip addr add 10.10.251.\${inst}/30 dev veth\${inst}1
    ip link set veth\${inst}1 up

    ip netns add \${name}
    ip link set veth\${inst}2 netns \${name}
    ip netns exec \${name} ip addr add 10.10.251.\${peer}/30 dev veth\${inst}2
    ip netns exec \${name} ip link set veth\${inst}2 up
    ip netns exec \${name} ip route add default via 10.10.251.\${inst}
    ip netns exec \${name} iptables -t nat -A POSTROUTING -o veth\${inst}2 -j MASQUERADE
}

mknat() {
    sysctl -w net.ipv4.ip_forward=1
    nat 1 cats 2

    gen_bird_conf
    ip link add link eth0 name eth0.10 type vlan id 10
    ip link set eth0.10 netns cats
    ip netns exec cats ifconfig eth0.10 hw ether \$1
    ip netns exec cats /sbin/udhcpc -s /root/udhcpc-nat.conf -i eth0.10
    sleep 4
    gen_customer_bird_conf cats 10 2010
}

# Execute from here
mknat "\$@"
EOF
chmod +x /usr/local/bin/orchest_nat.sh
