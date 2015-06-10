#!/bin/sh
ping_res=$(ping -c 5 -q www.google.com | awk -F"," '{print $3}'| sed 's/%//'| grep packet| awk '{print $1}')
echo "{\"packet_loss\": $ping_res}"
