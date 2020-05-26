#!/bin/bash
source openrc
r1=$(openstack network list | grep 'ACCESS' | cut -d '|' -f2)
r2=$(openstack network list | grep 'INTERNET' | cut -d '|' -f2)
r3=$(openstack image list | grep 'OpenWRTBras' | cut -d '|' -f2)
r4=$(openstack image list | grep 'OpenWRTNat' | cut -d '|' -f2)
r5=$(openstack image list | grep 'OpenWRTSI1' | cut -d '|' -f2)
r6=$(openstack image list | grep 'OpenWRTSI2' | cut -d '|' -f2)
r7=$(openstack image list | grep 'OpenWRTSI3' | cut -d '|' -f2)
r8=$(openstack image list | grep 'cirros' | cut -d '|' -f2)
sed "s/par1/$r1/g" template.json > args.json
sed -i -e "s/par2/$r2/g" args.json
sed -i -e "s/par3/$r3/g" args.json
sed -i -e "s/par4/$r4/g" args.json
sed -i -e "s/par5/$r5/g" args.json
sed -i -e "s/par6/$r6/g" args.json
sed -i -e "s/par7/$r7/g" args.json
sed -i -e "s/par8/$r8/g" args.json
i=1
while IFS="=" read -r key value;do
	s=$value
        sed -i -e "s/argu$i/$s/g" args.json
        i=$((i+1));
done < conf.txt

