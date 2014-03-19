rule="from {net} to {remote} lookup lxctun"
ip rule del $rule 2> /dev/null || true
ip rule add $rule
if ! ip tun list | egrep "^t{net.ip}" ; then
    iptables -t nat -I POSTROUTING -s {net} -d {remote} -j ACCEPT
    ip tun add t{remote} mode ipip local {local} remote {remote}
    ip link set t{remote} up
    ip route add {remote}/32 dev t{remote} table lxctun
fi
