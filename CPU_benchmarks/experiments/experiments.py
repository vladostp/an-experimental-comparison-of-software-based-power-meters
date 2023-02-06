import json
import re
import subprocess
import os
import copy
import pytz
import datetime

from utils import *

# Refers all experiments in a notebook
class Experiments:
    def __init__(self, name):
        self.name = name
        self.jobs = {}
        self.gpu = None
        self.cpu = None
        self.solutions = []
        self.experiments = []
       
    def add_job(self, job, job_role):
        self.jobs[job_role] = job
        
    def add_solution(self, solution):
        self.solutions.append(solution)
        
    def add_experiment(self, experiment):
        # Searching for experiment with the same name
        found_experiment = next((exp for exp in self.experiments if exp.name == experiment.name), None)
        # If experiment is already present we will replace it
        if found_experiment:
            get_index_of_found = self.experiments.index(found_experiment)
            self.experiments[get_index_of_found] = experiment
        else:
            self.experiments.append(experiment)  
        
    # Get frequency info from cpupower
    def get_cpu_frequency_info(self):
        get_frequency_info_command = "sudo cpupower frequency-info | grep 'current CPU.*kernel' | sed -E 's/.*\ ([0-9]+.*)\ \(.*/\\1/g'"
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, get_frequency_info_command)
        print(result)

    # Change maximum and minimum CPU frequency
    def change_cpu_frequency(self, frequency_min, frequency_max):
        # Changing min and max CPU frequency
        change_frequency_command = "sudo cpupower frequency-set -d %s && sudo cpupower frequency-set -u %s" % (frequency_min, frequency_max)
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, change_frequency_command)
        print(result)
        
    # Change CPU governor
    def change_cpu_governor(self, governor):
        # Changing min and max CPU frequency
        change_frequency_command = "sudo cpupower frequency-set -g %s" % governor
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, change_frequency_command)
        print(result)

    def set_turbo_boost(self, action):
        register_value = "0x4000850089" if action == "disable" else "0x850089"
        command = "sudo wrmsr -a 0x1a0 %s" % register_value
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, command)
        print("Turbo boost disable register was set to: %s" % register_value)
        print(result)
        
    def get_turbo_boost_state(self):
        command = "sudo rdmsr -a 0x1a0 -f 38:38"
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, command)
        return result       
        
    def set_cpu_smt(self, state):
        command = "echo %s > /sys/devices/system/cpu/smt/control" % state
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, command)
        print(result) 
    
    def get_cpu_smt_state(self):
        command = "cat /sys/devices/system/cpu/smt/control"
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, command)
        return result[0].rstrip('\n')
    
    def get_scaling_max_frequency(self, cpu):
        command = "cat /sys/devices/system/cpu/cpu%d/cpufreq/scaling_max_freq" % int(cpu)
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, command)
        return result[0].rstrip('\n')
        
    def disable_all_idle_states(self):
        command = "sudo cpupower idle-set -D 0"
        result = ssh_exec_command(self.jobs["bench"].user,  self.jobs["bench"].host, command)
        print(result)
    
    def run_experiment_benchmarks(self, experiment):
        print("Found total of %d benchmarks to execute..." % len(experiment.benchmarks))
        print("--------------------------------------------------------------")
        counter = 1
        for benchmark in experiment.benchmarks:
            print("--------------------------------------------------------------")
            print("Executing %d benchmark from %d..." % (counter, len(experiment.benchmarks)))
            if benchmark.frequency != 0:
                print("Detected frequency in benchmark description...")
                print("Changing host frequency to %s..." % benchmark.frequency)
                self.change_cpu_frequency(benchmark.frequency, benchmark.frequency)
                self.get_cpu_frequency_info()
            benchmark.run(self.jobs["bench"].user, self.jobs["bench"].host)
            print("--------------------------------------------------------------")
            counter+=1
            
    def prepare_bench_host(self):
        print("Starting bench host preparation...")
        
        # Check if bench job was added to experiment
        if 'bench' not in self.jobs:
            print("Bench job was not found.")
            return
        
        # Get host kernel version
        get_kernel_version = "uname -r"
        result = ssh_exec_command(self.jobs["bench"].user, self.jobs["bench"].host, get_kernel_version)
        kernel_version = result[0]
        
        print("Installing necessary packages...")
        packages_to_install = "libczmq-dev bc libsystemd-dev uuid-dev libasan5 ntpdate libubsan1 libbson-dev libmongoc-dev cgroup-tools jq libgomp1 libgfortran5 linux-tools-common msr-tools linux-tools-generic util-linux linux-tools-%s" % kernel_version
        print("Installing %s..." % packages_to_install)
        package_install_command = "sudo sh -c 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y %s'" % packages_to_install
        result = ssh_exec_command(self.jobs["bench"].user, self.jobs["bench"].host, package_install_command)
        
        print("Adding msr module to Kernel...")
        modprobe_msr_command = "sudo modprobe msr"
        result = ssh_exec_command(self.jobs["bench"].user, self.jobs["bench"].host, modprobe_msr_command)
        print(result)

        print("Disabling Hyper Threading...")
        self.set_cpu_smt("off")
        print(self.get_cpu_smt_state())
        
        print("Disabling Turbo Boost...")
        self.set_turbo_boost("disable")
        print(self.get_turbo_boost_state())
                               
        print("Disabling all Idle States (C-States)...")
        self.disable_all_idle_states()
        
        print("Changing CPU governor to performance...")
        self.change_cpu_governor("performance")
        
        print("Get scaling max frequency...")
        scaling_max_frequency = self.get_scaling_max_frequency(0)
        print("Scaling max frequency is equal to %s." % scaling_max_frequency)
        
        print("Setting CPU frequnecy to max frequnecy...")
        self.change_cpu_frequency(scaling_max_frequency, scaling_max_frequency)
        
        print("Synchronizing clock...")
        self.synch_clock("bench", "time.nist.gov")
            
        # Get current host user
        get_user_command = "id -u -n"
        process = subprocess.run(get_user_command, shell=True, check=True, text=True, stdout=subprocess.PIPE)
        user = process.stdout.rstrip("\n")
        print(user)

        print("Copying necessary experiment files to bench host...")
        create_directory = "sudo sh -c 'mkdir -p /tmp/compare-software-power-meters'"
        result = ssh_exec_command(self.jobs["bench"].user, self.jobs["bench"].host, create_directory)
        print(result)
        scp_put_dir(self.jobs["bench"].user, self.jobs["bench"].host, "../", '/tmp/compare-software-power-meters')
        
        # Preparing bench host for each solution
        for solution in self.solutions:
            solution.prepare_bench_host()
            
        print("Bench host preparation is finished...")
         
    def clean_bench_host(self):
        print("Starting bench host cleaning...")
        # Cleaning bench host for each solution
        for solution in self.solutions:
            solution.clean_bench_host() 
        print("Bench host cleaning is finished...")
        
    def synch_clock(self, node, ntp_server):
        sync_clock_command = "sudo service ntp stop ; sudo ntpdate -s %s ; sudo service ntp start" % ntp_server
        result = ssh_exec_command(self.jobs[node].user, self.jobs[node].host, sync_clock_command)
        print(result)

    def prepare_data_host(self):
        print("Starting data host preparation...")
        
        # Check if data job was added to experiment
        if 'data' not in self.jobs:
            print("Data job was not found.")
            return

        print("Installing necessary packages...")
        packages_to_install = "curl"
        print("Installing %s..." % packages_to_install)
        package_install_command = "sudo sh -c 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y %s'" % packages_to_install
        result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, package_install_command)
        
         # Check if docker is installed
        check_install_command = "docker --version"
        result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, check_install_command, False)
        print(result)
        
        if len(result) == 0:
            # Installing docker and docker compose to data host
            print('Installing docker...') 
            docker_install_cmd = "curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
            result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, docker_install_cmd, False)
            print(result)
            
         # Check if docker compose is installed
        check_install_command = "/tmp/docker-compose --version"
        result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, check_install_command, False)
        print(result) 
        
        if len(result) == 0:
            print('Downloading docker-compose and making it executable...')
            docker_compose_install_cmd = "curl -sS -L \"https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)\" -o /tmp/docker-compose"
            result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, docker_compose_install_cmd)
            print(result)

            docker_compose_chmod = "chmod +x /tmp/docker-compose"
            result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, docker_compose_chmod)
            print(result)
    
        # Check installation of Docker and Docker-compose
        check_install_command = "docker --version && /tmp/docker-compose --version"
        result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, check_install_command)
        print(result)

        if len(result) < 2 or "Docker version" not in result[0] or "docker-compose version" not in result[1]:
            raise Exception("Docker or Docker-compose was not installed.")
            
        # Install necessary packages
        print("Installing necessary packages...")
        packages_to_install = "ntpdate"
        print("Installing %s..." % packages_to_install)
        package_install_command = "sudo sh -c 'apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -q -y %s'" % packages_to_install
        result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, package_install_command)
        
        # Sunchronize clock
        print("Synchronizing clock...")
        self.synch_clock("data", "time.nist.gov")
        
        print("Copying necessary experiment files to data host...")
        create_directory = "mkdir -p /tmp/compare-software-power-meters"
        result = ssh_exec_command(self.jobs["data"].user, self.jobs["data"].host, create_directory)
        print(result)
        scp_put_dir(self.jobs["data"].user, self.jobs["data"].host, "../", '/tmp/compare-software-power-meters')
        
        # Preparing data host for each solution
        for solution in self.solutions:
            solution.prepare_data_host()

        print("Data host preparation is finished...")
        
    def clean_data_host(self):
        print("Starting data host cleaning...")
        # Cleaning data host for each solution
        for solution in self.solutions:
            solution.clean_data_host()
        print("Data host cleaning is finished...")
    
    # Add cpu information to experiments
    def add_cpu_info(self):
        print("Adding lscpu info to experiments...")
        command = "lscpu --json"
        result = ssh_exec_command(self.jobs["bench"].user, self.jobs["bench"].host, command)
        json_string = ''.join(result)
        lscpu = json.loads(json_string)
        # Saving only specific fields abount CPU
        fields_list = [
            'Architecture:',
            'CPU(s):',
            'Thread(s) per core:',
            'Core(s) per socket:',
            'Socket(s):',
            'Model name:'
        ]
        self.cpu = [d for d in lscpu['lscpu'] if d['field'] in fields_list]

    # Add gpu information to experiments
    def add_gpu_info(self):
        print("Adding gpu info to experiments...")
        command = "nvidia-smi --query-gpu=count,gpu_name --format=csv"
        result = ssh_exec_command(self.jobs["bench"].user, self.jobs["bench"].host, command, False)

        if result == None:
            return

        gpu_result_parse = re.search("\n([0-9]+),\ (.*)\n", "".join(result))
        if gpu_result_parse == None:
            return

        self.gpu = {
            "count": gpu_result_parse.group(1),
            "name": gpu_result_parse.group(2)
        }
        
    # Get number of CPU threads available    
    def get_threads_available(self):
        threads_per_core = 0
        cores_per_socket = 0
        sockets = 0
        
        for info in self.cpu:
            if info['field'] == 'Thread(s) per core:':
                threads_per_core = int(info['data'])
            if info['field'] == 'Core(s) per socket:':
                cores_per_socket = int(info['data'])
            if info['field'] == 'Socket(s):':
                sockets = int(info['data'])
                
        return threads_per_core*cores_per_socket*sockets

    def set_general_info(self):
        self.add_cpu_info()
        self.add_gpu_info()
        
    # Saving experiments function
    def save(self):
        prefix = self.name.lower().replace(" ", "-")
        
        # Create result directory 
        experiment_time = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d-%H_%M_%S")
        result_dir = "../results/%s-%s-%s" % (prefix, self.jobs["bench"].host, experiment_time)

        if not os.path.isdir(result_dir):
            print("Created directory %s to store result..." % result_dir)
            os.mkdir(result_dir)

        save_structure = {}
        
        # Saving jobs info
        save_structure["jobs"] = {}
        temp_jobs = copy.deepcopy(self.jobs)
        for temp_job in temp_jobs:
            delattr(temp_jobs[temp_job], 'g5k_job_instance')
            delattr(temp_jobs[temp_job], 'deployment')
            save_structure["jobs"][temp_job] = temp_jobs[temp_job].__dict__

        save_structure["cpu"] = self.cpu
        save_structure["gpu"] = self.gpu

        # Saving experiments
        save_experiments = []
        for experiment in self.experiments:
            experiment_json = {}
            experiment_json["name"] = experiment.name
            experiment_json["start_time"] = experiment.start_time.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            experiment_json["end_time"] = experiment.end_time.astimezone(pytz.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
            experiment_json["benchmarks"] = []
            for benchmark in experiment.benchmarks:
                experiment_json["benchmarks"].append(benchmark.__dict__)
            experiment_json["results"] = []
            # Every result will be written to a separate CSV file
            for consumption_data in experiment.results:
                filename = consumption_data["source"] + "_" + experiment_json["name"].lower() + ".csv"
                filepath = "%s/%s" % (result_dir, filename)
                print("Saving %s consumption data to %s file..." % (consumption_data["source"], filepath))
                consumption_data["dataframe"].to_csv(filepath)
                experiment_json["results"].append({'source': consumption_data["source"], 'file': filename})

            save_experiments.append(experiment_json)

        save_structure["experiments"] = save_experiments

        print("Saving experiments to %s/experiments.json file..." % result_dir)
        with open("%s/experiments.json" % result_dir, 'w') as outfile:
            json.dump(save_structure, outfile)
