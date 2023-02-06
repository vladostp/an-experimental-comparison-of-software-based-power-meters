#!/bin/bash
benchmark_binary_path="/root/energy-consumption-of-gpu-benchmarks/code/templates/launch_parallel.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu0/idle.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu1/idle.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu2/idle.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu3/idle.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu4/idle.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu5/idle.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu6/idle.sh /root/energy-consumption-of-gpu-benchmarks/NAS_benchmark_binaries//gpu7/idle.sh"
chmod 777 $benchmark_binary_path
sleep_before=30
sleep_after=30
gpu_number=0
sleep $sleep_before
echo "BENCHMARK_TAG start_benchmark GPU $gpu_number DATE $(date '+%Y/%m/%dT%H:%M:%S.%6N')"
$benchmark_binary_path
echo "BENCHMARK_TAG stop_benchmark GPU $gpu_number DATE $(date '+%Y/%m/%dT%H:%M:%S.%6N')"
sleep $sleep_after