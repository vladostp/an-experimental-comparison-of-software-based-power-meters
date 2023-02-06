#!/bin/bash
benchmark_binary_path="/root/energy-consumption-of-gpu-benchmarks/code/templates/launch_parallel.sh /root/energy-consumption-of-gpu-benchmarks///CPU_benchmark_binaries///gpu0/mg.D"
chmod 777 $benchmark_binary_path
sleep_before=30
sleep_after=30
gpu_number=0
sleep $sleep_before
echo "BENCHMARK_TAG start_benchmark GPU $gpu_number DATE $(date '+%Y/%m/%dT%H:%M:%S.%6N')"
$benchmark_binary_path
echo "BENCHMARK_TAG stop_benchmark GPU $gpu_number DATE $(date '+%Y/%m/%dT%H:%M:%S.%6N')"
sleep $sleep_after