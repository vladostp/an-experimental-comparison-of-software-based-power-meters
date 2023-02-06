"""Functions to retrieve wattmeter data for all experiments and integrate them into the dataset.

The functions can be used to merge the results. The output of the file can be easily processed.
The results need to be synchronised with the experiment table (throught the experiment table).
    - add_benchmark_id_to_merged_timeseries().
The timestamps need to be synchronised: add_benchmark_id_to_merged_timeseries().
The energy results need to be converted to same unit:
    - convert_energy_scope_timeseries_to_sec(), 
    - convert_bmc_to_sec(), 
    - convert_watt_to_sec(), 
    - energy_scope_timestamp_to_sec().
For Energy Scope and the physical wattmeters, the total energy needs to be computed:
    - retrieve_wattmeter_data(), 
    - compute_energy_per_benchmark().
The results need to be cleaned in general:
    - set_repetition_to_ten(),
    - cleaning_table().

Typical use (on grid5000):
```
module load miniconda3
source activate gpu_benchmark
python utils/process_results.py --local_git_dir "/home/mjay/GPU_benchmark_energy/" --distant_directory "/root/energy-consumption-of-gpu-benchmarks/" --result_folder "/home/mjay/GPU_benchmark_energy/results/night_exp_08_11/"
```
To merge Energy Scope and Wattmeter data of various experiments:

```
local_git_dir = "/home/mjay/GPU_benchmark_energy/" 
prefix = [local_git_dir + "results/night_exp_20_04/", local_git_dir + "results/night_exp_19_04/"]

energy_scope_df = pd.concat([pd.read_csv(file + 'es_ts.csv') for file in prefix])
watt_df = pd.concat([pd.read_csv(file + 'g5k_metrics.csv') for file in prefix])
exp_table = pd.concat([pd.read_csv(file + 'processed_table.csv') for file in prefix])

grouped_watt_df = watt_df.groupby(by=['timestamp_sec']).mean().reset_index()
merged_df = pd.merge(energy_scope_df,grouped_watt_df, on='timestamp_sec', how='outer').sort_values(by=['timestamp_sec'])
merged_df['wattmetre_es_diff'] = abs(merged_df['wattmetre_power_watt'] - merged_df['data.data.etotal(W)'])
b_df = add_benchmark_id_to_merged_timeseries(exp_table, merged_df)

b_df.plot(x='timestamp_sec', figsize=(20,15), linestyle=' ', marker='.')
plt.legend(bbox_to_anchor=(1.1, 1))
```

"""
import argparse
import datetime
import pandas as pd
import time
import numpy as np
import getpass
import os
import logging
from requests import auth
import sys

def get_g5k_auth():
    user = getpass.getpass(prompt='Grid5000 login:')
    password = getpass.getpass(prompt='Grid5000 password:')
    return auth.HTTPBasicAuth(user, password)

def convert_paths(cell, local_directory, distant_directory):
    """Converting the table paths."""
    if type(cell) is str and distant_directory in cell:
        return local_directory + '/' +  "/".join(cell.split("/")[3:])
    return cell

def convert_bmc_to_sec(s):
    return time.mktime(
        datetime.datetime.strptime(
            s, 
            "%Y-%m-%dT%H:%M:%S.%f+01:00"
            ).timetuple())

def convert_watt_to_sec(s):
    return time.mktime(
        datetime.datetime.strptime(
            s, 
            "%Y-%m-%dT%H:%M:%S+01:00"
            ).timetuple())

def energy_scope_timestamp_to_sec(timestamp):
    return time.mktime(
        datetime.datetime.strptime(
            timestamp, 
            "%Y/%m/%d %H:%M:%S.%f"
            ).timetuple())

def retrieve_wattmeter_data(Wattmeter, table, auth):
    """Get wattmetre data with http request for every experiment in table.
    
    args:
        table: DataFrames. Table describing experiments.
        auth: HTTP Authentification for http requests to the wattmeter database.
    """
    # retrieving wattmeter data afterwards
    full_df = pd.DataFrame()
    for table_id in table.index:
        start, stop = table.loc[table_id][['gpu_0_start_benchmark', 'gpu_0_stop_benchmark']]
        wattmeter_data = Wattmeter(
            table.loc[table_id]['node'], 
            table.loc[table_id]['site'], 
            start - table.loc[table_id]['gpu_0_sleep_before'], 
            stop + table.loc[table_id]['gpu_0_sleep_after'],
            auth,
            metrics=["wattmetre_power_watt", "bmc_node_power_watt"],
        )
        for metric in wattmeter_data.metrics:
            apply_fct = convert_bmc_to_sec if 'bmc' in metric else convert_watt_to_sec
            df = wattmeter_data.results[metric]['data']
            df['timestamp_sec']=df['timestamp'].apply(apply_fct)
            full_df = pd.concat([full_df, df], ignore_index=True)
    return full_df

def convert_energy_scope_timeseries_to_sec(table):
    """Creates energy scope timeseries from table describing experiments.
    
    Goes throught all experiments involving Energy Scope and builts
    its timeserie dataframe.
    
    args:
        table: DataFrames. Table describing experiments.

    returns:
        table: DataFrames. Table containing the timeseries concatenated.
    """
    energy_scope_df = pd.DataFrame()

    for exp_id in table[table['tool_name']=='energy scope']['exp_id'].unique():
        es_param_file = table[table['exp_id']==exp_id]['tool_parameters'].values[0]
        es_param_df = pd.read_csv(es_param_file)

        # Fetch corresponding timeserie file
        es_file = table[table['exp_id']==exp_id]['tool_csv_file'].values[0]
        es_df = pd.read_csv(es_file)

        scope_start = es_param_df['data.data.tags.es_total.start'][0]
        scope_start_sec = energy_scope_timestamp_to_sec(scope_start)

        scope_stop = es_param_df['data.data.tags.es_total.stop'][0]
        scope_stop_sec = energy_scope_timestamp_to_sec(scope_stop)

        # Converting in seconds
        step = es_param_df['data.data.eprofile_period(ms)'][0]*0.001 

        # Recreating timestamps
        timestamps=np.arange(int(scope_start_sec),int(scope_stop_sec), step)[:-1]

        es_df['timestamp_sec']=timestamps

        cols_to_rename = [col for col in es_df.columns if "arch" in col]
        new_names = ['.'.join(col.split('.')[3:]) for col in cols_to_rename]
        renaming_dict = dict(zip(cols_to_rename, new_names))
        es_df = es_df.rename(columns=renaming_dict)

        energy_scope_df = pd.concat([energy_scope_df, es_df], ignore_index=True)
        
    return energy_scope_df

def compute_energy_per_benchmark(table, timeserie_df, table_energy_column, timeserie_df_power_column, bench_ids=None):
    """Modifies table by computing energy from power timeseries.
    
    Since experiments sometimes include several benchmarks, we need to compute the energy 
    for each benchmark and for each energy column.
    Returns the corrected description table.
    
    args:
        table: DataFrame. Table describing experiments.
        timeserie_df: DataFrame. Timeseries to compute energy from.
        table_energy_column: string. Name of the energy column to correct in table.
        timeserie_df_power_column: string. Name of the power column
            to compute the energy from.
        bench_ids: List of strings. Subset of benchmarks ids to process.
            None by default.
    
    returns:
        corrected description table: DataFrame
    """
    if bench_ids is None:
        bench_ids = table['gpu_0_benchmark_id'].unique()
    for bench_id in bench_ids:
        # get benchmark start and stop time
        start, stop = table[
            (table['gpu_0_benchmark_id'] == bench_id)
        ][['gpu_0_start_benchmark', 'gpu_0_stop_benchmark']].values[0]
        # Retrieves power timeserie between the start and stop time
        bench_df = timeserie_df[
            (timeserie_df['timestamp_sec']>=start)&(timeserie_df['timestamp_sec']<=stop)
            ].reset_index(
                drop=True
            ).sort_values(
                by=['timestamp_sec']
            )[['timestamp_sec', timeserie_df_power_column]].dropna()
        # Compute energy = power * duration between datapoints
        bench_df['energy(Ws)'] = bench_df['timestamp_sec'].diff()*bench_df[timeserie_df_power_column]
        total_energy_kWh = bench_df['energy(Ws)'].sum()*1e-3/3600
        # update the table
        index = table[(table['gpu_0_benchmark_id'] == bench_id)].index[0]
        table.at[index, table_energy_column] = total_energy_kWh
    return table

def add_benchmark_id_to_merged_timeseries(table, merged_df, time_before_start=None, time_after_end=None):
    """Adding the corresponding benchmark id to merged_df.
    
    args:
        table: DataFrame. Table describing experiments.
        merged_df: DataFrame. Timeseries of both energy scope and wattmeter data.

    returns:
        DataFrame.
    """
    b_df = pd.DataFrame()
    bench_ids = table['gpu_0_benchmark_id'].unique()
    for bench_id in bench_ids:  # ADD LOOP FOR GPU
        # Get the benchmark data
        bench_table = table[
            (table['gpu_0_benchmark_id'] == bench_id)
        ]
        start, stop = bench_table[['gpu_0_start_benchmark', 'gpu_0_stop_benchmark']].values[0]
        start = start - time_before_start if time_before_start is not None else start - bench_table['gpu_0_sleep_before'].values[0]
        stop = stop + time_after_end if time_after_end is not None else stop + bench_table['gpu_0_sleep_after'].values[0]
        appli = bench_table['gpu_0_appli'].values[0]
        appli_class = bench_table['gpu_0_appli_class'].values[0]

        # create a df of the benchmark
        bench_df = merged_df[
            (merged_df['timestamp_sec']>=start)&(merged_df['timestamp_sec']<=stop)
            ].reset_index(drop=True)
        # Adding more data on the benchmark
        bench_df['sec']= bench_df['timestamp_sec']-bench_df['timestamp_sec'].min()
        bench_df['benchmark_id'] = bench_id
        bench_df['benchmark_appli'] = "{} {}".format(appli.upper(), appli_class)
        b_df = pd.concat([b_df, bench_df])
        
    return b_df.dropna(subset=['benchmark_id']) 


def b_df_for_plotting(energy_scope_df, watt_df, table):
    """Creates a multi-column dataframe with timestamps starting at the benchmark start.

    The timeseries are modified so that all missing values are replaced by the closest values 
    (close in term of timestamp). Computing statistics per timestamps is easier but the results
    are not exactly accurate since values can be moved around for a few seconds, 
    especially for BMC values.
    A left join is done, with the left columns being energy scope timeseries, since 
    the acquisition frequency is the highest.
    
    Level 1: benchmark ids.
    Level 2: Timeseries with timestamps starting at 0.

    Alternative:
    ```
    grouped_watt_df = watt_df.groupby(by=['timestamp_sec']).mean().reset_index()
    grouped_watt_df['timestamp'] = pd.to_datetime(
        grouped_watt_df['timestamp_sec'].apply(
            lambda x: time.asctime(time.localtime(x))
        )
    )
    interpolated_df['bmc_node_power_watt'] = interpolated_df['bmc_node_power_watt'].interpolate(method='linear')
    ```
    
    args:
        energy_scope_df: DataFrame. Energy Scope timeseries.
        watt_df: DataFrame. Wattmeter timeseries.
        table: DataFrame. Describing experiments.
    returns:
        DataFrame. 
            Level 1: benchmark ids
            Level 2: Timeseries with timestamps starting at 0.
    """
    bmc_df = watt_df[['timestamp_sec', 'bmc_node_power_watt']].dropna()
    wattemtre_df = watt_df[['timestamp_sec', 'wattmetre_power_watt']].dropna()
    watt_df = pd.merge_asof(
        wattemtre_df.sort_values(by=['timestamp_sec']), 
        bmc_df.sort_values(by=['timestamp_sec']), 
        on='timestamp_sec').dropna()
    merged_df = pd.merge_asof(
        energy_scope_df.sort_values(by=['timestamp_sec']),
        watt_df.sort_values(by=['timestamp_sec']), 
        on='timestamp_sec')
    merged_df['wattmetre_es_diff'] = abs(merged_df['wattmetre_power_watt'] - merged_df['data.data.etotal(W)'])
    b_df = add_benchmark_id_to_merged_timeseries(table, merged_df)
    return merged_df, b_df

def read_bench_csv(bench_csv_file):
    """Loads benchmark dataframes.
    
    Saving multi-columns timeseries is complexe. This function allows
    to recreate the identical dataframe.
    """
    b_df = pd.read_csv(bench_csv_file, low_memory=False)
    bench_time_series = {}
    bench_ids = list(set([col.split('.')[0] for col in b_df.columns]))
    for bench_id in bench_ids:
        bench_df = b_df[[col for col in b_df.columns if col.split('.')[0]==bench_id]].rename(columns=b_df.iloc[0]).drop(0)
        bench_df = bench_df.astype({col:float for col in bench_df.columns if col!='timestamp'})
        bench_time_series[bench_id]=bench_df
    return pd.concat(bench_time_series, axis=1)  

def remove_PUE(row):
    if row['tool_name']=='experiment_impact_tracker':
        return row['tool_energy_consumption(kWh)']/1.58
    elif row['tool_name']=='carbon_tracker':
        return row['tool_energy_consumption(kWh)']/1.67
    else:
        return row['tool_energy_consumption(kWh)']

def set_repetition_to_ten(exp_table, repetition_nb = 10):
    """Clean the experiment table by remove extra repetitions."""
    to_delete = []
    for tool_name in exp_table['tool_name'].unique():
        es_table = exp_table[(exp_table['tool_on_one_process']==False)&(exp_table['tool_name']==tool_name)]
        idx = es_table.set_index(['gpu_0_appli','gpu_0_appli_class']).index.unique()
        for i in range(len(idx)):
            appli = idx[i][0]
            appli_class = idx[i][1]
            indexes_to_delete = exp_table[(
                exp_table['gpu_0_appli']==appli)&(
                exp_table['gpu_0_appli_class']==appli_class)&(
                exp_table['tool_name']==tool_name)&(
                exp_table['tool_on_one_process']==False
            )][:-repetition_nb].index.values
            to_delete = to_delete + list(indexes_to_delete)
    return exp_table.drop(to_delete, axis=0).reset_index(drop=True)

def cleaning_table(exp_table, watt_df, energy_scope_df):
    """Pre-processing results.

    - Set the number of experiments per configuration to 10.
    - Compute energy sum 
    
    args:
        exp_table: DataFrame. Experiment table.
        watt_df: DataFrame. Wattmeter df.
        energy_scope_df: DataFrame. Energy Scope df.

    returns:
        exp_table: DataFrame. Updated experiment table.
    """
    logging.info("Correcting energy per benchmark")
    exp_table = exp_table[exp_table['error'].isna()].reset_index(drop=True)
    exp_table = set_repetition_to_ten(exp_table)
    exp_table['tool_energy_consumption(kWh)_no_PUE'] = exp_table.apply(remove_PUE, axis=1)
    exp_table = compute_energy_per_benchmark(
        exp_table, watt_df, 'bmc_node_power_watt_energy_consumption(kWh)', 'bmc_node_power_watt')
    exp_table = compute_energy_per_benchmark(
        exp_table, watt_df, 'wattmetre_power_watt_energy_consumption(kWh)', 'wattmetre_power_watt')
    exp_table = compute_energy_per_benchmark(
        exp_table, energy_scope_df, 
        'tool_energy_consumption(kWh)', 
        'data.data.etotal(W)', 
        bench_ids=exp_table[exp_table['tool_name']=='energy scope']['gpu_0_benchmark_id'].unique()
        )
    return exp_table
    
def parsing_arguments():
    parser = argparse.ArgumentParser(description='Process results')
    parser.add_argument('--local_git_dir', 
                        help='Path to the local git repository.', 
                        type=str)
    parser.add_argument('--distant_directory', 
                        help='Path to the directory in gemini.', 
                        type=str, default='/root/energy-consumption-of-gpu-benchmarks/')
    parser.add_argument('--result_folder', 
                        help='Path to the result folder.', 
                        type=str)
    return parser.parse_args()

def main():
    logging.basicConfig(level=logging.INFO)
    
    args = parsing_arguments()

    local_git_dir = args.local_git_dir # "/Users/mathildepro/Documents/code_projects/GPU_benchmarks/" #
    distant_directory = args.distant_directory #"/root/energy-consumption-of-gpu-benchmarks/"
    #local_git_dir = "/home/mjay/GPU_benchmark_energy/" 
    prefix = args.result_folder # local_git_dir + "results/night_exp_08_11/"
    experiments_table = prefix + "/experiment_table.csv"
    merged_table_csv_file = prefix + "/processed_table.csv"
    es_timeseries_csv_file = prefix + '/es_ts.csv'
    wattmeter_csv_file = prefix + '/g5k_metrics.csv'
    
    sys.path.append(local_git_dir+"/code/")

    from utils.tools import Wattmeter
    
    # Experiment metadata
    exp_table = pd.DataFrame()
    logging.info("Retrieving data from " + experiments_table)
    exp_table = pd.read_csv(experiments_table)
    logging.info(exp_table['result_dir'].unique()[:5])

    # Modify the table if the location of the directory has changed
    # Typically when the experiments were done in grid5000 and the analysis locally 
    # however the fct convert_paths needs to be modify depending on your case
    logging.info("File directory "+ os.path.dirname(os.path.abspath(__file__)))
    exp_table = exp_table.applymap(lambda cell: convert_paths(cell, local_git_dir, distant_directory))
    logging.info(exp_table['result_dir'].unique()[:5])

    
    # Getting timeseries from tool result files
    logging.info("Retrieving energy scope data")
    energy_scope_df = convert_energy_scope_timeseries_to_sec(exp_table)
    logging.info(energy_scope_df.head())
    energy_scope_df.to_csv(es_timeseries_csv_file, index=False)

    # Retrieving wattmeter data
    logging.info("Retrieving wattmeter data")
    auth = get_g5k_auth()
    watt_df = retrieve_wattmeter_data(Wattmeter, exp_table, auth)
    logging.info(watt_df.head())
    watt_df.to_csv(wattmeter_csv_file, index=False)

    # Correct total energy per benchmark
    exp_table = cleaning_table(exp_table, watt_df, energy_scope_df)
    # This takes too much time so it is discarded
    exp_table.to_csv(merged_table_csv_file, index=False)
    
if __name__ == '__main__':
    main()