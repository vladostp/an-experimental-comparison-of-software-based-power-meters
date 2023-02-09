from sklearn import linear_model
import re
import datetime
import json
import pandas as pd
import copy
import numpy as np

# Parse experiment result from experiment result folder
# Returns an object with filled in experiment and consumption data
def parse_experiment(path):
    experiments = {}
    experiments["experiments"] = []
    with open("%s/experiments.json" % path, 'r') as file:
        data = json.load(file)
    
        experiments["jobs"] = data["jobs"]
        experiments["cpu"] = data["cpu"]
        experiments["gpu"] = data["gpu"]
        
        # Parsing experiments data
        for experiment in data["experiments"]:
            experiment_new = {}
            experiment_new["name"] = experiment["name"]
            # Converting timestamps from string to datetime
            experiment_new["start_time"] = datetime.datetime.strptime(experiment["start_time"], "%Y-%m-%d %H:%M:%S.%f")
            experiment_new["end_time"] = datetime.datetime.strptime(experiment["end_time"], "%Y-%m-%d %H:%M:%S.%f")
            experiment_new["benchmarks"] = []
            for benchmark in experiment["benchmarks"]:
                benchmark['start_time'] = datetime.datetime.strptime(benchmark["start_time"], "%Y-%m-%d %H:%M:%S.%f")
                benchmark["end_time"] = datetime.datetime.strptime(benchmark["end_time"], "%Y-%m-%d %H:%M:%S.%f")
                experiment_new["benchmarks"].append(benchmark)

            # Fill consumption data from CSV files
            experiment_new["results"] = []
            for consumption_data in experiment["results"]:
                dataframe = pd.read_csv("%s/%s" % (path, consumption_data["file"]))
                if 'timestamp' in dataframe:
                    dataframe['timestamp'] = pd.to_datetime(dataframe['timestamp'])
                    
                experiment_new["results"].append({
                    'source': consumption_data["source"],
                    'dataframe': dataframe
                }) 
            experiments["experiments"].append(experiment_new)
    return experiments


# Print experiment information
def show_experiment_info(experiment):
    print("[=============== Showing experiment info ===============]")
    print("------------  Jobs info ------------")
    for job in experiment['jobs']:
        print(job)
        print("   - Job id: %d" % experiment['jobs'][job]["uid"])
        print("   - Assigned node: %s" % experiment['jobs'][job]["host"])
    print("------------ CPU info ------------")
    for info in experiment['cpu']:
        print("   - %s %s" % (info["field"], info["data"]))
    print("------------ GPU info ------------")
    if experiment['gpu']:
        print("   - Count: %s" % experiment['gpu']["count"])
        print("   - Name: %s" % experiment['gpu']["name"])
    else:
        print("   - No GPU found")
    print("------------ Experiments ------------")
    for experiment in experiment['experiments']:
        print("   [---------- Name: %s ----------]" % experiment['name'])
        if 'aquisition_frequency' in experiment:
            print("   Aquisition frequency: %s" % experiment['aquisition_frequency'])
        print("   Experiment start time: %s" % experiment['start_time'])
        print("   Experiment end time: %s" % experiment['end_time'])
        print("   -------- Benchmarks runned --------")
        for bench in experiment['benchmarks']:
                print("      ---- %s" % bench['name'])
                print("         - Benchmark type: %s" % bench['bench_type'])
                print("         - Start time: %s" % bench['start_time'])
                print("         - End time: %s" % bench['end_time'])
                
                if 'bench_type' in bench and bench['bench_type'] == 'parallel':
                    print("         - Benchmarks launched in parallel:")
                    for bin_info_one in bench['bin_info']:
                        print("                  ----------")
                        print("                  - Benchmark bin: %s" % bin_info_one['bin_file'])
                        print("                  - Command prefix: %s" % bin_info_one['prefix'])
                        print("                  ----------")
                else:
                    print("         - Benchmark bin: %s" % bench['bin_info']['bin_file'])
                    print("         - Command prefix: %s" % bench['bin_info']['prefix'])
        print("   -----------------------------------")


# Get experiment by name from a map of experiments
def get_experiment(experiments, name):
    for experiment in experiments["experiments"]:
        if experiment['name'] == name:
            return experiment

# Get consumption dataframe by source
def get_consumption_dataframe(consumptions, source_name):
    for consumption_data in consumptions:
        if consumption_data['source'] == source_name:
            return copy.deepcopy(consumption_data['dataframe'])
    return None

# Shift dataframe timestamps 
def shift_dataframe_time(dataframe, shift_date):
    if 'timestamp' in dataframe:
        dataframe['timestamp'] = dataframe['timestamp'] - shift_date
        return dataframe

# Groups multiple experiences and consumption data by benchmark
def convert_exp_into_benchmark_dataframes(
    experiments,
    experiment_name,
    solution_name,
    delay_time = 5,
    timeshift=True
):
    benchmarks = {}

    for experiment in experiments:
        # Get exeriment by name
        solution = get_experiment(experiment, experiment_name)
        
        # Shift benchmark time
        for benchmark in solution['benchmarks']:
            # Creating the benchmark instance in benchmarks map
            bench_name = benchmark['name']
            if bench_name not in benchmarks:
                benchmarks[bench_name] = {'bin_info':  benchmark['bin_info']}

            # Calculating benchmark period +- delay time in seconds
            if delay_time > 0:
                start_time = benchmark['start_time'] - datetime.timedelta(seconds=delay_time)
                end_time = benchmark['end_time'] + datetime.timedelta(seconds=delay_time)
            elif delay_time < 0:
                start_time = benchmark['start_time'] + datetime.timedelta(seconds=abs(delay_time))
                end_time = benchmark['end_time'] - datetime.timedelta(seconds=abs(delay_time))
            else:
                start_time = benchmark['start_time']
                end_time = benchmark['end_time']

            ## Select data between delayed start time and delayed end time for solution
            df = get_consumption_dataframe(solution['results'], solution_name)
            ### If not able to get consumption dataframe or got an empty dataframe return None
            if df is None or df.empty:
                return None
            
            # Filter dataframe
            if 'timestamp' in df:
                df_part = copy.deepcopy(df[(df['timestamp'] > start_time) & (df['timestamp'] < end_time)])
            else: 
                df_part = df[df['benchmark'] == bench_name]

            ## Shifting time to start at timestamp zero
            if 'timestamp' in df and timeshift:
                df_part = shift_dataframe_time(df_part, start_time)

            # If there is no value for a target on specific timestamp for scaphandre we will fill it with zero
            if solution_name == 'scaphandre':
                # Create a multi index containing all timestamps and targets
                mux = pd.MultiIndex.from_product([df_part['timestamp'].unique(),
                      df_part['target'].unique()], names=['timestamp','target'])
                # Reindexing by multi index by filling empty values with 0
                df_part = df_part.set_index(['timestamp','target']).reindex(mux, fill_value=0).reset_index()
                # Removing host and dram values with value = 0
                df_part = df_part.drop(df_part[((df_part['target'] == 'host') | (df_part['target'] == 'dram')) & (df_part['value'] == 0)].index)

            solution_df_and_times = {
                        'start_time': start_time,
                        'end_time': end_time,
                        'dataframe': df_part
            }

            ## Adding solution data to benchmarks
            if solution_name not in benchmarks[bench_name]:
                benchmarks[bench_name][solution_name] = [solution_df_and_times]
            else:
                benchmarks[bench_name][solution_name].append(solution_df_and_times)

            if solution_name != 'kwollect':
                ## Selecting kwollect dataframe part between start and end time
                df_kwollect = get_consumption_dataframe(solution['results'], f"kwollect-{solution_name}")
                if df_kwollect is not None:
                    df_kwollect_part = copy.deepcopy(df_kwollect[(df_kwollect['timestamp'] > start_time) & (df_kwollect['timestamp'] < end_time)])
                    if timeshift:
                        df_kwollect_part = shift_dataframe_time(df_kwollect_part, start_time)
                    kwollect_df_and_times = {
                                'start_time': start_time,
                                'end_time': end_time,
                                'dataframe': df_kwollect_part 
                    }
                    ## Adding kwollect data to benchmark
                    if 'kwollect' not in benchmarks[bench_name]:
                        benchmarks[bench_name]['kwollect'] = [kwollect_df_and_times]
                    else:
                        benchmarks[bench_name]['kwollect'].append(kwollect_df_and_times)

    return benchmarks

# Get median consumption for all sockets for power api
def get_median_consumption_all_sockets(df, target, scope):
    df_target = df[df['target'] == target]
    df_scope = df_target[df_target['scope'] == scope]
    df_scope_median = df_scope.groupby(['timestamp','socket'], as_index=False)['power'].median()
    df_scope_median_all_sockets = df_scope_median.groupby('timestamp', as_index=False)['power'].sum()
    return df_scope_median_all_sockets

# Join multiple Scaphandre per component dataframes into a single consumption dataframe
def process_scaphandre_dataframes(experiments):
    # Create a global scaphandre dataframe from host, ram and process dataframes
    for experiment in experiments:
        solution = get_experiment(experiment, 'Scaphandre')
        scaphandre_host_df = get_consumption_dataframe(solution['results'], 'scaphandre-host')
        scaphandre_dram_df = get_consumption_dataframe(solution['results'], 'scaphandre-host-ram')
        scaphandre_process_df = get_consumption_dataframe(solution['results'], 'scaphandre-process')
        scaphandre_global_df = scaphandre_join_consumption_dataframes(scaphandre_host_df, scaphandre_dram_df, scaphandre_process_df)
        solution['results'].append({
            "source": "scaphandre",
            "dataframe": scaphandre_global_df
        })

# Join multiple Scaphandre per component dataframes into a single consumption dataframe for process experiment
def process_scaphandre_dataframes_process(experiments_scaphandre):
    #  Create a global scaphandre dataframe from host, ram and process dataframes
    for experiment in experiments_scaphandre:
        for sub_experiment in experiments_scaphandre[0]['experiments']:
            solution = get_experiment(experiment, sub_experiment['name'])
            scaphandre_host_df = get_consumption_dataframe(solution['results'], 'scaphandre-host')
            scaphandre_dram_df = get_consumption_dataframe(solution['results'], 'scaphandre-host-ram')
            scaphandre_process_df = get_consumption_dataframe(solution['results'], 'scaphandre-process')
            if not scaphandre_host_df.empty and not scaphandre_dram_df.empty and not scaphandre_process_df.empty:
                scaphandre_global_df = scaphandre_join_consumption_dataframes(scaphandre_host_df, scaphandre_dram_df, scaphandre_process_df)
                solution['results'].append({
                    "source": "scaphandre",
                    "dataframe": scaphandre_global_df
                })

# Join Scaphandre consumption dataframes to one
def scaphandre_join_consumption_dataframes(host_df, host_ram_df, process_df):
    host_df["target"] = "host"
    host_ram_df["target"] = "dram"

    # Here we will construct target of processes
    ## Each process is identified by a binary name and by a PID number
    ## We want be able to distinguish two processes with the same binary name
    ## So we will transform the PID number in an integer
    ## We will associate a number to every PID of the same binary
    ## So we will be able to distinguish 2 executions without the same PID
    ## The target will be composed of executable name _ number associated with execution PID
    ## Example: 2 Executions of ep.D.x with different PIDs will be stored as ep.D.x_0 and ep.D.x_1
    process_df["target"] = process_df.apply(lambda row: f"{row['exe']}_{list(process_df[process_df['exe'] == row['exe']]['pid'].unique()).index(row['pid'])}", axis=1) 

    # Concatenating 3 dataframes in one
    result_df = pd.concat([host_df, host_ram_df, process_df])[['timestamp', 'target', 'value']].sort_values('timestamp')

    return result_df

# Calculate integral to get overall consumption from dataframe
def overall_consumption_from_df(df, value_column_name='value'):
    dataframe_copy = copy.deepcopy(df)
    dataframe_copy['timestamp'] = dataframe_copy['timestamp'].dt.total_seconds()

    dataframe_copy = dataframe_copy.set_index('timestamp')
    dataframe_copy = dataframe_copy.filter(['timestamp', value_column_name])

    return np.trapz(dataframe_copy, x=dataframe_copy.index, axis=0)

# Add value to dataframe
def add_consumption_value_to_df(df, value):
    value_df = pd.DataFrame(value, index=[0])
    return pd.concat([df, value_df], ignore_index=True)

# Calculate kwollect consumption and add data to dataframe
def kwollect_consumption(kwollect_result):

    # Processing wattmetre data
    kwollect_result_wattmetre = copy.deepcopy(kwollect_result[kwollect_result['metric_id'] == 'wattmetre_power_watt'])
    kwollect_result_wattmetre['timestamp'] = kwollect_result_wattmetre['timestamp'].dt.floor('1s')

    # Processing bmc data
    kwollect_result_bmc = copy.deepcopy(kwollect_result[kwollect_result['metric_id'] == 'bmc_node_power_watt'])
    kwollect_result_bmc['timestamp'] = kwollect_result_bmc['timestamp'].dt.floor('5s')

    # Calculate overall consumption from dataframe
    overall_consumption_wattmetre = overall_consumption_from_df(kwollect_result_wattmetre)

    # Calculate overall consumption from dataframe
    overall_consumption_bmc = overall_consumption_from_df(kwollect_result_bmc)

    return (overall_consumption_wattmetre[0], overall_consumption_bmc[0])

# Calculate linear regression from two columns of a dataframe
def calculate_linear_regression(df, x='tool', y='wattmeter'):
    X = df[[x]]
    y = df[y]

    model = linear_model.LinearRegression()
    results = model.fit(X, y)

    return (results.coef_[0], results.intercept_)

def show_correlation_statistics(df):
    print(f"---------- Global statistics ----------")
    print(f"Pearson correlation coefficient: {df.corr()['tool']['wattmeter']}")
    print(f"Regression: {calculate_linear_regression(df, x='tool', y='wattmeter')}")

    # Caluclating regression for each benchmark
    if 'benchmark' in df:
        for benchmark in df["benchmark"].unique():
            benchmark_df = df[df["benchmark"] == benchmark]
            print(f"    ---------- Benchmark {str(benchmark)} statistics ----------")
            print(f"    Pearson correlation coefficient: {benchmark_df.corr()['tool']['wattmeter']}")
            print(f"    Regression: {calculate_linear_regression(benchmark_df, x='tool', y='wattmeter')}")

# Get cgroups from benchmark description
def get_cgroups_from_bin_info(bin_info):
    cgroup_regex = re.compile(r'perf_event\:(.*)')

    if type(bin_info) != list:
        cgroup_search = cgroup_regex.search(bin_info['prefix'])
        return [cgroup_search.group(1)]

    cgroup_list = []
    for bin_entry in bin_info:
        cgroup_search = cgroup_regex.search(bin_entry['prefix'])
        cgroup_list.append(cgroup_search.group(1))

    return cgroup_list

# Get binary files from benchmark description
def get_bins_from_bin_info(bin_info):
    if type(bin_info) != list:
        return [bin_info['bin_file']]

    bin_files_list = []
    for bin_entry in bin_info:
        bin_files_list.append(bin_entry['bin_file'])

    return bin_files_list

def get_powerapi_and_scaphandre_process_dfs(benchmarks_powerapi, benchmarks_scaphandre):
    # Construct result dataframe
    result_df_plots = pd.DataFrame(columns=['timestamp', 'benchmark', 'plot_name', 'value'])

    # Creating global dataframes for each benchmark and plotting them
    for benchmark_index in range(len(benchmarks_powerapi)):
        # Getting info about benchmark from different solutions
        benchmark_name = list(benchmarks_powerapi)[benchmark_index]
        benchmark_powerapi = benchmarks_powerapi[benchmark_name]
        benchmark_scaphandre = benchmarks_scaphandre[benchmark_name]

        # Calculate and Plot PowerAPI consumption
        ## Create list with dataframes only
        experiments_powerapi_dataframes = list(map(lambda el: el['dataframe'], benchmark_powerapi['powerapi']))

        ## Calculate a median value dataframe
        powerapi_median_values_df = calculate_median_values(experiments_powerapi_dataframes, ['timestamp', 'target', 'scope', 'socket'], 'power')

        ## Create a plottable dataframe for powerapi
        result_df_plot_powerapi = create_plottable_df_for_powerapi(powerapi_median_values_df, str(benchmark_name), targets=['process','rapl',''], scopes=['dram', 'cpu'])

        ## Adding to results df
        result_df_plots = pd.concat([result_df_plots, result_df_plot_powerapi], ignore_index=True)

        # Calculate and Plot Scaphandre consumption
        ## Create list with dataframes only
        experiments_scaphandre_dataframes = list(map(lambda el: el['dataframe'], benchmark_scaphandre['scaphandre']))

        ## Calculate a median value dataframe
        scaphandre_median_values_df = calculate_median_values(experiments_scaphandre_dataframes, ['timestamp', 'target'], 'value', timestamp_floor='5s')

        ## Create a plottable dataframe for power api
        result_df_plot_scaphandre = create_plottable_df_for_scaphandre(scaphandre_median_values_df, str(benchmark_name), targets = ['host', 'dram', 'process'])

        ## Adding to results df
        result_df_plots = pd.concat([result_df_plots, result_df_plot_scaphandre], ignore_index=True)

    return result_df_plots

def process_benchmarks_for_total_energy_bar_plots(benchmarks_powerapi, benchmarks_scaphandre):
    # Construct result dataframe
    result_df = pd.DataFrame(columns=['benchmark', 'tool', 'value'])

    # Creating global dataframes for each benchmark and plotting them
    for benchmark_index in range(len(benchmarks_powerapi)):

        # Getting info about benchmark from different solutions
        benchmark_name = list(benchmarks_powerapi)[benchmark_index]
        benchmark_powerapi = benchmarks_powerapi[benchmark_name]
        benchmark_scaphandre = benchmarks_scaphandre[benchmark_name]
        # Adding PowerApi results to result dataframe
        for result_index in range(len(benchmark_powerapi['powerapi'])):

            power_api_result = benchmark_powerapi['powerapi'][result_index]['dataframe']
            
            # Calculate overall PowerAPI consumption
            power_api_result_sockets = power_api_result.groupby(['timestamp', 'target', 'scope'], as_index=False)['power'].sum()
            power_api_result_sockets['timestamp'] = power_api_result_sockets['timestamp'].dt.floor('1s')

            power_api_sockets_rapl = power_api_result_sockets[power_api_result_sockets['target'] == 'rapl']
            power_api_sockets_rapl_global = power_api_sockets_rapl.groupby(['timestamp', 'target'], as_index=False)['power'].sum()

            # Calculate overall consumption for global rapl, cpu, rapl, cpu process, ram process
            overall_rapl_consumption_powerapi = overall_consumption_from_df(power_api_sockets_rapl_global, 'power')
            overall_rapl_ram_powerapi = overall_consumption_from_df(power_api_sockets_rapl[power_api_sockets_rapl['scope'] == 'dram'], 'power')
            overall_rapl_cpu_powerapi = overall_consumption_from_df(power_api_sockets_rapl[power_api_sockets_rapl['scope'] == 'cpu'], 'power')

            ## TODO : Add all by a single command
            result_df = add_consumption_value_to_df(result_df, {
                'benchmark': str(benchmark_name),
                'tool': 'powerapi',
                'source': 'rapl-global',
                'value': overall_rapl_consumption_powerapi[0]
            })
            result_df = add_consumption_value_to_df(result_df, {
                'benchmark': str(benchmark_name),
                'tool': 'powerapi',
                'source': 'rapl-dram',
                'value': overall_rapl_ram_powerapi[0]
            })
            result_df = add_consumption_value_to_df(result_df, {
                'benchmark': str(benchmark_name),
                'tool': 'powerapi',
                'source': 'rapl-cpu',
                'value': overall_rapl_cpu_powerapi[0]
            })

            cgroup_list = sorted(power_api_result[(power_api_result['target'] != 'rapl') & (power_api_result['target'] != 'global')]['target'].unique())

            # Loop through all executed benchmarks
            for cgroup in cgroup_list:
                power_api_sockets_process = power_api_result_sockets[power_api_result_sockets['target'] == cgroup]
                power_api_sockets_process_global = power_api_sockets_process.groupby(['timestamp', 'target'], as_index=False)['power'].sum()

                overall_process_consumption_powerapi = overall_consumption_from_df(power_api_sockets_process_global, 'power')
                overall_process_cpu_powerapi = overall_consumption_from_df(power_api_sockets_process[power_api_sockets_process['scope'] == 'cpu'], 'power')
                overall_process_dram_powerapi = overall_consumption_from_df(power_api_sockets_process[power_api_sockets_process['scope'] == 'dram'], 'power')

                result_df = add_consumption_value_to_df(result_df, {
                    'benchmark': str(benchmark_name),
                    'tool': 'powerapi',
                    'source': f"process-{cgroup_list.index(cgroup)+1}-global",
                    'value': overall_process_consumption_powerapi[0]
                })
                result_df = add_consumption_value_to_df(result_df, {
                    'benchmark': str(benchmark_name),
                    'tool': 'powerapi',
                    'source': f"process-{cgroup_list.index(cgroup)+1}-cpu",
                    'value': overall_process_cpu_powerapi[0]
                })
                result_df = add_consumption_value_to_df(result_df, {
                    'benchmark': str(benchmark_name),
                    'tool': 'powerapi',
                    'source': f"process-{cgroup_list.index(cgroup)+1}-dram",
                    'value': overall_process_dram_powerapi[0]
                })

        for result_index in range(len(benchmark_scaphandre['scaphandre'])):

            scaphandre_result = benchmark_scaphandre['scaphandre'][result_index]['dataframe']

            # Calculate overall scaphandre consumption
            scaphandre_result['timestamp'] = scaphandre_result['timestamp'].dt.floor('5s')
            scaphandre_result_host_dram = scaphandre_result[(scaphandre_result['target'] == 'host') | (scaphandre_result['target'] == 'dram')]
            scaphandre_result_global = scaphandre_result_host_dram.groupby(['timestamp'], as_index=False)['value'].sum(min_count=2)
            # Delete all lines with NaN values
            scaphandre_result_global = scaphandre_result_global.dropna(subset=["value"])

            # Calculate RAPL overall consumption from dataframe
            overall_consumption_scaphandre = overall_consumption_from_df(scaphandre_result_global)
            # Calculate RAPL CPU consumption from dataframe
            overall_cpu_consumption_scaphandre = overall_consumption_from_df(scaphandre_result_host_dram[scaphandre_result_host_dram['target'] == 'host'])
            # Calculate RAPL RAM consumption from dataframe
            overall_dram_consumption_scaphandre = overall_consumption_from_df(scaphandre_result_host_dram[scaphandre_result_host_dram['target'] == 'dram'])
     
            ## TODO : Add all data with a single command
            ## Adding consumption data to dataframe
            result_df = add_consumption_value_to_df(result_df, {
                'benchmark': str(benchmark_name),
                'tool': 'scaphandre',
                'source': 'rapl-global',
                'value': overall_consumption_scaphandre[0]
            })
            ## Adding consumption data to dataframe
            result_df = add_consumption_value_to_df(result_df, {
                'benchmark': str(benchmark_name),
                'tool': 'scaphandre',
                'source': 'rapl-cpu',
                'value': overall_cpu_consumption_scaphandre[0]
            })
            ## Adding consumption data to dataframe
            result_df = add_consumption_value_to_df(result_df, {
                'benchmark': str(benchmark_name),
                'tool': 'scaphandre',
                'source': 'rapl-dram',
                'value': overall_dram_consumption_scaphandre[0]
            })

            # Adding scaphandre processes consumption
            #bin_list = get_bins_from_bin_info(benchmark_scaphandre['bin_info'])

            process_list = sorted(scaphandre_result[(scaphandre_result['target'] != "dram") & (scaphandre_result['target'] != "host")]['target'].unique())

            for index, process in enumerate(process_list):
                scaphandre_result_process = scaphandre_result[scaphandre_result['target'].str.contains(process)]
                overall_process_consumption_scaphandre = overall_consumption_from_df(scaphandre_result_process)
                
                result_df = add_consumption_value_to_df(result_df, {
                    'benchmark': str(benchmark_name),
                    'tool': 'scaphandre',
                    'source': f"process-{index+1}-cpu",
                    'value': overall_process_consumption_scaphandre[0]
                })
    return result_df

def get_dataframes_only_from_benchmark(experiment_map):
    return list(map(lambda el: el['dataframe'], experiment_map))

def create_plottable_df_for_powerapi(
    powerapi_df,
    benchmark_name,
    scopes = ['dram', 'cpu', 'total'], 
    targets = ['global', 'rapl', 'process'],
    plotname_postfix = ''
):
    # Construct result dataframe
    result_df_plots = pd.DataFrame(columns=['timestamp', 'benchmark', 'plot_name', 'value'])

    # Calculate total consumption for all available sockets
    powerapi_df = powerapi_df.groupby(['timestamp', 'target', 'scope'], as_index=False)['power'].sum()

    # Processing and adding global estimation into result dataframe
    if 'global' in targets:
        result_df_plots = add_data_by_target(result_df_plots, powerapi_df, scopes, 'global', 'powerapi_global', benchmark_name)

    # Processing and adding rapl values into result dataframe
    if 'rapl' in targets:
        result_df_plots = add_data_by_target(result_df_plots, powerapi_df, scopes, 'rapl', 'powerapi_rapl', benchmark_name)

    # Processing and adding process information into result dataframe
    if 'process' in targets:
        # Get different available cgroups from dataframe
        cgroup_list = sorted(powerapi_df[(powerapi_df['target'] != 'rapl') & (powerapi_df['target'] != 'global')]['target'].unique())
        
        # Loop through all available cgroups and add them into result dataframe
        for cgroup in cgroup_list:
            result_df_plots = add_data_by_target(result_df_plots, powerapi_df, scopes, cgroup, f"powerapi_process_{cgroup_list.index(cgroup)+1}", benchmark_name)
            #print(f"{cgroup} = powerapi_process_{cgroup_list.index(cgroup)+1}")
    result_df_plots['plot_name'] = result_df_plots['plot_name'] + plotname_postfix

    return result_df_plots

# Add data into result dataframe for a specific target and for specific scopes
def add_data_by_target(result_df, df, scopes, target, plot_prefix, benchmark_name):
    # Get entries by target
    df_target = df[df['target'] == target]
    
    # Get entries by scope
    df_cpu_scope = copy.deepcopy(df_target[df_target['scope'] == 'cpu'])
    df_dram_scope = copy.deepcopy(df_target[df_target['scope'] == 'dram'])

    # Calculte the total consumption for both scopes
    df_total = pd.concat((df_cpu_scope, df_dram_scope)).groupby('timestamp',as_index=False).sum()

    # Adding values into result dataframe
    if 'cpu' in scopes:
        df_cpu_scope = df_cpu_scope.rename(columns={"power": "value"})
        df_cpu_scope["benchmark"] = benchmark_name
        df_cpu_scope["plot_name"] = f"{plot_prefix}_cpu"
        df_cpu_scope = df_cpu_scope.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, df_cpu_scope], ignore_index=True)

    if 'dram' in scopes:
        df_dram_scope = df_dram_scope.rename(columns={"power": "value"})
        df_dram_scope["benchmark"] = benchmark_name
        df_dram_scope["plot_name"] = f"{plot_prefix}_dram"
        df_dram_scope = df_dram_scope.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, df_dram_scope], ignore_index=True)

    if 'total' in scopes:
        df_total = df_total.rename(columns={"power": "value"})
        df_total["benchmark"] = benchmark_name
        df_total["plot_name"] = f"{plot_prefix}_total"
        df_total = df_total.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, df_total], ignore_index=True)

    return result_df

# Floor timestamp in a dataframe row
def floor_timestamp_row(row, floor_value):
    row['timestamp'] = row['timestamp'].floor(floor_value)
    return row

# Flooring function which supports different timestamps based on columns values
def floor_timestamp_dataframe(df, timestamp_floor):
    # We can floor data by different timestamps based on a specific columns values
    if type(timestamp_floor) ==  list:
        # Looping through columns values
        for floor_value in timestamp_floor:
            # Appyling rounding to a specific column value
            df = df.apply(lambda row: floor_timestamp_row(row, floor_value['timestamp_floor']) if row[floor_value['column_name']] == floor_value['column_value'] else row, axis=1)
    else:
        df['timestamp'] = df['timestamp'].dt.floor(timestamp_floor)
    return df

# Calculating median values from a group of dataframes
def calculate_median_values(dfs, grouping_fileds, value_field='value', timestamp_floor='1s'):
    # Concatenating dataframes together
    global_df = pd.concat(dfs, ignore_index=True)
    # Flooring timestamps
    global_df = floor_timestamp_dataframe(global_df, timestamp_floor)
    # Calculating median values
    result_df = global_df.groupby(grouping_fileds, as_index=False)[value_field].median()
    return result_df

# Calculating mean values from a group of dataframes
def calculate_mean_values(dfs, grouping_fileds, value_field='value', timestamp_floor='1s'):
    # Concatenating dataframes together
    global_df = pd.concat(dfs, ignore_index=True)
    # Flooring timestamps
    global_df = floor_timestamp_dataframe(global_df, timestamp_floor)
    # Calculating median values
    result_df = global_df.groupby(grouping_fileds, as_index=False)[value_field].mean()
    return result_df

# Calculating max values from a group of dataframes
def calculate_max_values(dfs, grouping_fileds, value_field='value', timestamp_floor='1s'):
    # Concatenating dataframes together
    global_df = pd.concat(dfs, ignore_index=True)
    # Flooring timestamps
    global_df = floor_timestamp_dataframe(global_df, timestamp_floor)
    # Calculating median values
    result_df = global_df.groupby(grouping_fileds, as_index=False)[value_field].max()
    return result_df

# Calculating min values from a group of dataframes
def calculate_min_values(dfs, grouping_fileds, value_field='value', timestamp_floor='1s'):
    # Concatenating dataframes together
    global_df = pd.concat(dfs, ignore_index=True)
    # Flooring timestamps
    global_df = floor_timestamp_dataframe(global_df, timestamp_floor)
    # Calculating median values
    result_df = global_df.groupby(grouping_fileds, as_index=False)[value_field].min()
    return result_df

# Create a plottable dataframe from kwollect dataframe
def create_plottable_df_for_kwollect(
    kwollect_df, 
    benchmark_name, 
    plot_prefix='kwollect', 
    targets=['wattmeter', 'bmc'],
    plotname_postfix=''
):
    # Construct result dataframe
    result_df = pd.DataFrame(columns=['timestamp', 'benchmark', 'plot_name', 'value'])

    if 'wattmeter' in targets:
        kwollect_wattmeter_df = copy.deepcopy(kwollect_df[kwollect_df['metric_id'] == 'wattmetre_power_watt'])
        kwollect_wattmeter_df["benchmark"] = benchmark_name
        kwollect_wattmeter_df["plot_name"] = f"{plot_prefix}_wattmeter"
        kwollect_wattmeter_df = kwollect_wattmeter_df.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, kwollect_wattmeter_df], ignore_index=True)

    if 'bmc' in targets:
        kwollect_bmc_df = copy.deepcopy(kwollect_df[kwollect_df['metric_id'] == 'bmc_node_power_watt'])
        kwollect_bmc_df["benchmark"] = benchmark_name
        kwollect_bmc_df["plot_name"] = f"{plot_prefix}_bmc"
        kwollect_bmc_df = kwollect_bmc_df.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, kwollect_bmc_df], ignore_index=True)

    result_df['plot_name'] = result_df['plot_name'] + plotname_postfix

    return result_df

# Create a plottable dataframe from a scaphandre dataframe
def create_plottable_df_for_scaphandre(
    scaphandre_df,
    benchmark_name,
    targets = ['host', 'dram', 'total', 'process'],
    plotname_postfix=''
):
    # Construct result dataframe
    result_df = pd.DataFrame(columns=['timestamp', 'benchmark', 'plot_name', 'value'])

    # Adding host values
    if 'host' in targets:
        scaphandre_host = copy.deepcopy(scaphandre_df[scaphandre_df['target'] == 'host'])
        scaphandre_host["benchmark"] = benchmark_name
        scaphandre_host["plot_name"] = f"scaphandre_host"
        scaphandre_host = scaphandre_host.filter(items=['timestamp', 'value', 'benchmark', 'plot_name'])
        result_df = pd.concat([result_df, scaphandre_host], ignore_index=True)

    # Adding dram values
    if 'dram' in targets:
        scaphandre_dram = copy.deepcopy(scaphandre_df[scaphandre_df['target'] == 'dram'])
        scaphandre_dram["benchmark"] = benchmark_name
        scaphandre_dram["plot_name"] = f"scaphandre_dram"
        scaphandre_dram = scaphandre_dram.filter(items=['timestamp', 'value', 'benchmark', 'plot_name'])
        result_df = pd.concat([result_df, scaphandre_dram], ignore_index=True)

    # Calculating and adding total values
    if 'total' in targets:
        # Calculating total consumption
        scaphandre_result_total = copy.deepcopy(scaphandre_df[(scaphandre_df['target'] == 'host') | (scaphandre_df['target'] == 'dram')])
        scaphandre_result_total = scaphandre_result_total.groupby(['timestamp'], as_index=False)['value'].sum(min_count=2)
        scaphandre_result_total = scaphandre_result_total.dropna(subset=["value"])
        scaphandre_result_total["benchmark"] = benchmark_name
        scaphandre_result_total["plot_name"] = f"scaphandre_total"
        scaphandre_result_total = scaphandre_result_total.filter(items=['timestamp', 'value', 'benchmark', 'plot_name'])
        result_df = pd.concat([result_df, scaphandre_result_total], ignore_index=True)

    # Adding process values
    if 'process' in targets:
        # Getting unique processes
        process_list = sorted(scaphandre_df[(scaphandre_df['target'] != "dram") & (scaphandre_df['target'] != "host")]['target'].unique())
    
        # Adding every process data
        for index, process in enumerate(process_list):
            # Get only the process data
            scaphandre_process = copy.deepcopy(scaphandre_df[scaphandre_df['target'] == process])
            scaphandre_process["benchmark"] = benchmark_name
            scaphandre_process["plot_name"] = f"scaphandre_process_{index+1}_cpu"
            #print(f"scaphandre_process_{index+1}_cpu = {process}")
            scaphandre_process = scaphandre_process.filter(items=['timestamp', 'value', 'benchmark', 'plot_name'])

            result_df = pd.concat([result_df, scaphandre_process], ignore_index=True)

    result_df['plot_name'] = result_df['plot_name'] + plotname_postfix

    return result_df

# Add data into result dataframe for a specific target and for specific scopes
def add_data_by_target_perf(result_df, df, targets, plot_prefix, benchmark_name):
    
    # Get entries by scope
    df_cpu_event = copy.deepcopy(df[df['event'] == 'power/energy-pkg/'])
    df_dram_event = copy.deepcopy(df[df['event'] == 'power/energy-ram/'])

    # Calculte the total consumption for both scopes
    df_total = pd.concat((df_cpu_event, df_dram_event)).groupby('timestamp',as_index=False).sum()

    # Adding values into result dataframe
    if 'cpu' in targets:
        df_cpu_event["benchmark"] = benchmark_name
        df_cpu_event["plot_name"] = f"{plot_prefix}_cpu"
        df_cpu_event = df_cpu_event.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, df_cpu_event], ignore_index=True)

    if 'dram' in targets:
        df_dram_event["benchmark"] = benchmark_name
        df_dram_event["plot_name"] = f"{plot_prefix}_dram"
        df_dram_event = df_dram_event.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, df_dram_event], ignore_index=True)

    if 'total' in targets:
        df_total["benchmark"] = benchmark_name
        df_total["plot_name"] = f"{plot_prefix}_total"
        df_total = df_total.filter(items=['timestamp', 'benchmark', 'plot_name', 'value'])
        result_df = pd.concat([result_df, df_total], ignore_index=True)

    return result_df


def create_plottable_df_for_perf(
    df,
    benchmark_name,
    targets = ['cpu', 'dram', 'total'],
    plotname_postfix=''
):
    # Construct result dataframe
    result_df = pd.DataFrame(columns=['timestamp', 'benchmark', 'plot_name', 'value'])

    # Calculate total consumption for all available sockets
    df = df.groupby(['timestamp', 'event'], as_index=False)['value'].sum()

    # Processing and adding global estimation into result dataframe
    result_df = add_data_by_target_perf(result_df, df, targets, 'perf', benchmark_name)

    return result_df

# Create a plottable dataframe from a energy scope dataframe
def create_plottable_df_for_energy_scope(
    energy_scope_df,
    benchmark_name,
    targets = ['cpu', 'dram', 'total'],
    plotname_postfix=''
):
    # Construct result dataframe
    result_df = pd.DataFrame(columns=['timestamp', 'benchmark', 'plot_name', 'value'])

    if 'cpu' in targets:
        result_df = add_data_by_target_energy_scope(result_df, energy_scope_df, benchmark_name, "data.data.ecpu(W)", "cpu")

    if 'dram' in targets:
        result_df = add_data_by_target_energy_scope(result_df, energy_scope_df, benchmark_name, "data.data.edram(W)", "dram")
        
    if 'total' in targets:
        result_df = add_data_by_target_energy_scope(result_df, energy_scope_df, benchmark_name, "data.data.etotal(W)", "total")

    result_df['plot_name'] = result_df['plot_name'] + plotname_postfix

    return result_df

# Add data into result dataframe by renaming and filtering value column
def add_data_by_target_energy_scope(result_df, energy_scope_df, benchmark_name, value_column, post_fix):
    energy_scope_df = copy.deepcopy(energy_scope_df.rename(columns={value_column : "value"}))
    energy_scope_df["benchmark"] = benchmark_name
    energy_scope_df["plot_name"] = f"energy_scope_{post_fix}"
    energy_scope_df = energy_scope_df.filter(items=['timestamp', 'value', 'benchmark', 'plot_name'])
    result_df = pd.concat([result_df, energy_scope_df], ignore_index=True)
    return result_df

# Get correlation dataframe by benchmark for a solution
def get_correlation_by_benchmark(experiments, experiment, solution, benchmark_delay_time):
    # Converting experiments to benchmarks with dataframes
    benchmarks = convert_exp_into_benchmark_dataframes(experiments, experiment, solution, benchmark_delay_time, timeshift = False)
    # Creating result dataframes
    result_df = pd.DataFrame(columns=['timestamp', 'wattmeter', 'tool', 'benchmark'])
    # Processing each benchmark
    for benchmark in benchmarks:
        # Get Solution and Kwollect dataframes lists
        solution_list = benchmarks[benchmark][solution]
        kwollect_list = benchmarks[benchmark]['kwollect']

        # For each dataframe we will join powerapi and kwollect values
        for index, _ in enumerate(solution_list):
            # Solution power values processing
            df_solution = solution_list[index]['dataframe']

            # Processing solution dataframe for correlation
            df_solution = dataframe_process_for_correlation_by_solution(df_solution, solution)

            # Kwollect power values processing
            df_kwollect = kwollect_list[index]['dataframe']

            # Processing kwollect dataframe for correlation
            df_kwollect = kwollect_process_for_correlation(df_kwollect, solution)

            # Merge PowerAPI and Kwollect values by timestamp
            joined_df = df_kwollect.merge(df_solution, on='timestamp', how='left')

            # Dropping rows where one of the values is empty
            joined_df_without_na = copy.deepcopy(joined_df.dropna(subset=["wattmeter", 'tool'])) 

            # Adding benchmark name to dataframe
            joined_df_without_na['benchmark'] = str(benchmark)

            # Adding joined dataframe to result dataframe
            result_df = pd.concat([result_df, joined_df_without_na], ignore_index=True)

    return result_df

# Get global correlation dataframe from experiment
def get_global_correlation(experiments, experiment_name, solution_name):
    # Creating result dataframe
    result_df = pd.DataFrame(columns=['timestamp', 'wattmeter', 'tool'])

    # Getting points from all experiments
    for experiment in experiments:
        # Get Solution dataframe
        solution = get_experiment(experiment, experiment_name)
        df_solution = get_consumption_dataframe(solution['results'], solution_name)

        # Processing solution dataframe for correlation
        df_solution = dataframe_process_for_correlation_by_solution(df_solution, solution_name)

        # Get Kwollect dataframe
        df_kwollect = get_consumption_dataframe(solution['results'], f"kwollect-{solution_name}")

        # Processing kwollect dataframe for correlation
        df_kwollect = kwollect_process_for_correlation(df_kwollect, solution_name)

        # Merge PowerAPI and Kwollect values by timestamp
        joined_df = df_kwollect.merge(df_solution, on='timestamp', how='left')

        # Dropping rows where one of the values is empty
        joined_df_without_na = joined_df.dropna(subset=["wattmeter", 'tool']) 

        # Adding joined dataframe to result dataframe
        result_df = pd.concat([result_df, joined_df_without_na], ignore_index=True)
    return result_df

def kwollect_process_for_correlation(df_kwollect, solution_name):
    # Round dataframe timestamp to one second
    df_kwollect['timestamp'] = df_kwollect['timestamp'].dt.floor('1s')
    
    # Select only wattmeter values and filter all other columns
    df_kwollect = df_kwollect[df_kwollect['metric_id'] == 'wattmetre_power_watt']
    df_kwollect = df_kwollect.filter(items=['timestamp', 'value'])

    # If solution is Scaphandre we will agregate wattmeter points by calculating mean value for the last 5 seconds
    if solution_name == 'scaphandre':
        df_kwollect = df_kwollect.groupby(pd.Grouper(key='timestamp', axis=0, freq='5S', sort=False)).mean()

    # Rename consumption values column
    df_kwollect = df_kwollect.rename(columns={'value': 'wattmeter'})

    return df_kwollect

def dataframe_process_for_correlation_by_solution(df_solution, solution):
    # If solution if powerapi we will prepare powerapi dataframe
    if solution == 'powerapi':
        # Calculate total consumption for all available sockets
        df_solution = df_solution.groupby(['timestamp', 'target', 'scope'], as_index=False)['power'].sum()
        # Calculate global consumption for both dram and cpu scopes
        df_solution = df_solution.groupby(['timestamp', 'target'], as_index=False)['power'].sum()
        # Selecting only rapl values and filter other columns
        # Round dataframe timestamp to one second
        df_solution['timestamp'] = df_solution['timestamp'].dt.floor('1s')

        df_solution = df_solution[df_solution['target'] == 'rapl']
        df_solution = df_solution.filter(items=['timestamp', 'power'])
        # Rename consumption values column
        df_solution = df_solution.rename(columns={'power': 'tool'})

    elif solution == 'scaphandre':
        # Empirically deducted that Pearson coefficient is better is we apply a timedelta of 5 seconds
        df_solution['timestamp'] = df_solution['timestamp'] - datetime.timedelta(seconds=5)
        
        # Get only cpu and dram related data
        df_solution = df_solution[(df_solution['target'] == 'host') | (df_solution['target'] == 'dram')]
        # We need at least 2 values of cpu and dram consumption in order to be able to calculate the total rapl consumption
        df_solution = df_solution.groupby(['timestamp'], as_index=False)['value'].sum(min_count=2)
        # Delete all lines where the global consumption was not calculated (value is NaN)

        # Round dataframe timestamp to one second
        df_solution['timestamp'] = df_solution['timestamp'].dt.floor('1s')
        
        df_solution = df_solution.dropna(subset=["value"])
        # Leave only necessary columns
        df_solution = df_solution.filter(items=['timestamp', 'value'])
        # Rename consumption value column
        df_solution = df_solution.rename(columns={"value": "tool"})

    elif solution == 'energyscope':
        # Round dataframe timestamp to 500 ms = acquisition frequency of energy scope
        df_solution['timestamp'] = df_solution['timestamp'].dt.floor('500ms')
        # Empirically deducted that correlation is better is we apply a timedelta of 500ms
        #df_solution['timestamp'] = df_solution['timestamp'] + datetime.timedelta(microseconds=500000)
        # Leave only necessary columns
        df_solution = df_solution.filter(items=['timestamp','data.data.etotal(W)'])
        # Calculating mean consumption values from each second to be able to compare with wattmeter
        df_solution = df_solution.groupby(pd.Grouper(key='timestamp', axis=0, freq='S', sort=False)).mean()
        # Rename consumption value column
        df_solution = df_solution.rename(columns={"data.data.etotal(W)": "tool"})

    elif solution == 'perf':
        df_solution = df_solution.groupby(['timestamp'], as_index=False)['value'].sum()
        # Round dataframe timestamp to 500 ms = acquisition frequency of energy scope
        df_solution['timestamp'] = df_solution['timestamp'].dt.floor('100ms')
        # Empirically deducted that correlation is better is we apply a timedelta of 500ms
        df_solution['timestamp'] = df_solution['timestamp'] + datetime.timedelta(microseconds=500000)
        # Leave only necessary columns
        df_solution = df_solution.filter(items=['timestamp','value'])
        # Calculating mean consumption values from each second to be able to compare with wattmeter
        df_solution = df_solution.groupby(pd.Grouper(key='timestamp', axis=0, freq='S', sort=False)).mean()
        # Rename consumption value column
        df_solution = df_solution.rename(columns={"value": "tool"})

    else:
        return None

    return df_solution

def calculate_energyscope(energy_scope_dataframes, calculation_function, timestamp_floor='500ms'):
    ## Calculate a median value dataframe
    values_df_cpu = calculation_function(energy_scope_dataframes, ['timestamp'], 'data.data.ecpu(W)', timestamp_floor)
    values_df_dram = calculation_function(energy_scope_dataframes, ['timestamp'], 'data.data.edram(W)', timestamp_floor)
    values_df_total = calculation_function(energy_scope_dataframes, ['timestamp'], 'data.data.etotal(W)', timestamp_floor)
    
    ### Merging median values dataframes
    values_df = pd.merge(values_df_cpu, values_df_dram, on="timestamp")
    values_df = pd.merge(values_df_total, values_df, on="timestamp")

    return values_df


# Calculate the overall consumption for every benchmark
def calculate_total_consumption(result_df, benchmark_dfs, tool):
    for benchmark in benchmark_dfs:
        for kwollect_result in benchmark_dfs[benchmark]['kwollect']:
            kwollect_df = kwollect_result['dataframe']
            kwollect_result_wattmetre = copy.deepcopy(kwollect_df[kwollect_df['metric_id'] == 'wattmetre_power_watt'])
            kwollect_result_wattmetre['timestamp'] = kwollect_result_wattmetre['timestamp'].dt.floor('1s')

            # Calculate overall consumption from dataframe
            overall_consumption_wattmetre = overall_consumption_from_df(kwollect_result_wattmetre)

            # Adding consumption data to dataframe
            result_df = add_consumption_value_to_df(result_df, {
                'benchmark': str(benchmark),
                'tool': tool,
                'value': overall_consumption_wattmetre[0]
            })

    return result_df