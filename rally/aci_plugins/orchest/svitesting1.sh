ip addr add 10.10.10.1/24 dev eth1
ip addr add 10.10.10.2/24 dev eth1
ip addr add 10.10.10.3/24 dev eth1
ip addr add 10.10.10.4/24 dev eth1
ip addr add 10.10.10.5/24 dev eth1
ip -6 addr add 2001:b10::1/128 dev eth1
ip -6 addr add 2001:b10::2/128 dev eth1
ip -6 addr add 2001:b10::3/128 dev eth1
ip -6 addr add 2001:b10::4/128 dev eth1
ip -6 addr add 2001:b10::5/128 dev eth1

cat <<EOF >/etc/bird/bird_svi.conf
log syslog all;
router id 199.199.199.201;

ipv4 table master4;
ipv6 table master6;

protocol device {
        scan time 10;           # Scan interfaces every 10 seconds
}

protocol static {
	ipv4;
        route 10.10.10.1/32 via 192.168.10.101;
        route 10.10.10.2/32 via 192.168.10.101;
        route 10.10.10.3/32 via 192.168.10.101;
        route 10.10.10.4/32 via 192.168.10.101;
        route 10.10.10.5/32 via 192.168.10.101;
}

protocol static {
        ipv6;
        route 2001:b10::1/128 via 2001:a10::65;
        route 2001:b10::2/128 via 2001:a10::65;
        route 2001:b10::3/128 via 2001:a10::65;
        route 2001:b10::4/128 via 2001:a10::65;
        route 2001:b10::5/128 via 2001:a10::65;
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local 192.168.10.101 as 10;
        neighbor 192.168.10.199 as 1;
	multihop;
        ipv4 {
		import all;
        	export all;
	};
        #source address 192.168.10.101;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local 192.168.10.101 as 10;
        neighbor 192.168.10.200 as 1;
	multihop;
        ipv4 {
		import all;
	        export all;
	};
        #source address 192.168.10.101;     # What local address we use for the TCP connection
}
EOF
