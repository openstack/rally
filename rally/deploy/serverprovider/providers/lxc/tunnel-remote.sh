ip tun del t{net.ip}
ip tun add t{net.ip} mode ipip local {local} remote {remote}
ip link set t{net.ip} up
ip route add {net} dev t{net.ip} src {local}
exit 0
