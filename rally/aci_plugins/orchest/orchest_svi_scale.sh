cat <<EOF >/usr/local/bin/orchest_svi_scale.sh
#!/bin/sh

ip addr add 11.10.\$1.1/24 dev eth0
ip addr add 11.10.\$1.2/24 dev eth0
ip addr add 11.10.\$1.3/24 dev eth0
ip addr add 11.10.\$1.4/24 dev eth0
ip addr add 11.10.\$1.5/24 dev eth0

ip route add 192.168.0.0/16 via 192.168.\$1.1
ip route add 11.10.0.0/16 via 192.168.\$1.1
EOF
chmod +x /usr/local/bin/orchest_svi_scale.sh
cat <<EOF >/root/create_bird.sh
#!/bin/sh
cat <<EOF >/etc/bird/bird_svi_scale.conf
router id 199.199.\$1.201;

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
        route 11.10.\$1.1/32 via 192.168.\$1.101;
        route 11.10.\$1.2/32 via 192.168.\$1.101;
        route 11.10.\$1.3/32 via 192.168.\$1.101;
        route 11.10.\$1.4/32 via 192.168.\$1.101;
        route 11.10.\$1.5/32 via 192.168.\$1.101;
}

protocol bgp {
        description "My BGP uplink";
        local as \$1;
        neighbor 192.168.\$1.199 as 1;
    	ipv4 {
            import all;
            export all;
        };
        source address 192.168.\$1.101;     # What local address we use for the TCP connection
}

protocol bgp {
        description "My BGP uplink";
        local as \$1;
        neighbor 192.168.\$1.200 as 1;
    	ipv4 {
            import all;
            export all;
        };
        source address 192.168.\$1.101;     # What local address we use for the TCP connection
}
EOF
chmod +x /root/create_bird.sh
