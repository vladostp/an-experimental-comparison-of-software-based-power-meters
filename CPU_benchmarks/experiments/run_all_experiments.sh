#!/bin/bash

echo "Launching experiments at jobs bench: $1 and data: $2"

./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment power_profiles --energy_scope
./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment power_profiles --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment scaphandre_sampling_frequency --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment energy_scope_sampling_frequency --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment two_ep_parallel_execution --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment two_mg_parallel_execution --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment three_ep_parallel_execution --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment ep_lu_parallel_execution --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment scaphandre_cpu_overhead
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment powerapi_cpu_overhead --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment powerapi_max_process --no_image_deploy
#./launch_experiment.py --g5k_site lyon --bench_host_jobid $1 --data_host_jobid $2 --experiment scaphandre_max_process --no_image_deploy
