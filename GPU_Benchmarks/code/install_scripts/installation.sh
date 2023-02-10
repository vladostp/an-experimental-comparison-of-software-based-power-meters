#!/bin/bash
apt-get -y update
apt-get -y upgrade
apt-get -y install libgfortran5
apt install -y git
apt install -y linux-tools-common msr-tools linux-tools-generic i7z
# 'uname -r' got me 5.4.0-100-generic
apt install -y linux-tools-`uname -r`
apt install -y nvidia-cuda-toolkit
apt install -y nvidia-driver-510  # This is specific the gemini node
apt install -y ubuntu-drivers-common
apt install -y software-properties-common
add-apt-repository ppa:deadsnakes/ppa
apt install -y python3.7
apt install -y python3.7-pip
apt install -y python3.7-distutils
python3.7 -m pip install scikit-learn pandas matplotlib py-cpuinfo psutil requests
python3.7 -m pip install codecarbon==2.0.0 #2.0.0 
python3.7 -m pip install git+https://github.com/Breakend/experiment-impact-tracker.git@c1b0fcb4e75f04511805a1e57b2d8a97266d2977 # 0.1.9
python3.7 -m pip install carbontracker==1.1.6 #1.1.6 
python3.7 -m pip install pyJoules==0.5.1 #0.5.1
tar -xf /root/an-experimental-comparison-of-software-based-power-meters/GPU_Benchmarks/software-installation/energy-scope_v2022-03-24_acquisition.tar --directory /root/
