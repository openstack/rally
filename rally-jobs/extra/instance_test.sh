#!/bin/sh
# Load server and output JSON results ready to be processed
# by Rally scenario

get_used_cpu_percent() {
    echo 100 $(top -b -n 1 | grep -i CPU | head -n 1 | awk '{print $8}' | tr -d %) - p | dc
}

get_used_ram_percent() {
    local total=$(free | grep Mem: | awk '{print $2}')
    local used=$(free | grep -- -/+\ buffers | awk '{print $3}')
    echo ${used} 100 \* ${total} / p | dc
}

get_used_disk_percent() {
    df -P / | grep -v Filesystem | awk '{print $5}' | tr -d %
}

get_seconds() {
    (time -p ${1}) 2>&1 | awk '/real/{print $2}'
}

complete_load() {
    local script_file=${LOAD_SCRIPT_FILE:-/tmp/load.sh}
    local stop_file=${LOAD_STOP_FILE:-/tmp/load.stop}
    local processes_num=${LOAD_PROCESSES_COUNT:-20}
    local size=${LOAD_SIZE_MB:-5}

    cat << EOF > ${script_file}
until test -e ${stop_file}
do dd if=/dev/urandom bs=1M count=${size} 2>/dev/null | gzip >/dev/null ; done
EOF

    local sep
    local cpu
    local ram
    local dis
    rm -f ${stop_file}
    for i in $(seq ${processes_num})
    do
        i=$((i-1))
        sh ${script_file} &
        cpu="${cpu}${sep}[${i}, $(get_used_cpu_percent)]"
        ram="${ram}${sep}[${i}, $(get_used_ram_percent)]"
        dis="${dis}${sep}[${i}, $(get_used_disk_percent)]"
        sep=", "
    done
    > ${stop_file}
    cat << EOF
    {
      "title": "Generate load by spawning processes",
      "description": "Each process runs gzip for ${size}M urandom data in a loop",
      "chart_plugin": "Lines",
      "axis_label": "Number of processes",
      "label": "Usage, %",
      "data": [
        ["CPU", [${cpu}]],
        ["Memory", [${ram}]],
        ["Disk", [${dis}]]]
    }
EOF
}

additive_dd() {
    local c=${1:-50} # Megabytes
    local file=/tmp/dd_test.img
    local write=$(get_seconds "dd if=/dev/urandom of=${file} bs=1M count=${c}")
    local read=$(get_seconds "dd if=${file} of=/dev/null bs=1M count=${c}")
    local gzip=$(get_seconds "gzip ${file}")
    rm ${file}.gz
    cat << EOF
    {
      "title": "Write, read and gzip file",
      "description": "Using file '${file}', size ${c}Mb.",
      "chart_plugin": "StackedArea",
      "data": [
        ["write_${c}M", ${write}],
        ["read_${c}M", ${read}],
        ["gzip_${c}M", ${gzip}]]
    },
    {
      "title": "Statistics for write/read/gzip",
      "chart_plugin": "StatsTable",
      "data": [
        ["write_${c}M", ${write}],
        ["read_${c}M", ${read}],
        ["gzip_${c}M", ${gzip}]]
    }

EOF
}

cat << EOF
{
  "additive": [$(additive_dd)],
  "complete": [$(complete_load)]
}
EOF
