#!/bin/bash
sudo modprobe msr
echo off > /sys/devices/system/cpu/smt/control
sudo wrmsr -a 0x1a0 0x4000850089
sudo cpupower idle-set -D 0
sudo cpupower frequency-set -g performance
#cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq
sudo cpupower frequency-set -d 2200000 && sudo cpupower frequency-set -u 2200000 # This is specific the gemini node
#i7z
sudo chmod -R a+r /sys/class/powercap/intel-rapl
