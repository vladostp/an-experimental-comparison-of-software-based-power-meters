import pandas as pd
import datetime
import pytz

from utils import *
from solution import Solution

# Perf Class
class Perf(Solution):
    def __init__(self, experiments):
        self.name = 'perf'
        self.experiments = experiments

    def get_total_energy(self, experiment):
        result_df = pd.DataFrame(columns=['benchmark', 'tool', 'socket', 'event', 'value'])

        for benchmark in experiment.benchmarks:
            if benchmark.result_file:
                dest_path = "/tmp/"
                result_file_path = "/tmp/" + benchmark.result_file
                copy_result_file = scp_copy_file(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, result_file_path, dest_path)
                print(copy_result_file)
        
            # Creating a pandas dataframe from CSV file
            file_df = pd.read_csv(result_file_path, 
                                    sep = ':', 
                                    names = ['socket', 'value', 'unit', 'event','nothing1','nothing2','nothing3','nothing4'], 
                                    comment = '#')

            file_df['tool'] = 'perf'
            file_df['benchmark'] = benchmark.name
            file_df = file_df.drop(columns=['unit', 'nothing1', 'nothing2', 'nothing3', 'nothing4'])
            result_df = pd.concat([result_df, file_df], ignore_index=True)
           
        return result_df

    def get_consumption_profile(self, experiment):
        result_df = pd.DataFrame(columns=['timestamp', 'benchmark', 'tool', 'socket', 'event', 'value_joules', 'interval', 'value'])

        for benchmark in experiment.benchmarks:
            if benchmark.result_file:
                dest_path = "/tmp/"
                result_file_path = "/tmp/" + benchmark.result_file
                copy_result_file = scp_copy_file(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, result_file_path, dest_path)
                print(copy_result_file)
        
            # Creating a pandas dataframe from CSV file
            file_df = pd.read_csv(result_file_path, 
                                    sep = ':', 
                                    names = ['time', 'socket', 'value', 'unit', 'event','interval','nothing2','nothing3','nothing4'], 
                                    comment = '#')

            # Reading and parsing start date from the first line of CSV file
            with open(result_file_path) as f:
                execution_start = f.readline().strip('\n')
            
            start_time = datetime.datetime.strptime(execution_start, '# started on %a %b  %d %H:%M:%S %Y')

            # Changin timezone to UTC
            time_zone = self.get_timezone_info()
            start_time = pytz.timezone(time_zone).localize(start_time, is_dst=None)
            start_time = start_time.astimezone(pytz.utc)
            start_time = start_time.replace(tzinfo=None)
            
            file_df['tool'] = 'perf'

            # Converting time to timestamp
            file_df['time'] = pd.to_timedelta(file_df['time'], unit='s')
            file_df['timestamp'] = file_df['time'] + start_time

            file_df = file_df.rename(columns={"value": "value_joules"})
            file_df['benchmark'] = benchmark.name

            # Converting joules in watts by using interval data
            file_df['value'] = file_df['value_joules'] / (file_df['interval'] / 1000000000)

            file_df = file_df.drop(columns=['unit', 'time', 'nothing2', 'nothing3', 'nothing4'])
            result_df = pd.concat([result_df, file_df], ignore_index=True)

        return result_df

    def get_timezone_info(self):
        command = "cat /etc/timezone"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, command)
        return result[0].strip()