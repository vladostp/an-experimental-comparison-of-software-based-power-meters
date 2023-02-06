#!/bin/bash
GPU_TOTAL_NUMBER=$0
COMPILER_DIR=$1
BINARY_DIR=$2

cd COMPILER_DIR

for bench in ep lu mg
do
    for class in D E
    do
        for gpu_id in {0..$GPU_TOTAL_NUMBER-1}
        do
            python3 $BINARY_DIR/modify_config.py --gpu_id $gpu_id --nas_config_repo $COMPILER_DIR/config/gpu.config # modify config file
            echo "config file: "
            head -1 $COMPILER_DIR/config/gpu.config
            make clean
            make $bench CLASS=$class
            mkdir $BINARY_DIR/gpu$gpu_id
            cp $COMPILER_DIR/bin/$bench.$class $BINARY_DIR/gpu$gpu_id/
        done
    done
done