#!/bin/bash

source dual-demo-functions.sh

    PROJECT="admin"

    create_network $PROJECT "ACCESS" "--provider:network_type vlan --shared --apic:svi True --apic:bgp_enable True \
    --apic:bgp_asn 1010 --apic:distinguished_names type=dict ExternalNetwork=uni/tn-common/out-Access-Out/instP-data_ext_pol"; \
    NET_ID=${CREATED_NETWORKS[-1]}
    create_subnet $PROJECT $NET_ID "172.168.0.1" "172.168.0.0/24" "--host-route destination=10.108.1.0/24,gateway=172.168.0.1 \
    --host-route destination=10.10.240.0/24,gateway=172.168.0.1 --host-route destination=10.10.224.0/22,gateway=172.168.0.1"; \
    SUB_ID=${CREATED_SUBNETS[-1]}
    create_v6subnet $PROJECT $NET_ID "2001:ac::1" "2001:ac::/64" "--ipv6-ra-mode dhcpv6-stateful --ipv6-address-mode dhcpv6-stateful"; \
    SUBV6_ID=${CREATED_SUBNETS[-1]}
    create_svi_ports $PROJECT $NET_ID $SUB_ID $SUBV6_ID "172.168.0" "2001:ac" 2

    create_network $PROJECT "INTERNET" "--provider:network_type vlan --shared --apic:svi True --apic:bgp_enable True \
    --apic:bgp_asn 1020 --apic:distinguished_names type=dict ExternalNetwork=uni/tn-common/out-Internet-Out/instP-data_ext_pol"; \
    NET_ID=${CREATED_NETWORKS[-1]}
    create_subnet $PROJECT $NET_ID "173.168.0.1" "173.168.0.0/24" "--host-route destination=10.108.1.0/24,gateway=173.168.0.1 \
    --host-route destination=10.10.241.0/24,gateway=173.168.0.1"; \
    SUB_ID=${CREATED_SUBNETS[-1]}
    create_v6subnet $PROJECT $NET_ID "2001:ad::1" "2001:ad::/64" "--ipv6-ra-mode dhcpv6-stateful --ipv6-address-mode dhcpv6-stateful";\
    SUBV6_ID=${CREATED_SUBNETS[-1]}
    create_svi_ports $PROJECT $NET_ID $SUB_ID $SUBV6_ID "173.168.0" "2001:ad" 2

