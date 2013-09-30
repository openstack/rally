#!/bin/sh

# Get the MAC address of the first interface.
mac=$(virsh dumpxml $1 | xml2  | awk -F= '$1 == "/domain/devices/interface/mac/@address" {print $2; exit}')
# Get the ip address assigned to this MAC from dnsmasq
ip=$(awk -vmac=$mac '$2 == mac {print $3}' /var/lib/libvirt/dnsmasq/default.leases )
echo $ip
