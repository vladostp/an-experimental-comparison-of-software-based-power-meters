"""How to use the software wattmeters or as called here, the power tools.

The Wattmeter class allows to retrieve wattmeter data.
The PowerTool class is a skeleton for every Tool class.
    It contains a method to start the tools with the benchmarks in various ways: 
        - with the benchmark in parallel,
        - the tool monitoring one benchmark or all of them.
    The results are processed depending on the tool outputs.

Typical use:

tool = EnergyScope("./")
bench_timestamps, output = tool.launch_experiments(
    benchmarks, # Benchmark object
    False,
)
print(tool.process_power_results())

# ...
wattmeter_data = Wattmeter(
    "gemini", 
    "lyon", 
    2022-04-20T17:49:26+02:00, 
    2022-04-20T18:49:26+02:00,
    _,
)
print(wattmeter_data.results["wattmetre_power_watt"]['energy_kWh'])
"""
import datetime
import json
import logging
from multiprocessing import Pool
import os
import time
from typing import Tuple, List
import glob

import requests
# you may need to install requests for python3 with sudo-g5k apt install python3-requests
import pandas as pd
import numpy as np

def merge_dict_with_identical_keys(dicts):
    new_dict = {}
    for key in dicts[0].keys():
        new_dict[key]=[]
        for dico in dicts:
            if type(dico[key])==list:
                new_dict[key] = new_dict[key] + dico[key]
            else:
                new_dict[key].append(dico[key])
    return new_dict  
    
def convert_energy_joule_in_kWh(energy_joule: float) -> float:
    """Converts joule in kWh"""
    return energy_joule/3600*10**(-3)

def convert_energy_kWh_in_joules(energy_kWh: float) -> float:
    """Converts kWh in Joules"""
    return energy_kWh*3600*10**(3)

def compute_time_serie_energy_joule(serie, interval) -> float:
    """Returns total energy in Joule. 
    
    args:
        serie: List. Time serie of power values in watt
        interval: float. Time interval in seconds
    """
    return np.sum(serie * interval) # in Joule
    
class Wattmeter:

    def __init__(
        self, 
        node: str, 
        site: str, 
        start: float, 
        stop: float, 
        g5k_auth = None,
        metrics: List[str] = ["wattmetre_power_watt", "bmc_node_power_watt", "pdu_outlet_power_watt"], 
        margin=30,
        ) -> None:

        self.node = node
        self.site = site
        self.start = start
        self.stop = stop
        self.metrics = metrics
        self.g5k_auth = g5k_auth
        self.plot_start, self.plot_stop = self.process_timestamps(margin=margin)
        self.energy_start, self.energy_stop = self.process_timestamps()
        self.results = {}
        raw_data = self.retrieve_power()
        for metric in metrics:
            self.results[metric]={}
            self.results[metric]['plot_data'] = self.process_power(metric, raw_data)
            self.results[metric]['data'] = self.results[metric]['plot_data'][
                (
                    self.results[metric]['plot_data']['timestamp'] < self.energy_stop
                )&(
                    self.results[metric]['plot_data']['timestamp'] > self.energy_start
                )
            ]
            self.results[metric]['energy_joule'] = compute_time_serie_energy_joule(
                self.results[metric]['data'][metric].values, 1)
            self.results[metric]['energy_kWh'] = convert_energy_joule_in_kWh(self.results[metric]['energy_joule'])
    
    def process_timestamps(self, margin=0) -> Tuple[str, str]:
        request_start = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.start - margin))
        request_stop = time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(self.stop + margin))
        return request_start, request_stop

    def retrieve_power(self) -> List[dict]:
        """
        one dictionnary for every power data point. One data point every seconds.
        returns list of dictionnaries.
        """
        url = "https://api.grid5000.fr/stable/sites/%s/metrics?metrics=%s&nodes=%s&start_time=%s&end_time=%s" \
                % (self.site, ','.join(self.metrics), self.node, self.plot_start, self.plot_stop)
        logging.info(url)
        if self.g5k_auth is not None:
            return requests.get(url, auth=self.g5k_auth, verify=False).json()  # 
        else:
            return requests.get(url, verify=False).json() 


    def process_power(self, metric: str, raw_data: dict) -> pd.DataFrame:
        """
        Converts list of dict to dataframe 
        
        Format of raw data: List of dict:
            {
            'timestamp': '2022-02-25T09:02:15.40325+01:00', 
            'device_id': 'chifflet-7', 
            'metric_id': 'bmc_node_power_watt', 
            'value': 196, 
            'labels': {}
            }
        
        returns:
            df with columns "timestamp", "value"
        """
        timestamps = np.array([d['timestamp'] for d in raw_data if d['metric_id']==metric])
        values = np.array([d['value'] for d in raw_data if d['metric_id']==metric])
        dict_for_df = {'timestamp': timestamps, metric:values}
        return pd.DataFrame(dict_for_df)
    
    def save_power(self, result_dir: str) -> None:
        for metric in self.metrics:
            path = result_dir+metric+".csv"
            self.results[metric]["csv_file"]=path
            self.results[metric]['data'].to_csv(path, index=False)


class PowerTool:
    """Super class for power tool objects.

    Because all should have in commun:
    - a directory to save the results in
    - a method to process results that return a csv file or a data frame
    - a method to be launched (alongside a list of benchmarks)

    Attributes:
        result_dir: A string of the absolute path of the folder to save the 
            results in.
    """
    def __init__(
        self, 
        result_dir: str,
        tool_name: str,
        ) -> None:
        self.result_dir = result_dir
        self.tool_name = tool_name
        
    def start_script(self, args):
        logging.info("Starting start_script")
        script, _ = args
        stream = os.popen(script)
        return stream.read()
    
    def start_script_parallel(self, args):
        logging.info("Starting start_script_parallel")
        scripts, worker_nb = args
        map_args = [(scripts[i], worker_nb) for i in range(len(scripts))]
        with Pool(processes=worker_nb) as pool:
            output_list = pool.map(self.start_script, map_args)
        return "\n".join(output_list)
    
    def start_without_tool(self, args):
        logging.info("Starting start_without_tool")
        script, sleep_before, sleep_after, nb_workers, _, script_fct = args
        # sleep to calm the machine down
        time.sleep(sleep_before)
        args = script, nb_workers
        output = script_fct(args)
        time.sleep(sleep_after)
        return output

    def start_tool(
        self, 
        scripts, 
        sleep_before, 
        sleep_after, 
        nb_workers, 
        _, 
        script_fct,
    ):
        # add import of the package
        time.sleep(sleep_before)
        # add code here to start the tool
        args = scripts, nb_workers
        output = script_fct(args)
        # add code here to stop the tool
        time.sleep(sleep_after)
        logging.info("Execution of PowerTool DONE")
        return output
    
    def start_tool_on_one_process(
        self, 
        scripts, 
        sleep_before, 
        sleep_after, 
        nb_workers,
        bench_id,
        script_fct,
    ):
        logging.info("Starting start_tool_on_one_process")
        apply_async_args = (scripts[0], sleep_before, sleep_after, nb_workers, bench_id, script_fct)
        map_args = [(scripts[i], sleep_before, sleep_after, nb_workers, bench_id, script_fct) for i in range(1,len(scripts))]
        with Pool(processes=nb_workers) as pool:
            tool_result = pool.apply_async(self.start_tool, apply_async_args)
            output_list = pool.map(self.start_without_tool, map_args)
            tool_result = tool_result.get()
        output_list.append(tool_result)
        
        return "\n".join(output_list)

    def launch_experiments(self, benchmarks, tool_on_one_process=False) -> str:
        
        nb_workers = len(benchmarks)
        loop_size = len(benchmarks[0])
        output = ""
        bench_timestamps = []
        # For every experiment to run
        for i in range(loop_size):
            logging.info("Starting loop {} experiment".format(i))
            
            # generate bash scrit to be executed by start_script
            scripts = []
            bench_id = []
            for bench in benchmarks: # every bench to execute in parallel
                bench[i].generate_script(with_sleep=False)
                scripts.append(bench[i].execution_script_path)
                bench_id.append(bench[i].benchmark_id)
                
            sleep_before = benchmarks[0][0].sleep_before
            sleep_after = benchmarks[0][0].sleep_after
            
            if tool_on_one_process:
                fct = self.start_tool_on_one_process 
                script_fct = self.start_script
            else:
                fct = self.start_tool
                script_fct = self.start_script_parallel
                
            loop_output = fct(
                scripts, 
                sleep_before, 
                sleep_after, 
                nb_workers,
                bench_id,
                script_fct,
            )
            
            bench_timestamps.append(self.process_stdout(loop_output))
            output = "\n".join([loop_output,output])
            logging.info(loop_output)
            logging.info("bench timestamps: {}".format(bench_timestamps))
        
        return merge_dict_with_identical_keys(bench_timestamps), output   
    
    def process_stdout(self, output):
        res = {}
        for line in output.split('\n'):
            if 'BENCHMARK_TAG' in line:
                # read line
                info = line.split(' ')
                start_or_stop = info[1]
                gpu_number = info[3]
                date = info[5]
                # add to dict
                key = "gpu_{}_{}".format(gpu_number, start_or_stop)
                if key not in res.keys():
                    res[key]=[]
                res[key].append(
                    datetime.datetime.strptime(
                        date, '%Y/%m/%dT%H:%M:%S.%f'
                    ).timestamp()
                )
        return res
    
    def process_power_results(self):
        """Returns whatever power information given by tool"""
        return {}


class PyJoules(PowerTool):
    """Implement PowerTool methods for pyJoules."""
    def __init__(
        self, 
        result_dir: str, 
        ) -> None:
        
        from pyJoules.device import DeviceFactory
        from pyJoules.device.rapl_device import RaplPackageDomain, RaplDramDomain
        from pyJoules.device.nvidia_device import NvidiaGPUDomain
        
        domains = [
            RaplPackageDomain(0), 
            RaplDramDomain(0), 
            NvidiaGPUDomain(0),
            RaplPackageDomain(1), 
            RaplDramDomain(1), 
            NvidiaGPUDomain(1),
            ]
        
        super().__init__(result_dir, "pyjoules")
        self.traces = []
        self.domains = domains
        self.devices = DeviceFactory.create_devices(self.domains)
        
    def start_tool(
        self, 
        scripts, 
        sleep_before, 
        sleep_after, 
        nb_workers, 
        bench_id, 
        script_fct,
    ):
        from pyJoules.energy_meter import EnergyMeter
        
        logging.info("Starting the execution of py joules.")
        # create pyjoules object
        meter = EnergyMeter(self.devices)
        
        # sleep to calm the machine down
        time.sleep(sleep_before)
        # start measurement
        meter.start()
        args = scripts, nb_workers
        output = script_fct(args)
        logging.info(output)
        meter.stop()
        # save measurement
        self.traces.append(meter.get_trace())
        time.sleep(sleep_after)
        logging.info("Execution of PyJoules DONE")
        return output
    
    def convert_pyjoule_df(self, df):
        for col in df.columns:
            logging.info("going through "+col)
            if "energy" in col:
                df[col] = df[col].apply(convert_energy_joule_in_kWh)
                if "nvidia" in col:
                    logging.info(df[col])
                    df[col] = df[col]*10**(-3)
                else:
                    logging.info(df[col])
                    df[col] = df[col]*10**(-6)
        return df
                

    def process_power_results(self) -> dict:
        """
        Fetches the pyjoules results from the traces.
        Values related to CPUs are in uJ = 10**(-6) Joules
        Values related to GPUs (nvml) are in mJ = 10**(-3) Joules

        A pyjoule trace looks like this:
            print(trace[0].__dict__)
            {
            'timestamp': 1646059462.6163714,
            'tag': '', 'duration': 2.8429646492004395, 
            'energy': 
                {
                'package_0': 109109401.0, 
                'dram_0': 34332037.0, 
                'nvidia_gpu_0': 354182
                }
             }

        returns dict with traces parameter as list, like this:
            {'pyjoule_timestamp': [1646059462.6163714, 1646059475.4881787],
             'pyjoule_tag': ['', ''],
             'pyjoule_duration': [2.8429646492004395, 2.8492867946624756],
             'pyjoule_energy_package_0': [109109401.0, 109345423.0],
             'pyjoule_energy_dram_0': [34332037.0, 34457191.0],
             'pyjoule_energy_nvidia_gpu_0': [354182, 355131]}
        """
        results = pd.DataFrame()
        for trace in self.traces:
            trace_flatten = pd.json_normalize({'pyjoule':trace[0].__dict__}, sep='_').to_dict('records')
            results = pd.concat([results, pd.DataFrame(trace_flatten)], ignore_index=True)
        del self.traces
        del self.domains
        del self.devices
        # Compute total energy
        logging.info(results)
        results = self.convert_pyjoule_df(results)
        logging.info(results)
        energy_cols = [col for col in results.columns if "energy" in col]
        results["tool_energy_consumption(kWh)"] = results[energy_cols].sum(axis=1)
        # Rename columns
        renamed_col = {
            'pyjoule_duration': "tool_duration(seconds)",
            "pyjoule_timestamp": "tool_timestamp(seconds)",
        }
        results = results.rename(columns=renamed_col)
        return results.to_dict('list')
    

class ExperimentImpactTracker(PowerTool):
    """Implement PowerTool methods for experiment-impact-tracker (EIT).

    Since this a python library, and it is not possible to put tags in the
    tracking, we have to launch the benchmarks one by one.
    EIT provide us with log files. 

    return list of energy metrics
    """
    def __init__(
        self, 
        result_dir: str, 
        ) -> None:    
        super().__init__(result_dir, "experiment_impact_tracker")
        self.log_dirs = []
    
    def start_tool(self, scripts, sleep_before, sleep_after, nb_workers, bench_id, script_fct):
        logging.info("Starting the execution of EIT.")
        from experiment_impact_tracker.compute_tracker import ImpactTracker
        
        time.sleep(sleep_before)
        
        log_dir = self.result_dir+bench_id[0]+"/"
        with ImpactTracker(log_dir):
            args = scripts, nb_workers
            output = script_fct(args)
        self.log_dirs.append(log_dir)

        time.sleep(sleep_after)
        logging.info("Execution of EIT DONE")
        return output

    def process_power_results(self) -> dict:
        """
        Fetches the experiment-impact-tracker results from the log files.

        returns
            carbon emissions in kg
            energy in kWh
            duration of experiment in hours
            PUE (1.58 by default)
        """
        from experiment_impact_tracker.data_interface import DataInterface
        
        results = {
            "tool_energy_consumption(kWh)":[],
            "tool_carbon_emissions(kgC02eq)":[],
            "tool_duration(seconds)":[],
            "tool_PUE":[]
        }
        for dir in self.log_dirs:
            data_interface = DataInterface([dir])
            results["tool_energy_consumption(kWh)"].append(data_interface.total_power)
            results["tool_carbon_emissions(kgC02eq)"].append(data_interface.kg_carbon)
            results["tool_duration(seconds)"].append(data_interface.exp_len_hours*3600)
            results["tool_PUE"].append(data_interface.PUE)
        return results


class CarbonTrackerTool(PowerTool):
    def __init__(
        self, 
        result_dir: str, 
        ) -> None:
        super().__init__(result_dir, "carbon_tracker")
        self.result_dir = self.result_dir+"/carbontracker/"
        
    def start_tool(self, scripts, sleep_before, sleep_after, nb_workers, bench_id, script_fct):
        logging.info("Starting the execution of carbontracker.")
        
        from carbontracker.tracker import CarbonTracker
        
        carbontracker_tracker = CarbonTracker(
            epochs=1,
            log_dir=self.result_dir,
            verbose=2,
            monitor_epochs=-1,
        )

        time.sleep(sleep_before)
        carbontracker_tracker.epoch_start()
        
        args = scripts, nb_workers
        output = script_fct(args)
            
        carbontracker_tracker.epoch_end()
        time.sleep(sleep_after)
        carbontracker_tracker.stop()
        
        logging.info("Execution of carbontracker DONE")
        return output
    
    def process_power_results(self) -> dict:
        """Fetches the carbontracker results from the log files.

        TODO : add epochs=last_log['actual']['epochs'] ?

        returns
            carbon emissions in g
            energy in kWh
            duration of experiment in seconds
            dict of details for each component
        """
        from utils.carbontracker_parser import parse_all_logs
        
        logs = parse_all_logs(log_dir=self.result_dir)
        results = {
            "tool_energy_consumption(kWh)":[],
            "tool_carbon_emissions(kgC02eq)":[],
            "tool_duration(seconds)":[],
            "tool_components":[]
        }
        for log in logs:
            results["tool_energy_consumption(kWh)"].append(log['actual']['energy (kWh)'])
            results["tool_carbon_emissions(kgC02eq)"].append(log['actual']['co2eq (g)'])
            results["tool_duration(seconds)"].append(log['actual']['duration (s)'])
            results["tool_components"].append(log['components'])
        return results
    

class CodeCarbon(PowerTool):
    """Implementation of PowerTool for Code Carbon."""
    def __init__(
        self, 
        result_dir: str, 
        ) -> None:
        super().__init__(result_dir, "codecarbon")
        #self.benchmark_test_id=[]

    def start_tool(self, scripts, sleep_before, sleep_after, nb_workers, bench_id, script_fct):
        from codecarbon import EmissionsTracker

        logging.info("Starting the execution of codecarbon.")
        
        #self.benchmark_test_id.append(bench_id[0])
        codecarbon_tracker = EmissionsTracker(
            project_name=bench_id[0],
            output_dir=self.result_dir, 
            save_to_file=self.result_dir+"emissions.csv"
            )
        
        time.sleep(sleep_before)
        
        codecarbon_tracker.start()
        args = scripts, nb_workers
        output = script_fct(args)
        codecarbon_tracker.stop()
        
        time.sleep(sleep_after)
        logging.info("Execution of codecarbon DONE")
        return output

    def process_power_results(self):
        df = pd.read_csv(self.result_dir+'emissions.csv')
        df['timestamp'] = df['timestamp'].apply(lambda row: time.mktime(datetime.datetime.strptime(row, "%Y-%m-%dT%H:%M:%S").timetuple()))
        renaming_dict = {
            "energy_consumed":"energy_consumption(kWh)",
            "emissions":"carbon_emissions(kgC02eq)",
            "duration":"duration(seconds)",
            "timestamp":"timestamp(seconds)",
            }
        df = df.rename(columns=renaming_dict)
        df = df.rename(columns={col:"tool_"+col for col in df.columns})
        df['tool_csv_file']=self.result_dir+"emissions.csv"
        return df.to_dict('list')

        
class EnergyScope(PowerTool):
    """Implementation of PowerTool for Energy Scope."""
    def __init__(
        self, 
        result_dir: str, 
        source_dir: str,
        job_id: str,
        launch_parallel_script: str,
        ) -> None: 
        super().__init__(result_dir, "energy scope")
        self.source_dir = source_dir
        self.job_id = job_id
        self.result_dir = result_dir
        self.es_execution_command = self.source_dir+"/energy_scope_mypc.sh"
        self.es_analysis_command = self.source_dir+"/energy_scope_run_analysis_allgo.sh"
        self.launch_parallel_script = launch_parallel_script
        os.popen("chmod 777 '{}'".format(self.launch_parallel_script))
        
    def generate_command_parallel_script(self, parallel_benchmarks):
        command = self.launch_parallel_script
        chmods = []
        for bench in parallel_benchmarks:
            command = command + " {}".format(bench.binary_path)
            chmods.append("chmod 777 {}".format(bench.binary_path))
        return command, chmods
    
    def concatenate_scripts(self, scripts, to_add) -> str:
        full_script = "\n".join(to_add)+"\n"
        for script in scripts:
            with open(script, "r") as f:
                full_script = "".join([full_script, f.read()+"\n"])
                
        final_script = "/".join(scripts[0].split("/")[:-1])+"/script_final.sh"
        with open(final_script, "x") as script:
            script.write(full_script)
        os.popen("chmod 777 {}".format(final_script))
        logging.info("Command to execute: "+final_script)
        return final_script
    
    def process_inputs(self) -> Tuple[str, str]:
        prefix_src = "ENERGY_SCOPE_SRC_DIR=" + self.source_dir
        prefix_traces = "ENERGY_SCOPE_TRACES_PATH=" + self.result_dir
        return prefix_src, prefix_traces
        
    def launch_experiments(self, benchmark_list, _) -> str:
        
        loop_size = len(benchmark_list[0])
        scripts = []
        for bench_order in range(loop_size):
            bench_in_parallel = [gpu_bench[bench_order] for gpu_bench in benchmark_list]
            command, chmods = self.generate_command_parallel_script(bench_in_parallel)
            benchmark_list[0][bench_order].generate_script(script_path=command)
            script = benchmark_list[0][bench_order].execution_script_path
            os.popen("chmod 777 {}".format(script))
            scripts.append(script) 
        logging.info(scripts)
        bash_command_to_execute = self.concatenate_scripts(scripts, chmods)
        prefix_src, prefix_traces = self.process_inputs()
        es_command = "{} {} {} {}".format(
            prefix_src, 
            prefix_traces, 
            self.es_execution_command, 
            bash_command_to_execute
        )
        logging.info("Starting the execution of energy scope: "+es_command)
        stream = os.popen(es_command)
        output = stream.read()
        logging.info("Execution of energy scope DONE")
        return self.process_stdout(output), output
    
    def analyse_trace(self) -> None:
        logging.info("trace analysis")
        logging.info(os.listdir(self.result_dir))
        self.trace_tar_file = glob.glob(self.result_dir + "energy_scope_*.tar.gz")[-1]
        self.es_trace_id = self.trace_tar_file.split('.')[0].split('_')[-1]
        logging.info("Energy scope trace id")
        logging.info(self.es_trace_id)
        command = "{} {}".format(self.es_analysis_command, self.trace_tar_file)
        logging.info("Starting the analysis of "+self.trace_tar_file)
        stream = os.popen(command)
        output = stream.read()
        logging.info("Energy scope analysis output: \n")
        logging.info(output)
        logging.info("Analysis DONE")
        
    def process_eprofile(self) -> pd.DataFrame():
        logging.info("eprofile analysis")
        logging.info(os.listdir(self.result_dir + "tmp_energy_scope_{}/".format(self.es_trace_id)))
        self.trace_eprofile = self.result_dir + "tmp_energy_scope_{}/energy_scope_eprofile_{}.txt".format(self.es_trace_id, self.es_trace_id)
        with open(self.trace_eprofile) as f:
            norm_df = pd.json_normalize(json.load(f))
        return norm_df

    def process_power_results(self):
        """Returns whatever power information given by tool"""
        self.analyse_trace()
        energy_df = self.process_eprofile()
        watt_cols = [col for col in energy_df.columns if '(W)' in col]
        watt_df = pd.DataFrame()
        for col in energy_df[watt_cols]:
            watt_df[col] = energy_df[col][0]
        path_csv_param = self.result_dir+'energy_scope_parameters.csv'
        energy_df.to_csv(path_csv_param, index=False) 
        path_csv = self.result_dir+'energy_scope.csv'
        watt_df.to_csv(path_csv, index=False) 
        energy = convert_energy_joule_in_kWh(energy_df["data.data.tags.es_appli_total.joule(J)"].values[0])
        results = {
            "tool_csv_file":path_csv, 
            "tool_parameters":path_csv_param, 
            "tool_energy_consumption(kWh)":energy
            }
        return results
