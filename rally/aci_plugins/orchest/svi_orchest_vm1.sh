ip addr add 10.10.10.1/24 dev eth1
ip addr add 10.10.10.2/24 dev eth1
ip addr add 10.10.10.3/24 dev eth1
ip addr add 10.10.10.4/24 dev eth1
ip addr add 10.10.10.5/24 dev eth1
#ip route add 192.168.20.0/24 via 192.168.10.1
#ip route add 10.10.20.0/24 via 192.168.10.1

cat <<EOF >/etc/bird/bird_svi.conf
router id 199.199.199.201;

#protocol kernel {
#        persist;                # Don't remove routes on bird shutdown
#        scan time 20;           # Scan kernel routing table every 20 seconds
#        export all;             # Default is export none
#}

# This pseudo-protocol watches all interface up/down events.
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

protocol bgp {
        description "My BGP uplink";
        local as 10;
        neighbor 192.168.10.199 as 1;
        ipv4 {
		import all;
        	export all;
	};
        source address 192.168.10.101;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink";
        local as 10;
        neighbor 192.168.10.200 as 1;
        ipv4 {
		import all;
	        export all;
	};
        source address 192.168.10.101;     # What local address we use for the TCP connection
}
EOF
