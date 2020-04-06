#!/bin/bash

set -x

install() {
    name=$1
    script=/bin/${1}.sh
    sed '/^# Execute from here/,$d' "$0" > "$script"
    echo '# Execute from here' >> "$script"
    echo "$name" '"$@"' >> "$script"
    chmod 755 "$script"
}

link_watcher() {
    ifname=$1
    exec 1>>/tmp/link_watcher 2>&1
    date
    if ! ip addr show dev "$ifname" | grep inet\  ; then
        /sbin/dhclient -1 "$ifname"
    fi
}

run_link_watcher() {
    install link_watcher "$@"
    (crontab -l | grep -v "/bin/link_watcher.sh" ; \
     echo "*/2 * * * * /bin/link_watcher.sh $@") | \
    crontab -
}

run_link_watcher_ns() {
    nsname=$1 ; shift
    install link_watcher "$@"
    (crontab -l | grep -v "/bin/link_watcher.sh" ; \
     echo "*/2 * * * * ip netns exec $nsname /bin/link_watcher.sh $@") | \
    crontab -
}

bird_watcher() {
    ifname="$1"
    localasn="$2"
    remoteasn="$3"
    peeraddr1="$4"
    peeraddr2="$5"
    route="$6"

    ifname=$(ifconfig | grep "^${ifname}" | cut -d' ' -f1)
    birdfile="/etc/bird/bird-${ifname}.conf"
    ipaddr=$(ip addr show dev "${ifname}" | awk '/inet / {split($2, a, "/"); print a[1]; }')
    lstaddr=$(grep '^ * ipaddr:' "${birdfile}" | cut -d' ' -f3)
    if [ -n "$ipaddr" -a "$ipaddr" != "$lstaddr" ] ; then
        cat >"$birdfile" <<EOF
/*
 * birdfile: $birdfile
 * ifname: $ifname
 * ipaddr: $ipaddr
 * peeraddr: $peeraddr1, $peeraddr2
 */
router id $ipaddr;
protocol kernel {
    scan time 1;
    export all;
    persist;
}
protocol device {
    scan time 1;
}
protocol static {
    route $route via $ipaddr;
}
protocol bgp {
    description "BGP: $ipaddr,$peeraddr1";
    source address $ipaddr;
    neighbor $peeraddr1 as $remoteasn;
    local as $localasn;
    import all;
    export all;
}
protocol bgp {
    description "BGP: $ipaddr,$peeraddr2";
    source address $ipaddr;
    neighbor $peeraddr2 as $remoteasn;
    local as $localasn;
    import all;
    export all;
}
EOF
        bird -c "$birdfile"
    fi
}

run_bird_watcher() {
    install bird_watcher "$@"
    (crontab -l | \
        grep -v "/bin/bird_watcher.sh" ; \
     echo "*/2 * * * * /bin/bird_watcher.sh $@") | \
    crontab -
}

run_bird_watcher_ns() {
    nsname=$1 ; shift
    install bird_watcher "$@"
    (crontab -l | \
        grep -v "/bin/bird_watcher.sh" ; \
     echo "*/2 * * * * ip netns exec $nsname /bin/bird_watcher.sh $@") | \
    crontab -
}

gen_bird_conf(){
myip=`ifconfig eth0 | grep "inet " | awk -F'[: ]+' '{ print $4 }'`

cat /etc/bird/bird-eth0.tmpl | sed -e "s/_MY_IP_TMPL/$myip/" >/etc/bird/bird-eth0.conf
}

cats_gen_bird_conf(){
myip=`ip netns exec cats ifconfig eth0.10 | grep "inet " | awk -F'[: ]+' '{ print $4 }'`

cat /etc/bird/bird-cats.tmpl | sed -e "s/_MY_IP_TMPL/$myip/" >/etc/bird/bird-cats.conf
}

site() {
    # site 1 pete2 10.2.1.1 23 25 10.10.0.0/16
    inst=$1
    name=$2
    addr=$3
    loc=$4
    rem=$5
    route=$6

    ip link add veth${inst}1 type veth peer name veth${inst}2
    ip addr add 10.10.${loc}${inst}.1/30 dev veth${inst}1
    ip link set veth${inst}1 up

    ip netns add ${name}
    ip link set veth${inst}2 netns ${name}
    ip netns exec ${name} ip addr add 10.10.${loc}${inst}.2/30 dev veth${inst}2
    ip netns exec ${name} ip link set veth${inst}2 up

    ip netns exec ${name} ip tunnel add gre${inst} mode gre \
       local 10.10.${loc}${inst}.2 remote 10.10.${rem}${inst}.2 dev veth${inst}2
    ip netns exec ${name} ip addr add ${addr}/24 dev gre${inst}
    ip netns exec ${name} ip link set gre${inst} up

    ip netns exec ${name} ip route add 10.10.${rem}${inst}.0/24 via 10.10.${loc}${inst}.1
    ip netns exec ${name} ip route add ${route} dev gre${inst}
}

nat() {
    # nat 1 pete1 2
    inst=$1
    name=$2
    peer=$3

    ip link add veth${inst}1 type veth peer name veth${inst}2
    ip addr add 10.10.251.${inst}/30 dev veth${inst}1
    ip link set veth${inst}1 up

    ip netns add ${name}
    ip link set veth${inst}2 netns ${name}
    ip netns exec ${name} ip addr add 10.10.251.${peer}/30 dev veth${inst}2
    ip netns exec ${name} ip link set veth${inst}2 up
    ip netns exec ${name} ip route add default via 10.10.251.${inst}
    ip netns exec ${name} iptables -t nat -A POSTROUTING -o veth${inst}2 -j MASQUERADE
}

mksites() {
# Access
    sysctl -w net.ipv4.ip_forward=1
    site 1 cats 10.0.1.1 23 25 default
    ip netns exec cats ip addr add 10.0.2.1/24 dev gre1
    site 2 dogs 10.0.1.1 23 25 default
    route add -net 172.168.0.0/24 gw 10.10.240.2
    route add -net 10.10.251.0/24 gw 10.10.240.2
#    run_bird_watcher eth1 10 1010 10.10.240.199 10.10.240.200 10.10.224.0/20
}

mkbras() {
    sysctl -w net.ipv4.ip_forward=1
    site 1 cats 10.1.1.1 25 23 10.0.0.0/16
    site 2 dogs 10.1.1.1 25 23 10.0.0.0/16

    gen_bird_conf
    ip link add link eth0 name eth0.10 type vlan id 10
    ip link set eth0.10 netns cats
    ip netns exec cats ifconfig eth0.10 hw ether fa:16:3e:bc:d5:38
    ip netns exec cats /sbin/dhclient -1 eth0.10
    sleep 4
    cats_gen_bird_conf

#    run_link_watcher_ns cats eth0.10

    ip link add link eth0 name eth0.20 type vlan id 20
    ip link set eth0.20 netns dogs
#    run_link_watcher_ns dogs eth0.20

#    run_bird_watcher eth0 1011 1010 10.10.240.199 10.10.240.200 10.10.248.0/21
#    run_bird_watcher_ns cats eth0.10 2011 2010 192.168.0.199 192.168.0.200 10.0.0.0/15
#    run_bird_watcher_ns dogs eth0.20 3011 3010 192.168.0.199 192.168.0.200 10.0.0.0/15
}

mknat() {
    sysctl -w net.ipv4.ip_forward=1
    nat 1 cats 2
    nat 5 dogs 6

    gen_bird_conf
    ip link add link eth0 name eth0.10 type vlan id 10
    ip link set eth0.10 netns cats
    ip netns exec cats ifconfig eth0.10 hw ether fa:16:3e:1b:a1:a1
    ip netns exec cats /sbin/dhclient -1 eth0.10
    sleep 4
    cats_gen_bird_conf
    
#    run_link_watcher_ns cats eth0.10

    ip link add link eth0 name eth0.20 type vlan id 20
    ip link set eth0.20 netns dogs
#    run_link_watcher_ns dogs eth0.20

#    run_bird_watcher eth0 1021 1020 10.10.241.199 10.10.241.200 10.10.248.0/21
#    run_bird_watcher_ns cats eth0.10 2021 2010 192.168.0.199 192.168.0.200 0/0
#    run_bird_watcher_ns dogs eth0.20 3021 3010 192.168.0.199 192.168.0.200 0/0
}

mkinet() {
    sysctl -w net.ipv4.ip_forward=1
    ip addr add 8.8.8.1/24 dev ens3
    ip addr add 8.8.8.2/24 dev ens3
    ip addr add 8.8.8.3/24 dev ens3
    ip addr add 8.8.8.3/24 dev ens3
    ip addr add 8.8.8.4/24 dev ens3
    ip addr add 8.8.8.5/24 dev ens3
    ip addr add 8.8.8.6/24 dev ens3
    ip addr add 8.8.8.7/24 dev ens3
    ip addr add 8.8.8.8/24 dev ens3
    route add -net 10.10.251.0/24 gw 10.10.241.2
    route add -net 173.168.0.0/24 gw 10.10.241.2

#    run_bird_watcher eth1 20 1020 10.10.241.199 10.10.241.200 0/0
}

# Execute from here
mkinet "$@"

