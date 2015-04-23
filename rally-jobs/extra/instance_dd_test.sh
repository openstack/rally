#!/bin/sh
time_seconds(){ (time -p $1 ) 2>&1 |awk '/real/{print $2}'; }
file=/tmp/test.img
c=${1:-$SIZE}
c=${c:-1000} #default is 1GB
write_seq=$(time_seconds "dd if=/dev/zero of=$file bs=1M count=$c")
read_seq=$(time_seconds "dd if=$file of=/dev/null bs=1M count=$c")
[ -f $file ] && rm $file

echo "{
    \"write_seq_${c}m\": $write_seq,
    \"read_seq_${c}m\": $read_seq
    }"
