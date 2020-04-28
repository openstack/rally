#!/bin/bash

source openrc
echo "Uploading images required for testing..."
openstack image create --container-format bare --disk-format raw --file openwrtbras.img --public OpenWRTBras
openstack image create --container-format bare --disk-format raw --file openwrtnat.img --public OpenWRTNat
openstack image create --container-format bare --disk-format raw --file openwrtsi1.img --public OpenWRTSI1
openstack image create --container-format bare --disk-format raw --file openwrtsi2.img --public OpenWRTSI2
openstack image create --container-format bare --disk-format raw --file openwrtsi3.img --public OpenWRTSI3
openstack image create --container-format bare --disk-format raw --file cirros.img --public Cirros

echo "Creating flavors required for testing..."
openstack flavor create --ram 512 --disk 1 --vcpus 1 --public --id tiny tiny
openstack flavor create --ram 1024 --disk 5 --vcpus 1 --public --id small small
openstack flavor create --ram 1024 --disk 10 --vcpus 1 --public --id medium medium

echo "Creating a project for testing..."
openstack project create --domain admin_domain --description "Created for rally testing" --enable rally

echo "Creating a user for testing..."
openstack user create --domain admin_domain --project rally --password noir0123 --description "Created for rally testing" --enable rally
openstack role add --project rally --user rally Admin
openstack role add --project rally --user admin Member

echo "Creating access-network and nat-network for testing..."
./admin.sh

echo "Generating args.json file for testing..."
./generate_args_json_file.sh
echo "Please copy the generated args.json file into the testing directory"
