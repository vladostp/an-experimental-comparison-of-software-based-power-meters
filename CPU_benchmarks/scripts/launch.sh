#!/bin/bash

# Launch processes and get theirs start and end time 
echo "Start time $(date -u '+%Y-%m-%d %H:%M:%S.%6N')"
for cmd in "$@"; do
  echo "Launching '$cmd'..."
  $cmd
done
echo "End time $(date -u '+%Y-%m-%d %H:%M:%S.%6N')"
