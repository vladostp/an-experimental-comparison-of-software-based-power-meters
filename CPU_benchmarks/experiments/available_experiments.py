# Import files for experiments
from experiments import Experiments
from experiment import Experiment
from kwollect import Kwollect
from powerapi import PowerAPI
from node_exporter import NodeExporter
from energy_scope import EnergyScope
from scaphandre import Scaphandre
from utils import *

def experiment_3_solutions_compare(job_bench, job_data, energy_scope_enabled, type="simple"):
    # Creating experiment instance
    experiments = Experiments('3 Solutions Compare')
    experiments.add_job(job_bench, "bench")
    experiments.add_job(job_data, "data")

    # Creating tested solutions instances
    powerapi = PowerAPI(experiments)
    scaphandre = Scaphandre(experiments)
    if energy_scope_enabled:
        energyscope = EnergyScope(experiments)
    kwollect = Kwollect(experiments)

    # Adding solutions to experiment
    experiments.add_solution(powerapi)
    experiments.add_solution(scaphandre)
    if energy_scope_enabled:
        experiments.add_solution(energyscope)
    experiments.add_solution(kwollect)

    # Preparing hosts
    experiments.prepare_bench_host()
    experiments.prepare_data_host()

    # Create cgroups for benchmarks
    powerapi.add_cgroup('/benchmark')

    # Set general (cpu and gpu info about bench host, g5k jobs) info to experiment
    experiments.set_general_info()

    # Experiment 1
    experiment1 = Experiment("PowerAPI")
    experiments.add_experiment(experiment1)

    # Start HWPC Service
    powerapi.start_hwpc_service()

    # Check if Smart Watt recieves PowerReports on data host
    powerapi.check_hwpc_report_send()

    benchmarks_template = [
        {
            "name": "EP D NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }, 
        {
            "name": "LU C NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "lu.C.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        },
        {
            "name": "MG D NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "mg.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]

    # Calculating frequencies if type of experiment is frequnecies
    frequencies = generate_frequencies(1000000, int(experiments.get_scaling_max_frequency(0))) if type == "frequencies" else ""

    # Calculating threads if type of experiments is threads
    threads = generate_thread_num_list(experiments.get_threads_available()) if type == "threads" else ""

    # Adding benchmarks to experiments
    experiment1.generate_benchmarks(benchmarks_template, frequencies, threads)

    # Running benchmarks
    experiment1.set_start_time_to_now()
    print("Experiment start time %s." % experiment1.start_time)

    experiments.run_experiment_benchmarks(experiment1)

    experiment1.set_end_time_to_now()
    print("Experiment end time %s." % experiment1.end_time)

    # Stop HWPC Service
    powerapi.stop_hwpc_service()

    # Get data from Kwollect for each benchmark
    kwollect_df = kwollect.get_consumption(experiment1)
    experiment1.add_result('kwollect-powerapi', kwollect_df)
    print(kwollect_df)

    # Get data from PowerAPI
    powerapi_df = powerapi.get_consumption(experiment1)
    experiment1.add_result('powerapi', powerapi_df)
    print(powerapi_df)

    # Experiment 2
    experiment2 = Experiment("Scaphandre")
    experiments.add_experiment(experiment2)

    # Start Scaphandre Service
    scaphandre.start_scaphandre_service()

    benchmarks_template = [
        {
            "name": "EP D NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        },
        {
            "name": "LU C NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "lu.C.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        },
        {
            "name": "MG D NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "mg.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]

    # Calculating frequencies if type of experiment is frequnecies
    frequencies = generate_frequencies(1000000, int(experiments.get_scaling_max_frequency(0))) if type == "frequencies" else ""

    # Calculating threads if type of experiments is threads
    threads = generate_thread_num_list(experiments.get_threads_available()) if type == "threads" else ""

    # Adding benchmarks to experiments
    experiment2.generate_benchmarks(benchmarks_template, frequencies, threads)

    # Running benchmarks
    experiment2.set_start_time_to_now()
    print("Experiment start time %s." % experiment2.start_time)

    experiments.run_experiment_benchmarks(experiment2)

    experiment2.set_end_time_to_now()
    print("Experiment end time %s." % experiment2.end_time)

    # Stop Scaphandre Service
    scaphandre.stop_scaphandre_service()

    # Get data from Kwollect for each benchmark
    kwollect_df = kwollect.get_consumption(experiment2)
    experiment2.add_result('kwollect-scaphandre', kwollect_df)
    print(kwollect_df)

    # Get data from Scaphandre
    scaphandre_df_process, scaphandre_df_host, scaphandre_df_host_ram = scaphandre.get_consumption(experiment2)
    experiment2.add_result('scaphandre-process', scaphandre_df_process)
    experiment2.add_result('scaphandre-host', scaphandre_df_host)
    experiment2.add_result('scaphandre-host-ram', scaphandre_df_host_ram)
    print(scaphandre_df_process)
    print(scaphandre_df_host)
    print(scaphandre_df_host_ram)

    if energy_scope_enabled:
        # Experiment 3
        experiment3 = Experiment("EnergyScope")
        experiments.add_experiment(experiment3)

        benchmarks_template = [
            {
                "name": "EP D NAS Benchmark",
                "bench_type": "energyscope",
                "bin_info": {
                    "bin_file": "ep.D.x",
                    "prefix": "sudo ENERGY_SCOPE_SRC_DIR=/tmp/compare-software-power-meters/energy_scope ENERGY_SCOPE_TRACES_PATH=/tmp/compare-software-power-meters/energy_scope/results /tmp/compare-software-power-meters/energy_scope/energy_scope_mypc.sh"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }, 
            {
                "name": "LU C NAS Benchmark",
                "bench_type": "energyscope",
                "bin_info": {
                    "bin_file": "lu.C.x",
                    "prefix": "sudo ENERGY_SCOPE_SRC_DIR=/tmp/compare-software-power-meters/energy_scope ENERGY_SCOPE_TRACES_PATH=/tmp/compare-software-power-meters/energy_scope/results /tmp/compare-software-power-meters/energy_scope/energy_scope_mypc.sh"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            },
            {
                "name": "MG D NAS Benchmark",
                "bench_type": "energyscope",
                "bin_info": {
                    "bin_file": "mg.D.x",
                    "prefix": "sudo ENERGY_SCOPE_SRC_DIR=/tmp/compare-software-power-meters/energy_scope ENERGY_SCOPE_TRACES_PATH=/tmp/compare-software-power-meters/energy_scope/results /tmp/compare-software-power-meters/energy_scope/energy_scope_mypc.sh"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }
        ]

        # Calculating frequencies if type of experiment is frequnecies
        frequencies = generate_frequencies(1000000, int(experiments.get_scaling_max_frequency(0))) if type == "frequencies" else ""

        # Calculating threads if type of experiments is threads
        threads = generate_thread_num_list(experiments.get_threads_available()) if type == "threads" else ""

        # Adding benchmarks to experiments
        experiment3.generate_benchmarks(benchmarks_template, frequencies, threads)

        # Running benchmarks
        experiment3.set_start_time_to_now()
        print("Experiment start time %s." % experiment3.start_time)

        experiments.run_experiment_benchmarks(experiment3)

        experiment3.set_end_time_to_now()
        print("Experiment end time %s." % experiment3.end_time)

        # Get data from Kwollect for each benchmark
        kwollect_df = kwollect.get_consumption(experiment3)
        experiment3.add_result('kwollect-energyscope', kwollect_df)
        print(kwollect_df)

        # Get consumption data from Energy Scope
        energy_scope_df = energyscope.get_consumption(experiment3)
        experiment3.add_result('energyscope', energy_scope_df)
        print(energy_scope_df)

    # Saving experiment
    experiments.save()
    
    # Stopping all services and containers at hosts
    experiments.clean_bench_host()
    experiments.clean_data_host()

def power_profiles(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    for i in range(0, experiment_repeat):
        print('Running power_profiles experiment [%s/%s]...' % (i+1, experiment_repeat))
        experiment_3_solutions_compare(job_bench, job_data, energy_scope_enabled)


def acquisition_frequency_and_cpu_load(job_bench, job_data, solution_name, solutions, frequencies, benchmark_templates, name, energy_scope_enabled, service_type='default', cgroups=1):
    # Creating experiment instance
    experiments = Experiments(name)
    experiments.add_job(job_bench, "bench")
    experiments.add_job(job_data, "data")
    
    solution = None
    
    # Creating tested solutions instances and adding them to experiments
    if 'powerapi' in solutions:
        powerapi = PowerAPI(experiments)
        experiments.add_solution(powerapi)
        solution = powerapi
        
    if 'scaphandre' in solutions:
        scaphandre = Scaphandre(experiments)
        experiments.add_solution(scaphandre)
        solution = scaphandre

    if energy_scope_enabled and 'energyscope' in solutions:
        energyscope = EnergyScope(experiments)
        experiments.add_solution(energyscope)
        solution = energyscope
        
    if 'kwollect' in solutions:
        kwollect = Kwollect(experiments)
        experiments.add_solution(kwollect)
        
    if 'node_exporter' in solutions:
        node_exporter = NodeExporter(experiments)
        experiments.add_solution(node_exporter)
        
    # Preparing hosts
    experiments.prepare_bench_host()
    experiments.prepare_data_host()
    
    # Set general (cpu and gpu info about bench host, g5k jobs) info to experiment
    experiments.set_general_info()
    
    # Executing experiments for different frequencies 
    for freq in frequencies:

        experiment = Experiment(solution_name + '-' + str(freq))
        experiments.add_experiment(experiment)
        
        # Changing aquistion frequency
        solution.set_acquisition_frequency(freq)
        print("Acquistion frequency was set to %s..." % solution.get_acquisition_frequency())
        
        if 'powerapi' in solutions:
            # Creating cgroups
            for i in range(0, cgroups):
                if i == 0:
                    powerapi.add_cgroup('/benchmark')
                else:
                    powerapi.add_cgroup('/benchmark%d' % i+1)

        # Restarting solution to use new frequency
        solution.stop_data()
        solution.start_data()
        
        # Starting service
        solution.start_bench_service(service_type)
        
        # Adding benchmark to template
        experiment.generate_benchmarks(benchmark_templates)
        
        # Running benchmarks
        experiment.set_start_time_to_now()
        print("Experiment start time %s." % experiment.start_time)

        experiments.run_experiment_benchmarks(experiment)

        experiment.set_end_time_to_now()
        print("Experiment end time %s." % experiment.end_time)
        
        # Stopping service at benchmark host
        solution.stop_bench_service(service_type)
        
        # Get data from Kwollect for each benchmark
        if 'kwollect' in solutions:
            kwollect_df = kwollect.get_consumption(experiment)
            experiment.add_result('kwollect-%s' % solution_name, kwollect_df)
            print(kwollect_df)
            
        # If node exporter is in solutions we will get and save cpu load
        if 'node_exporter' in solutions:
            # Get CPU load from Node Exporter
            node_exporter_df = node_exporter.get_cpu_load(experiment)
            experiment.add_result('cpu-load-%s' % solution_name, node_exporter_df)
            print(node_exporter_df)

        # Get consumption data frames
        # Scaphandre is a little big unique it gives us 3 different data frames
        if 'scaphandre' in solutions:
            scaphandre_df_process, scaphandre_df_host, scaphandre_df_host_ram = scaphandre.get_consumption(experiment)
            experiment.add_result('scaphandre-process', scaphandre_df_process)
            experiment.add_result('scaphandre-host', scaphandre_df_host)
            experiment.add_result('scaphandre-host-ram', scaphandre_df_host_ram)
            print(scaphandre_df_process)
            print(scaphandre_df_host)
            print(scaphandre_df_host_ram)
        else:
            solution_df = solution.get_consumption(experiment)
            experiment.add_result(solution_name, solution_df)
            print(solution_df)
                                  
        # Cleaning after each experiment
        solution.clean_after_experiment()
                                  
    # Saving experiment
    experiments.save()
    
    # Stopping all services and containers at hosts
    experiments.clean_bench_host()
    experiments.clean_data_host()

def scaphandre_sampling_frequency(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    for i in range(0, experiment_repeat):
        print('Running Scaphandre sampling frequency change [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "Scaphandre frequency change"
        solution_name = "scaphandre"
        solutions_list = ['kwollect', 'scaphandre']
        frequencies = [10, 5, 2 , 1]                        
        cgroups = 0
        benchmark_templates = [
            {
                "name": "EP NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "ep.D.x",
                    "prefix": "sudo"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }
        ]
                        
        acquisition_frequency_and_cpu_load(job_bench, 
                                        job_data, 
                                        solution_name, 
                                        solutions_list, 
                                        frequencies, 
                                        benchmark_templates, 
                                        experiment_name,
                                        energy_scope_enabled,
                                        'default', 
                                        cgroups)

def powerapi_sampling_frequency(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployment for bench job
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    for i in range(0, experiment_repeat):
        print('Running PowerAPI sampling frequency change [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "PowerAPI frequency change"
        solution_name = "powerapi"
        solutions_list = ['kwollect', 'powerapi']
        frequencies = [1000, 500, 100, 80, 50]               
        cgroups = 1
        benchmark_templates = [
            {
                "name": "EP NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "ep.D.x",
                    "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }
        ]
                        
        acquisition_frequency_and_cpu_load(job_bench, 
                                        job_data, 
                                        solution_name, 
                                        solutions_list, 
                                        frequencies, 
                                        benchmark_templates, 
                                        experiment_name,
                                        energy_scope_enabled, 
                                        'default', 
                                        cgroups)

def energy_scope_sampling_frequency(job_bench, job_data, experiment_repeat, energy_scope_enabled):

    if not energy_scope_enabled:
        print("Energy Scope experiments are disabled. See --energy_scope option.")
        return

    for i in range(0, experiment_repeat):
        print('Running Energy Scope acquisition frequency change [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "Energy Scope frequency change"
        solution_name = "energyscope"
        solutions_list = ['kwollect', 'energyscope']
        frequencies = [500, 200, 100, 50, 20]
        cgroups = 0
        benchmark_templates = [
            {
                "name": "EP NAS Benchmark",
                "bench_type": "energyscope",
                "bin_info": {
                    "bin_file": "ep.D.x",
                    "prefix": "sudo ENERGY_SCOPE_SRC_DIR=/tmp/compare-software-power-meters/energy_scope ENERGY_SCOPE_TRACES_PATH=/tmp/compare-software-power-meters/energy_scope/results /tmp/compare-software-power-meters/energy_scope/energy_scope_mypc.sh"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }
        ]
                              
        acquisition_frequency_and_cpu_load(job_bench, 
                                           job_data, 
                                           solution_name, 
                                           solutions_list, 
                                           frequencies, 
                                           benchmark_templates, 
                                           experiment_name, 
                                           energy_scope_enabled,
                                           'default', 
                                           cgroups)

def max_process(job_bench, job_data, solution_name, solutions, process_num_list, name, service_type='default', powerapi_version='march'):
    # Creating experiment instance
    experiments = Experiments(name)
    experiments.add_job(job_bench, "bench")
    experiments.add_job(job_data, "data")
    
    solution = None
    
    # Creating tested solutions instances and adding them to experiments
    if 'powerapi' in solutions:
        powerapi = PowerAPI(experiments, powerapi_version)
        experiments.add_solution(powerapi)
        solution = powerapi
        
    if 'scaphandre' in solutions:
        scaphandre = Scaphandre(experiments)
        experiments.add_solution(scaphandre)
        solution = scaphandre
    
    if 'kwollect' in solutions:
        kwollect = Kwollect(experiments)
        experiments.add_solution(kwollect)
        
    if 'node_exporter' in solutions:
        node_exporter = NodeExporter(experiments)
        experiments.add_solution(node_exporter)
        
    # Preparing hosts
    experiments.prepare_bench_host()
    experiments.prepare_data_host()
    
    # Set general (cpu and gpu info about bench host, g5k jobs) info to experiment
    experiments.set_general_info()
    
    # Executing experiments for different frequencies 
    for processes in process_num_list:
        experiment = Experiment(solution_name + '-' + str(processes) + '-processes')
        experiments.add_experiment(experiment)
        
        # Creating cgroups
        if 'powerapi' in solutions:
            for i in range(0, processes):
                powerapi.add_cgroup('/benchmark%s' % str(i+1))
            print(powerapi.cgroups)
                   
        # Starting service
        solution.start_bench_service(service_type)
        
        benchmark_templates = [
            {
                "name": "%d Parallel EP NAS Benchmarks" % processes,
                "bench_type": "parallel",
                "bin_info": [],
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }
        ]
         
        for i in range (0, processes):
            if 'powerapi' in solutions:
                benchmark_templates[0]["bin_info"].append(
                    {
                    "bin_file": "ep.C.x",
                    "prefix": "sudo OMP_NUM_THREADS=1 cgexec -g perf_event:/benchmark%s" % str(i+1)
                    }
                )
            else:
                benchmark_templates[0]["bin_info"].append(
                    {
                    "bin_file": "ep.C.x",
                    "prefix": "sudo OMP_NUM_THREADS=1"
                    }
                )
        
        # Adding benchmark to template
        experiment.generate_benchmarks(benchmark_templates)
        
        # Running benchmarks
        experiment.set_start_time_to_now()
        print("Experiment start time %s." % experiment.start_time)

        experiments.run_experiment_benchmarks(experiment)

        experiment.set_end_time_to_now()
        print("Experiment end time %s." % experiment.end_time)
        
        # Stopping service at benchmark host
        solution.stop_bench_service(service_type)
        
        # Get data from Kwollect for each benchmark
        if 'kwollect' in solutions:
            kwollect_df = kwollect.get_consumption(experiment)
            experiment.add_result('kwollect-%s' % solution_name, kwollect_df)
            print(kwollect_df)
            
        # If node exporter is in solutions we will get and save cpu load
        if 'node_exporter' in solutions:
            # Get CPU load from Node Exporter
            node_exporter_df = node_exporter.get_cpu_load(experiment)
            experiment.add_result('cpu-load-%s' % solution_name, node_exporter_df)
            print(node_exporter_df)

        # Get consumption data frames
        # Scaphandre is a little big unique it gives us 3 different data frames
        if 'scaphandre' in solutions:
            scaphandre_df_process, scaphandre_df_host, scaphandre_df_host_ram = scaphandre.get_consumption(experiment)
            experiment.add_result('scaphandre-process', scaphandre_df_process)
            experiment.add_result('scaphandre-host', scaphandre_df_host)
            experiment.add_result('scaphandre-host-ram', scaphandre_df_host_ram)
            print(scaphandre_df_process)
            print(scaphandre_df_host)
            print(scaphandre_df_host_ram)
        else:
            solution_df = solution.get_consumption(experiment)
            experiment.add_result(solution_name, solution_df)
            print(solution_df)
                       
        # Cleaning after each experiment
        solution.clean_after_experiment()
                                  
    # Saving experiment
    experiments.save()
    
    # Stopping all services and containers at hosts
    experiments.clean_bench_host()
    experiments.clean_data_host()


def powerapi_max_process(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_data.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()
       
    # PowerAPI max process number test
    for i in range(0, experiment_repeat):
        print('Running PowerAPI max process number [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "PowerAPI max process number"
        solution_name = "powerapi"
        solutions_list = ['kwollect', 'powerapi', 'node_exporter']
        processes = [4, 5, 6, 7, 8, 9, 10]
                    
        max_process(job_bench, 
                   job_data, 
                   solution_name, 
                   solutions_list, 
                   processes,
                   experiment_name, 
                   'cpu-0')

def powerapi_max_process_v0_9_2(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_data.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    ## Setting PowerAPI version
    powerapi_version = "v0.9.2"

    # PowerAPI max process number test
    for i in range(0, experiment_repeat):
        print('Running PowerAPI new max process number [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "PowerAPI new max process number"
        solution_name = "powerapi"
        solutions_list = ['kwollect', 'powerapi', 'node_exporter']
        processes = [4, 10, 12, 14, 16, 18, 20]

        max_process(job_bench, 
                   job_data, 
                   solution_name, 
                   solutions_list, 
                   processes,
                   experiment_name, 
                   'cpu-0',
                   powerapi_version)

def scaphandre_max_process(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_data.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    for i in range(0, experiment_repeat):
        print('Running Scaphandre max process number [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "Scaphandre max process number"
        solution_name = "scaphandre"
        solutions_list = ['kwollect', 'scaphandre', 'node_exporter']
        processes = [5, 10, 20, 30, 50, 100]
                    
        max_process(job_bench, 
                    job_data, 
                    solution_name, 
                    solutions_list, 
                    processes,
                    experiment_name, 
                    'cpu-0')

def cpu_load(job_bench, job_data, solution_name, solutions, frequencies, benchmark_templates, name, service_type='default', cgroups=1):
    # Creating experiment instance
    experiments = Experiments(name)
    experiments.add_job(job_bench, "bench")
    experiments.add_job(job_data, "data")
    
    solution = None
    
    # Creating tested solutions instances and adding them to experiments
    if 'powerapi' in solutions:
        powerapi = PowerAPI(experiments)
        experiments.add_solution(powerapi)
        solution = powerapi
        
    if 'scaphandre' in solutions:
        scaphandre = Scaphandre(experiments)
        experiments.add_solution(scaphandre)
        solution = scaphandre
        
    if 'kwollect' in solutions:
        kwollect = Kwollect(experiments)
        experiments.add_solution(kwollect)
        
    if 'node_exporter' in solutions:
        node_exporter = NodeExporter(experiments)
        experiments.add_solution(node_exporter)
        
    # Preparing hosts
    experiments.prepare_bench_host()
    experiments.prepare_data_host()
    
    # Set general (cpu and gpu info about bench host, g5k jobs) info to experiment
    experiments.set_general_info()
    
    # Executing experiments for different frequencies 
    for freq in frequencies:
        # Creating cgroups
        for i in range(0, cgroups):
            if i == 0:
                powerapi.add_cgroup('/benchmark')
            else:
                powerapi.add_cgroup('/benchmark%d' % i+1)
    
        experiment = Experiment(solution_name + '-' + str(freq))
        experiments.add_experiment(experiment)
        
        # Changing aquistion frequency
        solution.set_acquisition_frequency(freq)
        print("Acquistion frequency was set to %s..." % solution.get_acquisition_frequency())

        # Restarting solution to use new frequency
        solution.stop_data()
        solution.start_data()
        
        # Starting service
        solution.start_bench_service(service_type)
        
        # Adding benchmark to template
        experiment.generate_benchmarks(benchmark_templates)
        
        # Running benchmarks
        experiment.set_start_time_to_now()
        print("Experiment start time %s." % experiment.start_time)

        experiments.run_experiment_benchmarks(experiment)

        experiment.set_end_time_to_now()
        print("Experiment end time %s." % experiment.end_time)
        
        # Stopping service at benchmark host
        solution.stop_bench_service(service_type)
        
        # Get data from Kwollect for each benchmark
        if 'kwollect' in solutions:
            kwollect_df = kwollect.get_consumption(experiment)
            experiment.add_result('kwollect-%s' % solution_name, kwollect_df)
            print(kwollect_df)
            
        # If node exporter is in solutions we will get and save cpu load
        if 'node_exporter' in solutions:
            # Get CPU load from Node Exporter
            node_exporter_df = node_exporter.get_cpu_load(experiment)
            experiment.add_result('cpu-load-%s' % solution_name, node_exporter_df)
            print(node_exporter_df)

        # Get consumption data frames
        # Scaphandre is a little big unique it gives us 3 different data frames
        if 'scaphandre' in solutions:
            scaphandre_df_process, scaphandre_df_host, scaphandre_df_host_ram = scaphandre.get_consumption(experiment)
            experiment.add_result('scaphandre-process', scaphandre_df_process)
            experiment.add_result('scaphandre-host', scaphandre_df_host)
            experiment.add_result('scaphandre-host-ram', scaphandre_df_host_ram)
            print(scaphandre_df_process)
            print(scaphandre_df_host)
            print(scaphandre_df_host_ram)
        else:
            solution_df = solution.get_consumption(experiment)
            experiment.add_result(solution_name, solution_df)
            print(solution_df)
                                  
        # Cleaning after each experiment
        solution.clean_after_experiment()
                                  
    # Saving experiment
    experiments.save()
    
    # Stopping all services and containers at hosts
    experiments.clean_bench_host()
    experiments.clean_data_host()

def powerapi_cpu_overhead(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_data.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    for i in range(0, experiment_repeat):
        print('Running PowerAPI cpu overhead study [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "PowerAPI cpu overhead"
        solution_name = "powerapi"
        solutions_list = ['kwollect', 'powerapi', 'node_exporter']
        frequencies = [1000, 500, 100, 80, 50]                    
        cgroups = 1
        benchmark_templates = [
            {
                "name": "EP D NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "ep.D.x",
                    "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }, 
            {
                "name": "LU C NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "lu.C.x",
                    "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            },
            {
                "name": "MG D NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "mg.D.x",
                    "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }
        ]
                      
        cpu_load(job_bench, 
                job_data, 
                solution_name, 
                solutions_list, 
                frequencies, 
                benchmark_templates, 
                experiment_name, 
                'cpu-0', 
                cgroups)

def scaphandre_cpu_overhead(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_data.create_deployment('ubuntu2004-x64-cpu-0-isolate', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    for i in range(0, experiment_repeat):
        print('Running Scaphandre cpu overhead study [%s/%s]...' % (i+1, experiment_repeat))
        experiment_name = "Scaphandre cpu overhead"
        solution_name = "scaphandre"
        solutions_list = ['kwollect', 'scaphandre', 'node_exporter']
        frequencies = [10, 5, 2 , 1]                         
        cgroups = 0
        benchmark_templates = [
            {
                "name": "EP D NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "ep.D.x",
                    "prefix": "sudo"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }, 
            {
                "name": "LU C NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "lu.C.x",
                    "prefix": "sudo"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            },
            {
                "name": "MG D NAS Benchmark",
                "bench_type": "simple",
                "bin_info": {
                    "bin_file": "mg.D.x",
                    "prefix": "sudo"
                },
                "sleep_before": 60, 
                "sleep_after": 60,
                "frequency": 0,
                "threads": 0
            }
        ]
  
        cpu_load(job_bench, 
                job_data, 
                solution_name, 
                solutions_list, 
                frequencies, 
                benchmark_templates, 
                experiment_name, 
                'cpu-0', 
                cgroups)

def experiment_2_solutions_compare(job_bench, job_data, name, benchmark_templates):
    # Creating experiment instance
    experiments = Experiments(name)
    experiments.add_job(job_bench, "bench")
    experiments.add_job(job_data, "data")

    # Creating tested solutions instances
    powerapi = PowerAPI(experiments)
    scaphandre = Scaphandre(experiments)
    kwollect = Kwollect(experiments)

    # Adding solutions to experiment
    experiments.add_solution(powerapi)
    experiments.add_solution(scaphandre)
    experiments.add_solution(kwollect)

    # Preparing hosts
    experiments.prepare_bench_host()
    experiments.prepare_data_host()
    
    # Create cgroups for benchmarks
    powerapi.add_cgroup('/benchmark')
    powerapi.add_cgroup('/benchmark2')
    powerapi.add_cgroup('/benchmark3')
    
    # Set general (cpu and gpu info about bench host, g5k jobs) info to experiment
    experiments.set_general_info()
    
    # Set threads available global variable
    global available_threads
    available_threads = experiments.get_threads_available()
    
    # Experiment 1
    experiment1 = Experiment("PowerAPI")
    experiments.add_experiment(experiment1)
    
    # Start HWPC Service
    powerapi.start_hwpc_service()
    
    # Check if Smart Watt recieves PowerReports on data host
    powerapi.check_hwpc_report_send()
    
    experiment1.generate_benchmarks(benchmark_templates, "", "")
    
    # Running benchmarks
    experiment1.set_start_time_to_now()
    print("Experiment start time %s." % experiment1.start_time)

    experiments.run_experiment_benchmarks(experiment1)

    experiment1.set_end_time_to_now()
    print("Experiment end time %s." % experiment1.end_time)
    
    # Stop HWPC Service
    powerapi.stop_hwpc_service()
    
    # Get data from Kwollect for each benchmark
    kwollect_df = kwollect.get_consumption(experiment1)
    experiment1.add_result('kwollect-powerapi', kwollect_df)
    print(kwollect_df)

    # Get data from PowerAPI
    powerapi_df = powerapi.get_consumption(experiment1)
    experiment1.add_result('powerapi', powerapi_df)
    print(powerapi_df)

    # Experiment 2
    experiment2 = Experiment("Scaphandre")
    experiments.add_experiment(experiment2)
    
    # Start Scaphandre Service
    scaphandre.start_scaphandre_service()
    
    experiment2.generate_benchmarks(benchmark_templates, "", "")
    
    # Running benchmarks
    experiment2.set_start_time_to_now()
    print("Experiment start time %s." % experiment2.start_time)

    experiments.run_experiment_benchmarks(experiment2)

    experiment2.set_end_time_to_now()
    print("Experiment end time %s." % experiment2.end_time)
    
    # Stop Scaphandre Service
    scaphandre.stop_scaphandre_service()
    
    # Get data from Kwollect for each benchmark
    kwollect_df = kwollect.get_consumption(experiment2)
    experiment2.add_result('kwollect-scaphandre', kwollect_df)
    print(kwollect_df)

    # Get data from Scaphandre
    scaphandre_df_process, scaphandre_df_host, scaphandre_df_host_ram = scaphandre.get_consumption(experiment2)
    experiment2.add_result('scaphandre-process', scaphandre_df_process)
    experiment2.add_result('scaphandre-host', scaphandre_df_host)
    experiment2.add_result('scaphandre-host-ram', scaphandre_df_host_ram)
    print(scaphandre_df_process)
    print(scaphandre_df_host)
    print(scaphandre_df_host_ram)
    
    # Saving experiment
    experiments.save()
    
    # Stopping all services and containers at hosts
    experiments.clean_bench_host()
    experiments.clean_data_host()

def is_mg_parallel_execution(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    experiment_1_benchmark_template = [
        {
            "name": "MG and IS NAS Benchmarks Launched in Parallel",
            "bench_type": "parallel",
            "bin_info": [
                {
                "bin_file": "is.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                {
                "bin_file": "mg.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark2"
                }
            ],
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]

    for i in range(0, experiment_repeat):
        print('Running 2 solution parallel benchmark execution - different RAM intensive benchmarks [%s/%s]...' % (i+1, experiment_repeat))
        experiment_2_solutions_compare(job_bench, job_data, "2 Solutions Compare 2 Parallel Different RAM", experiment_1_benchmark_template)

def two_ep_parallel_execution(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    experiment_4_benchmark_template = [
        {
            "name": "2 Parallel EP NAS Benchmarks",
            "bench_type": "parallel",
            "bin_info": [
                {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark2"
                }
            ],
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]

    for i in range(0, experiment_repeat):
        print('Running 2 solution parallel benchmark execution - same benchmark [%s/%s]...' % (i+1, experiment_repeat))
        experiment_2_solutions_compare(job_bench, job_data, "2 Solutions Compare 2 Parallel Same", experiment_4_benchmark_template)

  
def two_mg_parallel_execution(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    experiment_3_benchmark_template = [
        {
            "name": "2 Parallel MG NAS Benchmarks",
            "bench_type": "parallel",
            "bin_info": [
                {
                "bin_file": "mg.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                {
                "bin_file": "mg.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark2"
                }
            ],
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]
    for i in range(0, experiment_repeat):
        print('Running 2 solution parallel benchmark execution - same RAM intensive Benchmark [%s/%s]...' % (i+1, experiment_repeat))
        experiment_2_solutions_compare(job_bench, job_data, "2 Solutions Compare 2 Parallel Same RAM", experiment_3_benchmark_template)

def three_ep_parallel_execution(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    experiment_6_benchmark_template = [
        {
            "name": "3 Parallel EP NAS Benchmarks",
            "bench_type": "parallel",
            "bin_info": [
                {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark2"
                },
                {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark3"
                }
            ],
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]
    
    for i in range(0, experiment_repeat):
        print('Running 2 solution parallel benchmark execution - 3 same benchmarks [%s/%s]...' % (i+1, experiment_repeat))
        experiment_2_solutions_compare(job_bench, job_data, "2 Solutions Compare 3 Parallel Same", experiment_6_benchmark_template)

def ep_lu_parallel_execution(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    experiment_8_benchmark_template =  [
        {
            "name": "1 EP et 1 LU parallel NAS Benchmarks",
            "bench_type": "parallel",
            "bin_info": [
                {
                "bin_file": "ep.D.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark"
                },
                {
                "bin_file": "lu.C.x",
                "prefix": "sudo cgexec -g perf_event:/benchmark2"
                }
            ],
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]

    for i in range(0, experiment_repeat):
        print('Running 2 solution parallel benchmark execution - different benchmarks [%s/%s]...' % (i+1, experiment_repeat))
        experiment_2_solutions_compare(job_bench, job_data, "2 Solutions Compare Parallel Different", experiment_8_benchmark_template)
  
# Defining experiments
def no_solution(job_bench, name, type="simple"):
    # Creating experiment instance
    experiments = Experiments(name)
    experiments.add_job(job_bench, "bench")

    # Creating tested solutions instances
    kwollect = Kwollect(experiments)

    # Adding solutions to experiment
    experiments.add_solution(kwollect)

    # Preparing hosts
    experiments.prepare_bench_host()

    # Set general (cpu and gpu info about bench host, g5k jobs) info to experiment
    experiments.set_general_info()

    # Experiment 1
    experiment1 = Experiment("Kwollect")
    experiments.add_experiment(experiment1)

    benchmarks_template = [
        {
            "name": "EP D NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "ep.D.x",
                "prefix": ""
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }, 
        {
            "name": "LU C NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "lu.C.x",
                "prefix": ""
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        },
        {
            "name": "MG D NAS Benchmark",
            "bench_type": "simple",
            "bin_info": {
                "bin_file": "mg.D.x",
                "prefix": ""
            },
            "sleep_before": 60, 
            "sleep_after": 60,
            "frequency": 0,
            "threads": 0
        }
    ]

    # Calculating frequencies if type of experiment is frequnecies
    frequencies = generate_frequencies(1000000, int(experiments.get_scaling_max_frequency(0))) if type == "frequencies" else ""

    # Calculating threads if type of experiments is threads
    threads = generate_thread_num_list(experiments.get_threads_available()) if type == "threads" else ""

    # Adding benchmarks to experiments
    experiment1.generate_benchmarks(benchmarks_template, frequencies, threads)

    # Running benchmarks
    experiment1.set_start_time_to_now()
    print("Experiment start time %s." % experiment1.start_time)

    experiments.run_experiment_benchmarks(experiment1)

    experiment1.set_end_time_to_now()
    print("Experiment end time %s." % experiment1.end_time)

    # Get data from Kwollect for each benchmark
    kwollect_df = kwollect.get_consumption(experiment1)
    experiment1.add_result('kwollect', kwollect_df)
    print(kwollect_df)

    # Saving experiment
    experiments.save()
    
    # Stopping all services and containers at hosts
    experiments.clean_bench_host()

def no_solution_execution(job_bench, job_data, experiment_repeat, energy_scope_enabled):
    # Creating deployments
    job_bench.create_deployment('ubuntu2004-x64-min', 'root')
    job_data.create_deployment('ubuntu2004-x64-min', 'root')
    job_bench.wait_for_deployment()
    job_data.wait_for_deployment()

    for i in range(0, experiment_repeat):
        print('Running no solution experience [%s/%s]...' % (i+1, experiment_repeat))
        no_solution(job_bench, "No solution", "simple")


available_experiments = {
    'power_profiles': power_profiles,
    'scaphandre_sampling_frequency': scaphandre_sampling_frequency,
    'powerapi_sampling_frequency': powerapi_sampling_frequency,
    'energy_scope_sampling_frequency': energy_scope_sampling_frequency,
    'scaphandre_cpu_overhead': scaphandre_cpu_overhead,
    'powerapi_cpu_overhead': powerapi_cpu_overhead,
    'powerapi_max_process': powerapi_max_process,
    'powerapi_max_process_v0_9_2': powerapi_max_process_v0_9_2,
    'scaphandre_max_process': scaphandre_max_process,
    'is_mg_parallel_execution': is_mg_parallel_execution,
    'two_ep_parallel_execution': two_ep_parallel_execution,
    'two_mg_parallel_execution': two_mg_parallel_execution,
    'three_ep_parallel_execution': three_ep_parallel_execution,
    'ep_lu_parallel_execution': ep_lu_parallel_execution,
    'no_solution_execution': no_solution_execution
}
