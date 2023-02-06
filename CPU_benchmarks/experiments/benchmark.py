import re
from time import sleep

from utils import *

# Benchmarks class
class Benchmark:
    def __init__(self,
                 name,
                 bench_type,
                 bin_info,
                 sleep_before,
                 sleep_after,
                 frequency,
                 threads):
        self.name = name
        self.bench_type = bench_type
        self.bin_info = bin_info
        self.sleep_before = sleep_before
        self.sleep_after = sleep_after
        self.frequency = frequency
        self.threads = threads
        self.start_time = None
        self.end_time = None
        self.stdout = None
    
    def run(self, user, host):
        # Select launch script depending on benchmark type
        if self.bench_type == "parallel":
            launch_script = "launch_parallel.sh"
        else:
            launch_script = "launch.sh"
            
        # Constructing command
        path = "/tmp"
        command = path + "/compare-software-power-meters/scripts/" + launch_script
        
        # If benchmark type is not parallel bin info contain one prefix and binfile
        if self.bench_type == "parallel":
            # If benchmark is parallel bin info will contain a list of binaries and prefixes
            for bin_info_entry in self.bin_info:
                command += " '" + bin_info_entry["prefix"] + " " + path + "/compare-software-power-meters/benchmarks/" + bin_info_entry["bin_file"] + "'"
        elif self.bench_type == "energyscope":
            command = self.bin_info["prefix"] + " "
            command += path + "/compare-software-power-meters/scripts/" + launch_script
            command += " '" + path + "/compare-software-power-meters/benchmarks/" + self.bin_info["bin_file"] + "'"
        else:
            command += " '" + self.bin_info["prefix"] + " " + path + "/compare-software-power-meters/benchmarks/" + self.bin_info["bin_file"] + "'"
        print("Starting benchmark %s..." % self.name)
        print("Benchmark command is '%s'" % command)
        
        print("Sleeping for %s seconds before benchmark..." % self.sleep_before)
        sleep(self.sleep_before)

        # Executing benchmark
        self.stdout = ssh_exec_command(user, host, command)

        self.parse_stdout()

        print("Benchmark started at: %s" % self.start_time)
        print("Benchmark ended at: %s" % self.end_time)

        print("Printing stdout:")
        print(self.stdout)

        print("Sleeping for %s seconds after benchmark..." % self.sleep_after)
        sleep(self.sleep_after)
          
    def parse_stdout(self):
        # Parse stdout to get start and end time of benchmark
        start_pattern = re.compile("^Start\ time\ (.*)$")
        end_pattern = re.compile("^End\ time\ (.*)$")
    
        for line in self.stdout:
            start_match = start_pattern.match(line)
            end_match = end_pattern.match(line)
            if start_match and len(start_match.groups()) > 0:
                self.start_time = start_match.group(1)
            if end_match and len(end_match.groups()) > 0:
                self.end_time = end_match.group(1)
