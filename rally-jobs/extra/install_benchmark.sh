#!/bin/sh

set -e

main() {
    cat > ~/dd_test.sh <<'EOF'
#!/bin/sh
time_seconds(){ (time -p $1 ) 2>&1 |awk '/real/{print $2}'; }
file=/tmp/test.img
c=1000 #1GB
write_seq_1gb=$(time_seconds "dd if=/dev/zero of=$file bs=1M count=$c")
read_seq_1gb=$(time_seconds "dd if=$file of=/dev/null bs=1M count=$c")
[ -f $file ] && rm $file

echo "{
    \"write_seq_1gb\": $write_seq_1gb,
    \"read_seq_1gb\": $read_seq_1gb
    }"
EOF

    chmod a+x ~/dd_test.sh
}

main
