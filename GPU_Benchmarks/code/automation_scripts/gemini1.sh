#!/bin/bash
# Usage example of this repository (ssh)
# This script automates the start of experiments on a gemini node in ssh and the retrieval of results from a local computer

# complete with your login
login=
user_home="/home/$login/"
node="gemini-1"
local_git_path="/root/comparison/"
frontale_git_path="$user_home/an-experimental-comparison-of-software-based-power-meters/GPU_Benchmarks/"
result_path="$local_git_path/results/test/"
installation_script="$local_git_path/code/install_scripts/installation.sh"
env_script="$local_git_path/code/install_scripts/get_env_ready.sh"
start_script="$local_git_path/code/start_exp.py"
es_folder="/root/energy_scope/"
benchmark_binary_dir="/GPU_benchmark_binaries/"

# installation

ssh root@$node "mkdir $local_git_path"
ssh root@$node "mkdir $local_git_path/results/"
ssh root@$node "mkdir $result_path"
rsync -avzh $frontale_git_path/code/ root@$node:$local_git_path/code/
rsync -avzh $frontale_git_path/$benchmark_binary_dir/ root@$node:$local_git_path/$benchmark_binary_dir/
rsync -avzh $frontale_git_path/software-installation/ root@$node:$local_git_path/software-installation/
ssh root@$node "bash $installation_script"
ssh root@$node "bash $env_script"

# compile benchmarks
# rsync -avzh NPB-GPU/ root@$node:NPB-GPU/ 
# ssh root@$node "bash $local_git_path/$benchmark_binary_dir/compile_all.sh 8 /root/NPB-GPU/CUDA/ $frontale_git_path/$benchmark_binary_dir/"

# start experiments. 
## Here it will start one experiment
ssh root@$node "python3 $start_script --git_repo $local_git_path --result_folder $result_path --energy_scope_folder $es_folder --CodeCarbon --benchmark_id 0 --repetitions 1 --benchmark_binary_dir $local_git_path/$benchmark_binary_dir/"
            
## Here it will start one experiment for each benchmark and each available tool.   
: '
for j in {1..1} # 1 to 10: number of repetitions
do
    for i in {0..3} # 0 to 3: benchmark id
    do
        for tool in CarbonTrackerTool CodeCarbon ExperimentImpactTracker EnergyScope
        do
            # Launch experiment for one tool, one benchmark, one repetition
            ssh root@$node "python3 $start_script --git_repo $local_git_path --result_folder $result_path --energy_scope_folder $es_folder --$tool --benchmark_id $i --repetitions 1 --benchmark_binary_dir $local_git_path/$benchmark_binary_dir/"
            # Get results
            scp -r root@$node:$local_git_path/results/ $frontale_git_path
        done
    done
done
'