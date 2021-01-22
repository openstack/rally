ip link add veth11 type veth peer name veth12
ip addr add 10.10.251.1/30 dev veth11
ip -6 addr add 2001:251::1/128 dev veth11
ip link set veth11 up

cat <<EOF >/root/create_bird.sh
#!/bin/sh
cat <<EOF >/etc/bird/bird_l3out.conf
log syslog all;
router id 199.199.199.202;

ipv4 table master4;
ipv6 table master6;

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
        route 10.10.251.0/24 via \$1;
}

protocol static {
        ipv6;
        route 2001:251::/64 via \$2;
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local as 1020;
        neighbor 173.168.0.199 as 1;
	multihop;
	ipv4 {
	        import all;
	        export all;
	};
        source address \$1;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv6";
        local as 1020;
        neighbor 2001:ad::c7 as 1;
        multihop;
        ipv6 {
                import all;
                export all;
        };
        source address \$2;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv4";
        local as 1020;
        neighbor 173.168.0.200 as 1;
	multihop;
	ipv4 {
	        import all;
	        export all;
	};
        source address \$1;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink for IPv6";
        local as 1020;
        neighbor 2001:ad::c8 as 1;
        multihop;
        ipv6 {
                import all;
                export all;
        };
        source address \$2;     # What local address we use for the TCP connection
}
EOF
