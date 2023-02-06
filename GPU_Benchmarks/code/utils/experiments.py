"""To start the experiments and save its metadata, including system description and wattmeter data.

The System class gathers system information. It also contains a method to create a log directory
    automatically unique to each experiment.
The Benchmark class can be used to automatically generate scripts executing bencharks.
The Experiment class collects necessary metadata, start the experiment and saves its results.

Typical use:
- Example in start_exp.py
- Simpler example, to start the application EP A on a single GPU and monitoring it with Energy Scope:

```
from experiments import System, Benchmark, Experiment
from tools import EnergyScope

# Variables
binary_dir = "NAS_benchmark_binaries/"
execution_script_template = "code/templates/script_template.sh"
experiments_dir="results/"

# Initialisation
current_system = System()
log_dir, exp_id = current_system.create_log_dir(experiments_dir)
script_dir = log_dir + "scripts/"

# Create benchmark object
benchmark = Benchmark(
    benchmark_id = exp_id,
    gpu_id = 0,
    name = "NAS",
    binary_dir = binary_dir,
    appli='EP',
    appli_class='A',
    sleep_before = 30,
    sleep_after = 30,
    execution_script_template = execution_script_template,
    execution_script_path = script_dir,
)

# Create tool object
tool_instance = EnergyScope(log_dir)

# Create the experiment object
current_exp = Experiment(
    experiments_table=experiments_dir+"experiment_table.csv",
    tool=tool_instance, 
    benchmarks=[[benchmark]],
    system=current_system,
    tool_on_one_process=tool_on_one_process,
)

# Start the experiment
current_exp.start()

# Process results
current_exp.retrieve_wattmeter_values() #to do afterwards
current_exp.process_power_tool_results()
current_exp.save_experiment_results()
```
"""
import cpuinfo
import getpass
import logging
import os
import psutil
import random
import re
from requests import auth
import time
from typing import Tuple

import pandas as pd

from utils.tools import PowerTool, Wattmeter, merge_dict_with_identical_keys


class System:
    """Retrieves system information.

    Description of the system is necessary to conduct reproducible experiments.
    This class contains methods to automatically retrieve needed information.
    It also contains the create_log_dir() method which creates a folder for
    each new experiment.

    Attributes:
        job_id: A string corresponding the g5k job id 
        exp_id: A string corresponding the experiment id
        host_name: A string corresponding the g5k host name 
        site: A string corresponding the g5k site
        node: A string corresponding the g5k node
        gpu_name: A string corresponding the model of the GPU used
        gpu_count: An integer correspodning the number of GPU used
        cpu_name: A string corresponding the model of the CPU used
        cpu_count: An integer corresponding the total number of virtual cores 
        cpu_phyical_core_count: An integer corresponding the total 
            number of physical cores 
    """
    def __init__(self) -> None:
        self.job_id = self.retrieve_g5k_job_id()
        self.exp_id = self.job_id
        self.host_name = self.retrieve_host_name()
        self.site, self.node = self.retrieve_site_node()
        if "\n" in self.node:
            self.node = self.node[:-1]
        self.gpu_name = self.retrieve_gpu_name()
        self.gpu_count = self.retrieve_gpu_count()
        self.cpu_name = self.retrieve_cpu_name()
        self.cpu_count = self.retrieve_cpu_count()
        self.cpu_phyical_core_count = self.retrieve_cpu_count(virtual = False)
        #self.g5k_auth = self.get_g5k_auth()

    def get_g5k_auth(self):
        """The credentials are asked at every execution to avoid saving them."""
        user = getpass.getpass(prompt='Grid5000 login:')
        password = getpass.getpass(prompt='Grid5000 password:')
        return auth.HTTPBasicAuth(user, password)

    def retrieve_g5k_job_id(self) -> str:
        name = "OAR_JOB_ID"
        if name in os.environ:
            return os.environ.get(name)
        else:
            return str(random.randint(0,1000))

    def retrieve_gpu_name(self) -> str:
        nvsmi_res = os.popen("nvidia-smi --query-gpu=gpu_name --format=csv").read()
        match = re.search(r'\n(.*?)\n', nvsmi_res)
        if match:
            gpu_name = match.group(1)
            logging.info(gpu_name)
            return gpu_name
        
    def retrieve_gpu_count(self) -> str:
        nvsmi_res = os.popen("nvidia-smi --query-gpu=count --format=csv").read()
        match = re.search(r'\n(.*?)\n', nvsmi_res)
        if match:
            gpu_name = match.group(1)
            logging.info(gpu_name)
            return gpu_name
        
    def retrieve_cpu_name(self) -> str:
        return cpuinfo.get_cpu_info()['brand_raw']
        
    def retrieve_cpu_count(self, virtual=True) -> str:
        return psutil.cpu_count(logical=virtual)

    def retrieve_host_name(self) -> str:
        return os.popen("hostname").read()

    def retrieve_site_node(self) -> Tuple[str, str]:
        """
        hostname is of the form "chifflet-6.lille.grid5000.fr"
        """
        if "grid5000" in self.host_name:
            node, site, _, _ = self.host_name.split(".")
            return site, node
        elif "chifflet" in self.host_name:
            return "lille", self.host_name
        elif "gemini" in self.host_name:
            return "lyon", self.host_name
        else:
            return "no_site", "no_host"
    
    def create_log_dir(self, result_dir: str) -> Tuple[str, str]:
        """Creates directory for logs.

        Gemini takes almost 5 minutes to reboot after an experiment.
        To avoid waiting after experiments, I use an interative session. 
        But this means that the g5k job id can't be the primary key for the experiment. 
        This function creates an experiment id of the format "<g5k job id>_<digit>".

        Args
            result_dir: str. User given directory to save all results in.
        
        Returns
            log_dir: str. result_dir + exp_id + "/"
            exp_id: str. Experiment id.
        """
        i=0
        exp_id = self.job_id + "_" + str(i)
        log_dir = result_dir+exp_id+"/"
        while os.path.isdir(log_dir):
            i += 1
            exp_id = self.job_id + "_" + str(i)
            log_dir = result_dir+exp_id+"/"
        os.mkdir(log_dir)
        self.exp_id = exp_id
        return log_dir, exp_id


class Benchmark:
    """Describes a benchmark to be launched within one experiment.

    Benchmarks are defined by an application (EP, LU or MG) and a class (A to E).
    The generate_script method creates a shell script in execution_script_path 
        which needs to be provided to the tool object. 
    A script template (execution_script_path) must be provided so that the only action to 
        do is add the application, the class, the gpu on which the benchmark will be 
        executed and the sleep durations.
    Sleeps are added before and after the benchmark is launched to make
        sure the machine is idle.
    Timestamps are echoed when the benchmark starts and ends to be able to cut
        the power time series.

    Attributes:
        benchmark_id: str. The benchmark id.
        gpu_id: int. The gpu device number on which the benchmark will be executed.
        name: A string corresponding to the name of the benchmark. 
            For example, "NAS".
        binary_dir: A string corresponding to the directory where the binaries are. 
        appli: str. The benchmark application. For example, "ep".
        appli_class: str. The benchmark application class. For example, "A".
        sleep_before: int (seconds). Time to wait before starting the benchmark.
        sleep_after: int (seconds). Time to wait after the benchmark ended.
        execution_script_template: A string of the path to the template to use.
        execution_script_path: A string of the path to save the execution script at.
    """
    def __init__(
        self,
        benchmark_id: str,
        gpu_id: int,
        name: str,
        binary_dir: str,
        appli: str,
        appli_class: str,
        sleep_before: int,
        sleep_after: int,
        execution_script_template: str,
        execution_script_path: str,
        ) -> None:
        self.benchmark_id = benchmark_id
        self.gpu_id = gpu_id
        self.name = name
        self.binary_dir = binary_dir
        self.appli = appli
        self.appli_class = appli_class
        self.sleep_before = sleep_before
        self.sleep_after = sleep_after
        self.execution_script_template = execution_script_template
        self.execution_script_path = execution_script_path
        self.binary_path = binary_dir + "{}.{}".format(appli, appli_class)
        logging.info("doing the chmod of "+self.binary_path)
        os.popen("chmod 777 {}".format(self.binary_path))

    def generate_script(self, with_sleep=True, script_path=None) -> None:
        if script_path is None:
            script_path = self.binary_path
        with open(self.execution_script_template, "r") as template:
            template_lines = template.readlines()
        for i in range(len(template_lines)):
            if template_lines[i]=="benchmark_binary_path=\n":
                template_lines[i]='benchmark_binary_path="{}"\n'.format(script_path)
            if template_lines[i]=="sleep_before=\n":
                template_lines[i]='sleep_before={}\n'.format(
                    self.sleep_before if with_sleep else 0)
            if template_lines[i]=="sleep_after=\n":
                template_lines[i]='sleep_after={}\n'.format(
                    self.sleep_after if with_sleep else 0)
            if template_lines[i]=="gpu_number=\n":
                template_lines[i]='gpu_number={}\n'.format(
                    self.gpu_id)
        execution_script="".join(template_lines)
        with open(self.execution_script_path, "w") as script:
            script.write(execution_script)
        os.popen("chmod 777 '{}'".format(self.execution_script_path))
                

class Experiment:
    """Describes one experiment.

    One experiment correspond to the benchmarking of one software wattmeter. 
    It usually includes several benchmark applications with sleeps inbetween.
    The class contains the methods to start an experiment, process and save the tool
    results and retrieve the corresponding wattmeter values.

    The variable results doesn't include time series or dataframe, only the path 
        where to store/find them.

    Attributes:
        experiments_table: str. Path to table (csv file) where all experiments
            are described.
        tool: A PowerTool object.
        system: System object containing system information 
            like the number of GPU. 
        benchmarks: 
            List of lists of Benchmark objects.
            first size is the number of workers.
            second size is the number of experiments.
        results: dict of results.
    """
    def __init__(
        self,
        experiments_table: str,
        tool: PowerTool,
        benchmarks,  #List[Benchmark]
        system: System,
        tool_on_one_process,
    ) -> None:
        self.experiments_table = experiments_table
        self.tool = tool
        self.result_dir = tool.result_dir
        self.benchmarks = benchmarks
        self.system = system
        self.results = {}
        self.tool_on_one_process = tool_on_one_process
        self.results["tool_on_one_process"]=self.tool_on_one_process
         
    def start(self):
        logging.info("Starting execution of experiment {}".format(self.system.exp_id))
        exp_start = time.time()
        bench_timestamps, output = self.tool.launch_experiments(
            self.benchmarks,
            self.tool_on_one_process,
        )
        exp_end = time.time()
        logging.info("Ending execution of experiment {}".format(self.system.exp_id))
        exp_timestamps = {"experiment_start": exp_start, "experiment_end": exp_end}
        self.results.update(exp_timestamps)
        self.results.update(bench_timestamps)

    def process_power_tool_results(self):
        """Processes the results and add them to the results dict.

        The exception is needed to be able to save the error and
            make sure the following benchmarks can be conducted
            as planned.
        """
        try:
            results = self.tool.process_power_results()
            logging.debug(results)
            self.results.update(results)
        except Exception as err:
            logging.error(err)
            self.results['error']=err
            logging.error("Continuing so the experience can be saved.")

    def retrieve_wattmeter_values(self):
        """Retrieves the wattmeter data and saves them to the results dict.
        """
        wattmeter_data = Wattmeter(
            self.system.node, 
            self.system.site, 
            self.results["experiment_start"], 
            self.results["experiment_end"],
            self.system.g5k_auth,
        )
        wattmeter_data.save_power(self.tool.result_dir)
        for metric in wattmeter_data.metrics:
            self.results[metric+'_energy_consumption(kWh)'] = wattmeter_data.results[metric]['energy_kWh']
            self.results[metric+'_csv_file'] = wattmeter_data.results[metric]['csv_file']

    def save_experiment_results(self):
        """Saves results of the experiment."""
        logging.info("Starting processing results.")
        
        self.results.update(self.tool.__dict__)
        
        # Processing the benchmark object
        for worker_id, gpu_benchmarks in enumerate(self.benchmarks):
            column_start = "gpu_{}_".format(worker_id)
            identical_key_dicts = []
            for _, bench_test in enumerate(gpu_benchmarks):
                bench_attr_dict = bench_test.__dict__
                old_keys = bench_attr_dict.keys()
                for key in old_keys:
                    if column_start not in key:
                        bench_attr_dict[column_start+key] = bench_attr_dict.pop(key)
                identical_key_dicts.append(bench_attr_dict)
            
            self.results.update(merge_dict_with_identical_keys(identical_key_dicts))
        
        self.results.update(self.system.__dict__)

        logging.info("Experiment info: \n")
        
        for key in self.results.keys():
            val = self.results[key]
            logging.info("{} : {}".format(key, len(val) if type(val) is list else val))
        
        # add experiment to existing results
        if os.path.exists(self.experiments_table):
            logging.info('Result file already created, appending results.')
            exp_df = pd.read_csv(self.experiments_table)
            exp_df = pd.concat([exp_df, pd.DataFrame(self.results)], ignore_index=True)
        else:
            logging.info('Creating result file at '+self.experiments_table)
            exp_df = pd.DataFrame(self.results)
            
        exp_df.to_csv(self.experiments_table, index=False)
        logging.info("Result df saved.")
        
        return exp_df
    
    
          
            
