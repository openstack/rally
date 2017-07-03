#!/bin/bash
samples_unpacked_dir=$(dirname "${BASH_SOURCE[0]}")
dirs=( $(find "$samples_unpacked_dir" -maxdepth 1 -type d -printf '%P\n') )
samples=~/.rally/plugins/samples
mkdir -p "$samples"
for dir in "${dirs[@]}"; do
    cp -r $samples_unpacked_dir/$dir $samples
    printf "\nTo test $dir plugin run next command:\n"
    printf "rally task start --task $samples/$dir/test_$dir.yaml\n"
    printf "or \nrally task start --task $samples/$dir/test_$dir.json\n"
done
