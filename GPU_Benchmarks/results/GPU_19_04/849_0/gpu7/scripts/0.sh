#!/bin/bash
benchmark_binary_path="/root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu7/idle.sh"
chmod 777 $benchmark_binary_path
sleep_before=0
sleep_after=0
gpu_number=7
sleep $sleep_before
echo "BENCHMARK_TAG start_benchmark GPU $gpu_number DATE $(date '+%Y/%m/%dT%H:%M:%S.%6N')"
$benchmark_binary_path
echo "BENCHMARK_TAG stop_benchmark GPU $gpu_number DATE $(date '+%Y/%m/%dT%H:%M:%S.%6N')"
sleep $sleep_after