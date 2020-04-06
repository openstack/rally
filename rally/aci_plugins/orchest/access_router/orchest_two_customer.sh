#

set -x

access_site() {
    # site 1 pete2 2 10.2.1.1 10.10.0.0/16
    inst=$1
    name=$2
    peer=$3
    addr=$4
    route=$5

    ip link add veth${inst}1 type veth peer name veth${inst}2
    ip addr add 10.10.231.${inst}/30 dev veth${inst}1
    ip link set veth${inst}1 up

    ip netns add ${name}
    ip link set veth${inst}2 netns ${name}
    ip netns exec ${name} ip addr add 10.10.231.${peer}/30 dev veth${inst}2
    ip netns exec ${name} ip link set veth${inst}2 up

    ip netns exec ${name} ip tunnel add gre${inst} mode gre \
       local 10.10.231.${peer} remote 10.10.251.${peer} dev veth${inst}2
    ip netns exec ${name} ip addr add ${addr}/24 dev gre${inst}
    ip netns exec ${name} ip link set gre${inst} up

    ip netns exec ${name} ip route add 10.10.251.0/24 via 10.10.231.${inst}
    ip netns exec ${name} ip route add ${route} dev gre${inst}

    ip netns exec ${name} ip addr add 10.0.2.1/24 dev gre${inst}
}

delete_site() {
    # site 1 pete2
    inst=$1
    name=$2

    ip link del veth${inst}1   
    ip netns delete $name
}

mksites() {
    sysctl -w net.ipv4.ip_forward=1
    access_site 1 cats 2 10.0.1.1 default
    access_site 5 dogs 6 10.0.1.1 default
    route add -net 172.168.0.0/24 gw 10.10.240.2
    route add -net 10.10.251.0/24 gw 10.10.240.2
}

delsites() {
    delete_site 1 cats
    delete_site 5 dogs
}

"$@"
