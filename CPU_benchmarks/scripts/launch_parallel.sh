#!/bin/bash

# Store PID of launched processes
pids=()

# Launch processes in backgroud and add their PID to array 
echo "Start time $(date -u '+%Y-%m-%d %H:%M:%S.%6N')"
for cmd in "$@"; do
  echo "Launching '$cmd' in backgroud..."
  $cmd&
  echo "PID: $!"
  pids=(${pids[@]} $!) 
done

# Wait for every process from PID array
echo "Waiting for processes with PIDs '${pids[@]}' to finish..."
for pid in ${pids[@]}; do
	wait $pid
done
echo "End time $(date -u '+%Y-%m-%d %H:%M:%S.%6N')"
echo "All processes finished..."
