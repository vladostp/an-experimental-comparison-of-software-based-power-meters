import datetime
import copy
import json

from benchmark import Benchmark

# Experiment class
class Experiment:
    def __init__(self,
                 name):
        self.name = name
        self.benchmarks = []
        self.results = []
        self.start_time = None
        self.end_time = None
        
    def add_benchmark_from_template(self, template):
        benchmark_instance = Benchmark(**template)
        self.benchmarks.append(benchmark_instance)
        
    # Extract binaries from benchmarks
    def get_binaries_from_benchmarks(self):
        bins = []
        for benchmark in self.benchmarks:
            if benchmark.bench_type == "parallel":
                for one_bin_info in benchmark.bin_info:
                    bins.append(one_bin_info['bin_file'])
            else:
                bins.append(benchmark.bin_info['bin_file'])
        return list(set(bins))
        
    def generate_benchmarks(self, template, frequencies="", threads="", replace=True):
        # If no threads and frequencies given adding template as benchmarks
        if threads == "" and frequencies == "":
            print('No threads and frequencies given so adding template...')
            benchmarks = template
        else:
            # Generate benchmarks for different frequency or threads number
            benchmarks = []

            for benchmark in template:
                if threads != "" and benchmark["bench_type"] == 'simple':
                    for thread in threads.split(","):
                        benchmark_new = copy.deepcopy(benchmark)
                        benchmark_new["threads"] = thread
                        benchmark_new["bin_info"]["prefix"] = benchmark["bin_info"]["prefix"][:4] + ' OMP_NUM_THREADS=' + thread + benchmark["bin_info"]["prefix"][4:]
                        benchmark_new["name"] = benchmark["name"] + " " + thread + " threads"
                        benchmarks.append(benchmark_new)
                elif frequencies != "":
                    for frequency in frequencies.split(","):
                        benchmark_new = copy.deepcopy(benchmark)
                        benchmark_new["frequency"] = frequency
                        benchmark_new["name"] = benchmark["name"] + " at " + frequency
                        benchmarks.append(benchmark_new)
                else:
                    benchmarks.append(benchmark)

            print("Generated %d benchmarks" % len(benchmarks))
            print(json.dumps(benchmarks[0], indent=4))
            print("........")
            print(json.dumps(benchmarks[len(benchmarks)-1], indent=4))
            print("Adding benchmarks to experiment...")
        
        # Creating benchmark instances and adding them to experiment
        benchmark_instances = []
        
        for benchmark in benchmarks:
            bench_instance = Benchmark(**benchmark)
            benchmark_instances.append(bench_instance)
            
        if replace:
            print("Replacing benchmarks by generated benchmarks in experiment...")
            self.benchmarks = benchmark_instances
        else: 
            return benchmark_instances
        
        
    def add_result(self, name, dataframe):
        result_dict = {'source': name, 'dataframe': dataframe}
        # Searching for result in experiment
        found_result = next((result for result in self.results if result['source'] == name), None)
        # If result is already present we will reamplce it
        if found_result:
            get_index_of_found = self.results.index(found_result)
            self.results[get_index_of_found] = result_dict
        else:
            self.results.append(result_dict)  
        
    def set_start_time_to_now(self):
        self.start_time = datetime.datetime.now(datetime.timezone.utc)

    def set_end_time_to_now(self):
        self.end_time = datetime.datetime.now(datetime.timezone.utc)
