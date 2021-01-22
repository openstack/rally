cat <<EOF >/usr/local/bin/orchest_svi_scale.sh
#!/bin/sh

ip addr add 11.10.\$1.1/24 dev eth1
ip addr add 11.10.\$1.2/24 dev eth1
ip addr add 11.10.\$1.3/24 dev eth1
ip addr add 11.10.\$1.4/24 dev eth1
ip addr add 11.10.\$1.5/24 dev eth1

ip -6 addr add 2001:b\$1::1/128 dev eth1
ip -6 addr add 2001:b\$1::2/128 dev eth1
ip -6 addr add 2001:b\$1::3/128 dev eth1
ip -6 addr add 2001:b\$1::4/128 dev eth1
ip -6 addr add 2001:b\$1::5/128 dev eth1

EOF
chmod +x /usr/local/bin/orchest_svi_scale.sh
cat <<EOF >/root/create_bird.sh
#!/bin/sh
cat <<EOF >/etc/bird/bird_svi_scale.conf
log syslog all;
router id 199.199.\$1.201;

ipv4 table master4;
ipv6 table master6;

protocol device {
        scan time 10;           # Scan interfaces every 10 seconds
}

protocol static {
	ipv4;
        route 11.10.\$1.1/32 via 192.168.\$1.101;
        route 11.10.\$1.2/32 via 192.168.\$1.101;
        route 11.10.\$1.3/32 via 192.168.\$1.101;
        route 11.10.\$1.4/32 via 192.168.\$1.101;
        route 11.10.\$1.5/32 via 192.168.\$1.101;
}

protocol static {
        ipv6;
        route 2001:b\$2::1/128 via 2001:a\$2::65;
	route 2001:b\$2::2/128 via 2001:a\$2::65;
	route 2001:b\$2::3/128 via 2001:a\$2::65;
	route 2001:b\$2::4/128 via 2001:a\$2::65;
	route 2001:b\$2::5/128 via 2001:a\$2::65;
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local as \$1;
        neighbor 192.168.\$1.199 as 1;
	multihop;
    	ipv4 {
            import all;
            export all;
        };
        source address 192.168.\$1.101;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv6";
        local as \$1;
        neighbor 2001:a\$2::c7 as 1;
        multihop;
        ipv6 {
            import all;
            export all;
        };
        source address 2001:a\$2::65;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local as \$1;
        neighbor 192.168.\$1.200 as 1;
    	ipv4 {
            import all;
            export all;
        };
        source address 192.168.\$1.101;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv6";
        local as \$1;
        neighbor 2001:a\$2::c8 as 1;
        multihop;
        ipv6 {
            import all;
            export all;
        };
        source address 2001:a\$2::65;     # What local address we use for the TCP connection
}
EOF
chmod +x /root/create_bird.sh
