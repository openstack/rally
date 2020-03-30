cat <<EOF >/usr/local/bin/orchest_bras.sh
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

site() {
    # site 1 pete2 2 10.2.1.1 10.10.0.0/16
    inst=\$1
    name=\$2
    peer=\$3
    addr=\$4
    route=\$5

    ip link add veth\${inst}1 type veth peer name veth\${inst}2
    ip addr add 10.10.251.\${inst}/30 dev veth\${inst}1
    ip link set veth\${inst}1 up

    ip netns add \${name}
    ip link set veth\${inst}2 netns \${name}
    ip netns exec \${name} ip addr add 10.10.251.\${peer}/30 dev veth\${inst}2
    ip netns exec \${name} ip link set veth\${inst}2 up

    ip netns exec \${name} ip tunnel add gre\${inst} mode gre \
       local 10.10.251.\${peer} remote 10.10.231.\${peer} dev veth\${inst}2
    ip netns exec \${name} ip addr add \${addr}/24 dev gre\${inst}
    ip netns exec \${name} ip link set gre\${inst} up

    ip netns exec \${name} ip route add 10.10.231.0/24 via 10.10.251.\${inst}
    ip netns exec \${name} ip route add \${route} dev gre\${inst}
}

mkbras() {
    sysctl -w net.ipv4.ip_forward=1
    site 1 cats 2 10.1.1.1 10.0.0.0/16
    site 5 dogs 6 10.1.1.1 10.0.0.0/16
    gen_bird_conf

    ip link add link eth0 name eth0.10 type vlan id 10
    ip link set eth0.10 netns cats
    ip netns exec cats ifconfig eth0.10 hw ether \$1
    ip netns exec cats /sbin/udhcpc -i eth0.10
    sleep 4
    gen_customer_bird_conf cats 10 2010

    ip link add link eth0 name eth0.20 type vlan id 20
    ip link set eth0.20 netns dogs
    ip netns exec dogs ifconfig eth0.20 hw ether \$2
    ip netns exec dogs /sbin/udhcpc -i eth0.20
    sleep 4
    gen_customer_bird_conf dogs 20 3010
}

# Execute from here
mkbras "\$@"
EOF
chmod +x /usr/local/bin/orchest_bras.sh
cat <<EOF >/usr/local/bin/run_bird
bird -c /etc/bird/bird-eth0.conf
ip netns exec cats bird -c /etc/bird/bird-cats.conf -P /tmp/bird-cats.run -s /tmp/sock-cats
ip netns exec dogs bird -c /etc/bird/bird-dogs.conf -P /tmp/bird-dogs.run -s /tmp/sock-dogs
EOF
chmod +x /usr/local/bin/run_bird
