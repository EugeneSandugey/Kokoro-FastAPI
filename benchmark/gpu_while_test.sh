#!/bin/bash
# Log GPU stats every second while the test runs
OUTPUT=/home/echo/projects/kokoro/benchmark/output/gpu_log.csv
echo "timestamp,gpu_pct,mem_pct,mem_used_mb,temp_c,power_w,sm_clock_mhz" > $OUTPUT

while true; do
    DATA=$(nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,temperature.gpu,power.draw,clocks.sm --format=csv,noheader,nounits 2>/dev/null)
    echo "$(date +%s),$DATA" >> $OUTPUT
    sleep 1
done
