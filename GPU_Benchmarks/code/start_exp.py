"""Start experiments.

It creates experiments from given arguments, starts them and processes and saves outputs.

typical use:
python /home/mjay/GPU_benchmark_energy/code/start_exp.py \
    --git_repo /home/mjay/GPU_benchmark_energy/ \
    --result_folder /home/mjay/GPU_benchmark_energy/results/image_test/ \
    --energy_scope_folder /home/mjay/energy_scope/ \
    --ExperimentImpactTracker


"""
import argparse
import logging
import os
import pandas as pd
from sklearn.model_selection import ParameterGrid

from utils.experiments import System, Benchmark, Experiment
from utils.tools import PowerTool, EnergyScope, ExperimentImpactTracker, CarbonTrackerTool, CodeCarbon, PyJoules


def create_benchmark_objects(exp_id, gpu_id, log_dir, binary_dir, execution_script_template, params, sleep_before, sleep_after):
    bench_list = []
    grid = ParameterGrid(params)
    script_dir = log_dir + "scripts/"
    os.mkdir(script_dir)
    i=0
    for param in grid:
        bench_appli = param['benchmarks'][0]
        bench_class = param['benchmarks'][1]
        benchmark = Benchmark(
            benchmark_id = exp_id + "_" + str(i),
            gpu_id = gpu_id,
            name = "NAS",
            binary_dir = binary_dir,
            appli=bench_appli,
            appli_class=bench_class,
            sleep_before = sleep_before,
            sleep_after = sleep_after,
            execution_script_template = execution_script_template,
            execution_script_path = script_dir+"{}.sh".format(i),
        )
        bench_list.append(benchmark)
        i+=1
    return bench_list

def parsing_arguments():
    parser = argparse.ArgumentParser(description='GPU benchmark & energy tools')
    parser.add_argument('--git_repo', 
                        help='Path to this git repo.', 
                        type=str, default='/root/energy-consumption-of-gpu-benchmarks/')
    parser.add_argument('--benchmark_binary_dir', 
                        help='Path to the directory containing the benchmark binaries.', 
                        type=str, default='/root/energy-consumption-of-gpu-benchmarks/GPU_benchmark_binaries/')
    parser.add_argument('--result_folder', 
                        help='Path to the folder to save the results in.', 
                        type=str, default='/root/energy-consumption-of-gpu-benchmarks/results/')
    parser.add_argument('--energy_scope_folder', 
                        help='Path to energy scope folder.', 
                        type=str, default='/root/energy_scope/')
    parser.add_argument('--repetitions', 
                        help='Number of repetitions.', 
                        type=int, default=10)
    parser.add_argument('--gpu_range', 
                        help='Number of GPU to use.', 
                        type=int, default=8)
    parser.add_argument('--sleep_before', 
                        type=int, default=30)
    parser.add_argument('--sleep_after', 
                        type=int, default=30)
    parser.add_argument('--NoTool', 
                        help='Launch the benchmarks without tools.', 
                        action='store_true', default=False)
    parser.add_argument('--ExperimentImpactTracker', 
                        help='Whether to test ExperimentImpactTracker or not.', 
                        action='store_true', default=False)
    parser.add_argument('--PyJoules', 
                        help='Whether to test PyJoules or not.', 
                        action='store_true', default=False)
    parser.add_argument('--EnergyScope', 
                        help='Whether to test EnergyScope or not.', 
                        action='store_true', default=False)
    parser.add_argument('--CarbonTrackerTool', 
                        help='Whether to test CarbonTrackerTool or not.', 
                        action='store_true', default=False)
    parser.add_argument('--CodeCarbon', 
                        help='Whether to test CodeCarbon or not.', 
                        action='store_true', default=False)
    parser.add_argument('--monitor_one_process', 
                        help='Whether to test the tool on one process or all processes.', 
                        action='store_true', default=False)
    parser.add_argument('--benchmark_id', 
                        help='If only one benchmark, which one.', 
                        type=int)
    parser.add_argument('--CPU', 
                        help='Whether to launch the CPU benchmarks instead of the GPU benchmarks, False by default.', 
                        action='store_true', default=False)
    return parser.parse_args()


def main():
    # Processing arguments
    args = parsing_arguments()
    
    git_repo = args.git_repo
    experiments_dir = args.result_folder
    
    current_system = System()
    tool_on_one_process = args.monitor_one_process
    
    es_src =  args.energy_scope_folder
    binary_dir = args.benchmark_binary_dir

    execution_script_template = git_repo+"code/templates/script_template.sh"
    launch_parallel_script = git_repo+"code/templates/launch_parallel.sh"
    
    if args.CPU:
        benchmarks = [('idle', 'sh'), ("mg", "D"), ("lu", "C"), ("ep", "D")] # CPU
        gpu_range = 1
    else:
        benchmarks = [('idle', 'sh'), ("mg", "D"), ("lu", "D"), ("ep", "E")] # GPU
        gpu_range = args.gpu_range

    if args.benchmark_id is not None:
        logging.info("performing only one benchmark:")
        benchmarks = benchmarks[args.benchmark_id:args.benchmark_id+1]
        logging.info(benchmarks)
    else:
        logging.info("List of benchmark to launch:")
        logging.info(benchmarks)
        
    params = {
        'benchmarks': benchmarks,
        'repetition': ['']*args.repetitions,
        'gpu_range': [gpu_range],
        }
    
    to_test = [args.NoTool, args.EnergyScope, args.CarbonTrackerTool, args.CodeCarbon, args.ExperimentImpactTracker, args.PyJoules]
    power_tools = [PowerTool, EnergyScope, CarbonTrackerTool, CodeCarbon, ExperimentImpactTracker, PyJoules] 
    tools_to_test = [power_tools[i] for i in range(len(power_tools)) if to_test[i]]
    
    # Start an experiment for every requested tools 
    for tool in tools_to_test:
        logging.info("Tool used: {}".format(tool))
        logging.info("On one process: {}".format(tool_on_one_process))
        log_dir, exp_id = current_system.create_log_dir(experiments_dir)
        logging.info("Log directory: {} \nExperiment ID: {}".format(log_dir, exp_id))

        # create a benchmark object per GPU
        parallel_bench_list = []
        for gpu_id in range(params['gpu_range'][0]):
            os.mkdir(log_dir+"/gpu{}/".format(gpu_id))
            bench_binary_dir =  binary_dir+"/gpu{}/".format(gpu_id)
            bench_list = create_benchmark_objects(
                exp_id, 
                gpu_id,
                log_dir+"/gpu{}/".format(gpu_id), 
                bench_binary_dir,
                execution_script_template, 
                params, args.sleep_before, args.sleep_after,
            )
            parallel_bench_list.append(bench_list)

        # Configure the tool object
        error=False
        if tool == EnergyScope:
            # add an if to check if ES is in the directory
            es_source_tar = git_repo + "software-installation/energy-scope_v2022-03-24_acquisition.tar"
            if os.path.exists(es_src):
                tool_instance = EnergyScope(log_dir, es_src, current_system.job_id, launch_parallel_script)
            else:
                logging.info("Energy Scope source files not found at {}\n, looking for its tar file at {}.".format(es_src, es_source_tar))
                if os.path.exists(es_source_tar):
                    os.popen("tar -xf {} --directory /root/".format(es_source_tar))
                    tool_instance = EnergyScope(log_dir, es_src, current_system.job_id, launch_parallel_script)
                else:
                    logging.error("Energy Scope tar file not found at {}.".format(es_source_tar))
                    error=True
        elif tool == PowerTool:
            tool_instance = tool(log_dir, "NoTool")
        else:
            tool_instance = tool(log_dir)
        
        if not error:
            # Create the experiment object
            current_exp = Experiment(
                experiments_table=experiments_dir+"experiment_table.csv",
                tool=tool_instance, 
                benchmarks=parallel_bench_list,
                system=current_system,
                tool_on_one_process=tool_on_one_process,
            )

            # Start the experiment
            current_exp.start()

            # Process results
            #current_exp.retrieve_wattmeter_values() #to do afterwards
            current_exp.process_power_tool_results()
            current_exp.save_experiment_results()
            logging.info(pd.DataFrame(current_exp.results).transpose())


if __name__ == '__main__':
    logging.basicConfig(
        filename='./logs.log', 
        level=logging.DEBUG,
        format='%(levelname)s - %(asctime)s: %(message)s',
        )
    try:
        main()
    except Exception as err:
        logging.error(err)
