ip addr add 10.10.20.1/24 dev eth1
ip addr add 10.10.20.2/24 dev eth1
ip addr add 10.10.20.3/24 dev eth1
ip addr add 10.10.20.4/24 dev eth1
ip addr add 10.10.20.5/24 dev eth1
ip -6 addr add 2001:b20::1/128 dev eth1
ip -6 addr add 2001:b20::2/128 dev eth1
ip -6 addr add 2001:b20::3/128 dev eth1
ip -6 addr add 2001:b20::4/128 dev eth1
ip -6 addr add 2001:b20::5/128 dev eth1
#ip route add 192.168.10.0/24 via 192.168.20.1
#ip route add 10.10.10.0/24 via 192.168.20.1

cat <<EOF >/etc/bird/bird_svi.conf
log syslog all;
router id 199.199.199.202;

ipv4 table master4;
ipv6 table master6;

protocol device {
        scan time 10;           # Scan interfaces every 10 seconds
}

protocol static {
	ipv4;
        route 10.10.20.1/32 via 192.168.20.101;
        route 10.10.20.2/32 via 192.168.20.101;
        route 10.10.20.3/32 via 192.168.20.101;
        route 10.10.20.4/32 via 192.168.20.101;
        route 10.10.20.5/32 via 192.168.20.101;
}

protocol static {
        ipv6;
        route 2001:b20::1/128 via 2001:a20::65;
        route 2001:b20::2/128 via 2001:a20::65;
        route 2001:b20::3/128 via 2001:a20::65;
        route 2001:b20::4/128 via 2001:a20::65;
        route 2001:b20::5/128 via 2001:a20::65;
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local 192.168.20.101 as 20;
        neighbor 192.168.20.199 as 1;
	multihop;
        ipv4 {
		import all;
	        export all;
	};
        #source address 192.168.20.101;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv6";
        local 2001:a20::65 as 20;
        neighbor 2001:a20::c7 as 1;
        multihop;
        ipv6 {
                import all;
                export all;
        };
        #source address 2001:a20::65;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local 192.168.20.101 as 20;
        neighbor 192.168.20.200 as 1;
	multihop;
        ipv4 {
		import all;
	        export all;
	};
        #source address 192.168.20.101;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv6";
        local 2001:a20::65 as 20;
        neighbor 2001:a20::c8 as 1;
        multihop;
        ipv6 {
                import all;
                export all;
        };
        #source address 2001:a20::65;     # What local address we use for the TCP connection
}
EOF
