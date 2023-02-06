#!/bin/bash
GPU_TOTAL_NUMBER=$0
BINARY_DIR=$1

for gpu_id in {0..GPU_TOTAL_NUMBER-1}
do
    cp $BINARY_DIR/idle.sh $BINARY_DIR/gpu$gpu_id/
done