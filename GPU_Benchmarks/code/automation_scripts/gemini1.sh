#!/bin/bash
# Usage example of this repository (ssh)
# This script automates the start of experiments on a gemini node in ssh and the retrieval of results from a local computer

# variables to modify
local_git_path="/root/comparison/"
# complete with your login
login=
user_home="/home/$login/"
frontale_git_path=user_home+"/an-experimental-comparison-of-software-based-power-meters/"
result_path="$local_git_path/results/test/"
installation_script="$local_git_path/code/install_scripts/installation.sh"
env_script="$local_git_path/code/install_scripts/get_env_ready.sh"
start_script="$local_git_path/code/start_exp.py"
es_folder="/root/energy_scope/"
benchmark_binary_dir="/GPU_benchmark_binaries/"

# installation

ssh root@gemini-1 "mkdir $local_git_path"
ssh root@gemini-1 "mkdir $local_git_path/results/"
ssh root@gemini-1 "mkdir $result_path"
rsync -avzh $frontale_git_path/code/ root@gemini-1:$local_git_path/code/
rsync -avzh $frontale_git_path/$benchmark_binary_dir/ root@gemini-1:$local_git_path/$benchmark_binary_dir/
rsync -avzh $frontale_git_path/software-installation/ root@gemini-1:$local_git_path/software-installation/
ssh root@gemini-1 "bash $installation_script"
ssh root@gemini-1 "bash $env_script"

# compile benchmarks
cd user_home
git clone git@github.com:GMAP/NPB-GPU.git
rsync -avzh NPB-GPU/ root@gemini-1:NPB-GPU/ 
ssh root@gemini-1 "bash $local_git_path/$benchmark_binary_dir/compile_all.sh"

# start experiments. Here it will start one experiment for each benchmark and each available tool.

for j in {1..1} # 1 to 10: number of repetitions
do
    for i in {0..3} # 0 to 3: benchmark id
    do
        for tool in CarbonTrackerTool CodeCarbon ExperimentImpactTracker EnergyScope
        do
            # Launch experiment for one tool, one benchmark, one repetition
            ssh root@gemini-1 "python3.7 $start_script --git_repo $local_git_path --result_folder $result_path --energy_scope_folder $es_folder --$tool --repetitions 1 --benchmark_binary_dir $local_git_path/$benchmark_binary_dir/"
            # Get results
            scp -r root@gemini-1:$local_git_path/results/ $frontale_git_path
        done
    done
done
