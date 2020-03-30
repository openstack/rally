cat <<EOF >/usr/local/bin/orchest_demo_scale.sh
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

    ip link add veth\${inst} type veth peer name veth\${peer}
    ip addr add 10.10.251.\${inst}/30 dev veth\${inst}
    ip link set veth\${inst} up

    ip netns add \${name}
    ip link set veth\${peer} netns \${name}
    ip netns exec \${name} ip addr add 10.10.251.\${peer}/30 dev veth\${peer}
    ip netns exec \${name} ip link set veth\${peer} up
    ip netns exec \${name} ip route add default via 10.10.251.\${inst}
    ip netns exec \${name} iptables -t nat -A POSTROUTING -o veth\${peer} -j MASQUERADE
}

mknat() {
    gen_bird_conf

    NOOFCUST=\$1
    CUSTID=1
    while [ \$CUSTID -le \$NOOFCUST ]
    do
        ID=\$(expr "\$CUSTID" - 1)
        INST=\$(expr 4 \* "\$ID" + 1)
        PEER=\$(expr 4 \* "\$ID" + 2)
        HEXCUSTID=\$(printf "%x\n" \$CUSTID)
        CUST="Customer-\$CUSTID"

        nat \$INST \$CUST \$PEER
        ip link add link eth0 name eth0.\$(expr 1000 + "\$CUSTID") type vlan id \$(expr 1000 + "\$CUSTID")
        ip link set eth0.\$(expr 1000 + "\$CUSTID") netns \$CUST
        ip netns exec \$CUST ifconfig eth0.\$(expr 1000 + "\$CUSTID") hw ether fa:16:3e:1b:a1:\$HEXCUSTID
        ip netns exec \$CUST /sbin/udhcpc -s /root/udhcpc-nat.conf -i eth0.\$(expr 1000 + "\$CUSTID")
        sleep 4
        gen_customer_bird_conf \$CUST \$(expr 1000 + "\$CUSTID") \$(expr 1000 + "\$CUSTID")
    	CUSTID=\$(expr "\$CUSTID" + 1)
    done
}

# Execute from here
if [ \$# -lt 1 ] ; then
    echo "\$0: NO_OF_CUSTOMERS <1-64>"
else
    mknat "\$@"
fi
EOF
chmod +x /usr/local/bin/orchest_demo_scale.sh
cat <<EOF >/usr/local/bin/scale_run_bird.sh
#

if [ \$# -lt 1 ] ; then
    echo "\$0: NO_OF_CUSTOMERS <1-64>"
else
    bird -c /etc/bird/bird-eth0.conf

    NOOFCUST=\$1
    CUSTID=1
    while [ \$CUSTID -le \$NOOFCUST ]
    do
        CUST="Customer-\$CUSTID"
        ip netns exec \$CUST  bird -c /etc/bird/bird-\$CUST.conf -P /tmp/bird-\$CUST.run -s /tmp/sock-\$CUST
	CUSTID=\$(expr "\$CUSTID" + 1)
    done
fi
EOF
chmod +x /usr/local/bin/scale_run_bird.sh
