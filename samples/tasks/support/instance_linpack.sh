#!/bin/sh
# Location of Linpack binary
LINPACK='/opt/linpack/xlinpack_xeon64'
type -P $LINPACK &>/dev/null && continue || { echo "Linpack Not Found"; exit 1 }

# Location to create linpack dat file
LINPACK_DAT='~/linpack.dat'

NUM_CPU=`cat /proc/cpuinfo | grep processor | wc -l`
export OMP_NUM_THREADS=$NUM_CPU
echo "Sample Intel(R) LINPACK data file (from lininput_xeon64)" > ${LINPACK_DAT}
echo "Intel(R) LINPACK data" >> ${LINPACK_DAT}
echo "1 # number of tests" >> ${LINPACK_DAT}
echo "10514 # problem sizes" >> ${LINPACK_DAT}
echo "20016 # leading dimensions" >> ${LINPACK_DAT}
echo "2 # times to run a test " >> ${LINPACK_DAT}
echo "4 # alignment values (in KBytes)" >> ${LINPACK_DAT}
OUTPUT=$(${LINPACK} < ${LINPACK_DAT} | grep -A 1 Average | grep 20016)
AVERAGE=$(echo $OUTPUT | awk '{print $4}')
MAX=$(echo $OUTPUT | awk '{print $5}')

echo "{
    \"average_gflops\": $AVERAGE,
    \"max_gflops\": $MAX
    }"
