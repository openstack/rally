rule="from {net} to {remote} lookup lxctun"
ip rule del $rule 2> /dev/null
ip rule add $rule
iptables -t nat -D POSTROUTING -s {net} -d {remote} -j ACCEPT 2> /dev/null
iptables -t nat -I POSTROUTING -s {net} -d {remote} -j ACCEPT
ip tun del t{remote}
ip tun add t{remote} mode ipip local {local} remote {remote}
ip link set t{remote} up
ip route add {remote}/32 dev t{remote} table lxctun
exit 0
