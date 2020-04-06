#!/bin/bash

set -x

function access_site {
    # site 1 pete2 2 10.2.1.1 10.10.0.0/16
    inst=$1
    name=$2
    peer=$3
    addr=$4
    route=$5

    ip link add veth${inst} type veth peer name veth${peer}
    ip addr add 10.10.231.${inst}/30 dev veth${inst}
    ip link set veth${inst} up

    ip netns add ${name}
    ip link set veth${peer} netns ${name}
    ip netns exec ${name} ip addr add 10.10.231.${peer}/30 dev veth${peer}
    ip netns exec ${name} ip link set veth${peer} up

    ip netns exec ${name} ip tunnel add gre${inst} mode gre \
       local 10.10.231.${peer} remote 10.10.251.${peer} dev veth${peer}
    ip netns exec ${name} ip addr add ${addr}/24 dev gre${inst}
    ip netns exec ${name} ip link set gre${inst} up

    ip netns exec ${name} ip route add 10.10.251.0/24 via 10.10.231.${inst}
    ip netns exec ${name} ip route add ${route} dev gre${inst}

    ip netns exec ${name} ip addr add 10.0.2.1/24 dev gre${inst}
}

function delete_site {
    # site 1 pete2
    inst=$1
    name=$2

    ip link del veth${inst}   
    ip netns delete $name
}

function mksites {
    sysctl -w net.ipv4.ip_forward=1

    NOOFCUST=$1
    for (( CUSTID=1; CUSTID<=$NOOFCUST; CUSTID++ ))
    do
        ID=$(expr "$CUSTID" - 1)
        INST=$(expr 4 \* "$ID" + 1)
        PEER=$(expr 4 \* "$ID" + 2)
        HEXCUSTID=$(printf "%x\n" $CUSTID)
        CUST="Customer-$CUSTID"

        access_site $INST $CUST $PEER 10.0.1.1 default
    done

    route add -net 172.168.0.0/24 gw 10.10.240.2
    route add -net 10.10.251.0/24 gw 10.10.240.2
}

function delsites {

    NOOFCUST=$1
    for (( CUSTID=1; CUSTID<=$NOOFCUST; CUSTID++ ))
    do
        ID=$(expr "$CUSTID" - 1)
        INST=$(expr 4 \* "$ID" + 1)
        CUST="Customer-$CUSTID"
        delete_site $INST $CUST
    done

}

function usage {
    echo "$0: [-h]"
    echo "  -h, --help                             Display help message"
    echo "  -d, --delete NO_OF_CUSTOMERS <1-64>    Delete Sites -d 2"
    echo "  -c, --create NO_OF_CUSTOMERS <1-64>    Create Sites -c 2"
}

#mksites "$@"
#delsites "$@"

function main {
    if [ $# -lt 2 ] ; then
        usage
    else

        while [ "$1" != "" ]; do
            case $1 in
                -h | --help )    usage
                                 exit
                                 ;;
                -d | --delete )  delsites ${@:2}
                                 exit
                                 ;;
                -c | --create )  mksites ${@:2}
                                 exit
                                 ;;
                * )              usage
                                 exit 1
            esac
            shift
        done
    fi
}

main $*

