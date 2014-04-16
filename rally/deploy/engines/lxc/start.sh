#!/bin/sh

IP=`ip -4 address show eth0 | grep inet | awk '{print $2}' | cut -d '/' -f -1`
if [ -z $IP ]
then
    echo "Error: ip address is not set" 1>&2
    exit 1
fi

sed -i "s/^my_ip.*/my_ip = $IP/" /etc/nova/nova.conf

for SERVICE in nova-compute nova-network ; do
 start-stop-daemon -S -b --name $SERVICE --exec \
    /usr/local/bin/$SERVICE -- \
    --config-file /etc/nova/nova.conf \
    --logfile /var/log/nova-$SERVICE
done
