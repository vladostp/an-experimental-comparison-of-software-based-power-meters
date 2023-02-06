import re
import pandas as pd
import subprocess
import json
import datetime

from utils import *
from solution import Solution

# Energyscope Class
class EnergyScope(Solution):
    def __init__(self, experiments):
        self.name = 'energyscope'
        self.experiments = experiments

    def analyze_energy_scope(self, jobid):
        # Analyze aquisition file
        anaylze_command_prefix = "ENERGY_SCOPE_SRC_DIR=/tmp/compare-software-power-meters/energy_scope ENERGY_SCOPE_TRACES_PATH=/tmp/compare-software-power-meters/energy_scope/results"
        analyze_commad = "%s /tmp/compare-software-power-meters/energy_scope/energy_scope_run_analysis_allgo.sh /tmp/compare-software-power-meters/energy_scope/results/energy_scope_%s.tar.gz" % (anaylze_command_prefix, jobid)
        analyze_result =  ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, analyze_commad)

        # Get destination user
        dest_user = subprocess.run(['id','-u','-n'], capture_output=True, text=True).stdout.rstrip("\n")

        # Copy aquisition result file
        result_file_path = "/tmp/compare-software-power-meters/energy_scope/results/tmp_energy_scope_%s/energy_scope_eprofile_%s.txt" % (jobid, jobid)
        
        dest_path = "/tmp/"
        copy_file = scp_copy_file(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, result_file_path, dest_path)

        # Retrieve and send content of eprofile file
        result_file = "/tmp/energy_scope_eprofile_%s.txt" % jobid
        file = open(result_file, "r")
        
        # Creating a pandas array from json and closing file
        file_pd = pd.json_normalize(json.load(file))
        file.close()
        
        # Removing eprofile file
        #remove_file_command = "rm -f /home/%s/compare-software-power-meters/energy_scope/results/energy_scope_eprofile_%s.txt" % (dest_user, jobid)
        #remove_file_result = subprocess.run(remove_file_command.split(" "), capture_output=True, text=True)
        #print(remove_file_result.stdout)

        return file_pd
    
    def create_plottable_dataframe_from_energy_scope(self, ec_array_dataframes):
        # Creating a dataframe with estimation result
        time_df = pd.DataFrame()

        for ec_dataframe in ec_array_dataframes:
            temp_df = pd.DataFrame()
            # Copy only energy columns to dataframe
            cols = list(ec_dataframe.columns)
            energy_cols = [x for x in cols if 'temp' not in x and 'W' in x]
            for col in ec_dataframe[energy_cols]:
                if len(ec_dataframe[col]) > 0:
                    temp_df[col] = ec_dataframe[col][0]

            # Get estimation start time
            start_column_time = [x for x in cols if 'es_total.start' in x and 'sec' not in x]
            # Convert to time into milliseconds
            utc_time = datetime.datetime.strptime(ec_dataframe[start_column_time].values[0][0], "%Y/%m/%d %H:%M:%S.%f")
            milliseconds_time = round(utc_time.timestamp() * 1000)

            # Get information about estimation period
            period_column = [x for x in cols if 'period' in x]
            period = ec_dataframe[period_column].values[0][0]

            # Calculate timestamp for each estimation value from start time and period of estimations
            temp_df['timestamp'] = temp_df.index * period + milliseconds_time
            temp_df['timestamp'] = pd.to_datetime(temp_df['timestamp'], unit='ms', origin='unix')
            temp_df['jobid'] = ec_dataframe['from_appli.jobid'][0]
            temp_df['command'] = ec_dataframe['from_appli.command'][0].split('/')[-1]

            time_df = pd.concat([time_df, temp_df])

        return time_df

    def get_consumption(self, experiment):
        pattern = re.compile("^jobid.* ([0-9]+)$")
        array_of_df = []
        for benchmark in experiment.benchmarks:
            # Get jobid from benchmark stdout
            for line in benchmark.stdout:
                match = pattern.match(line)
                if match and len(match.groups()) > 0:
                    jobid = match.group(1)
                    # If jobid is found we will create a Dataframe
                    if jobid:
                        eprofile_pd = self.analyze_energy_scope(jobid)
                        array_of_df.append(eprofile_pd)
        return self.create_plottable_dataframe_from_energy_scope(array_of_df)

    def get_acquisition_frequency(self):
        get_eprofile_period_cmd = 'cat /tmp/compare-software-power-meters/energy_scope/es_config.json | jq \'.parameter["eprofile_period(ms)"]\''
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, get_eprofile_period_cmd)
        eprofile_period = result[0].strip()
    
        get_read_rt_idle_time_cmd = 'cat /tmp/compare-software-power-meters/energy_scope/es_config.json | jq ".data.intel.generic.read_rt_idle_time"'
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, get_read_rt_idle_time_cmd)
        read_rt_idle_time = result[0].strip()
        
        return {
            'eprofile_period': eprofile_period,
            'read_rt_idle_time': read_rt_idle_time
        }

    def set_acquisition_frequency(self, eprofile_period, read_rt_idle_time=0):
        read_rt_idle_time = round(int(eprofile_period) / 1000 - 0.01, 3)
        change_eprofile_and_rt_time_cmd = 'cat <<< $(jq \'.parameter["eprofile_period(ms)"] = ' + str(eprofile_period) + ' | .data.intel.generic.read_rt_idle_time = ' + str(read_rt_idle_time) + '\' /tmp/compare-software-power-meters/energy_scope/es_config.json) > /tmp/compare-software-power-meters/energy_scope/es_config.json'
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, change_eprofile_and_rt_time_cmd)
        print(result)
        
    def clean_results_dir(self):
        clean_results_dir_cmd = "rm -rf /tmp/compare-software-power-meters/energy_scope/results/*"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, clean_results_dir_cmd)
        print(result)
        
    def clean_bench_host(self):
        print('Cleaning results dir for energy scope.')
        self.clean_results_dir()

    def clean_after_experiment(self):
        self.clean_results_dir()