#!/bin/bash
# Usage example of this repository (local)

# following variable to manually fill
# Path to git repository
git_repo=
# Path to repo/code/start_exp.py
start_script=
# Path to result directory e.g. git_repo/results/DATE_TIME/
result_repo=
# Path to the code of Energy Scope
es_folder=

# The following loops execute 10 experiments for each software monitoring the GPU energy consumption and for each benchmarks
for i in {0..3}
do
   for j in {1..10}
   do
      for tool in ExperimentImpactTracker CarbonTrackerTool CodeCarbon EnergyScope
      do
         python3.7 $start_script --git_repo $git_repo --result_folder $result_repo --energy_scope_folder $es_folder --$tool --repetitions 1 --benchmark_id $i
      done
   done
done