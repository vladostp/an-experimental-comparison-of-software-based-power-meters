import urllib.parse
import json
import pandas as pd

from utils import *
from solution import Solution

# Scaphandre Class
class Scaphandre(Solution):
    def __init__(self, experiments):
        self.name = 'scaphandre'
        self.experiments = experiments
        self.frequency = 5
    
    def start_scaphandre_data(self):
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, 'cd /tmp/compare-software-power-meters/scaphandre && /tmp/docker-compose up -d && docker ps', False)
        print(result)

    def stop_scaphandre_data(self):
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, 'cd /tmp/compare-software-power-meters/scaphandre && /tmp/docker-compose down -v && docker ps', False)
        print(result)
        
    def start_scaphandre_service(self, service_name='scaphandre'):
        start_scaphandre_service = "sudo sh -c 'service %s start && sleep 1 && service %s status'" % (service_name, service_name)
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, start_scaphandre_service)
        print(result)

    def stop_scaphandre_service(self, service_name='scaphandre'):
        stop_scaphandre_service = "sudo sh -c 'service %s stop && sleep 1 && service %s status'" % (service_name, service_name)
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, stop_scaphandre_service)
        print(result)
        
    def prepare_bench_host(self):
        print('Preparing bench host for Scaphandre...')
        
        # Copy bins, configs and creating services
        print('Copy Scaphandre binary into /opt dir...')
        copy_bin_files_command = "sudo cp -n /tmp/compare-software-power-meters/scaphandre/scaphandre /opt && ls /opt"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, copy_bin_files_command)
        print(result)
    
        print('Copy Scaphandre service file into /etc/systemd/system/...')
        copy_service_files_command = "sudo cp /tmp/compare-software-power-meters/scaphandre/scaphandre*.service* /etc/systemd/system/ && ls /etc/systemd/system/scaphandre*"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, copy_service_files_command)
        print(result)
    
        print('Check services...')
        check_services_command = "sudo sh -c 'systemctl daemon-reload; service scaphandre status; service scaphandre-cpu-0 status'"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, check_services_command)
        print(result)
        
        print('Bench host is prepared for Scaphandre...')
        
    def clean_bench_host(self):
        print("Stopping Scaphandre service...")
        self.stop_scaphandre_service('scaphandre')
        self.stop_scaphandre_service('scaphandre-cpu-0')
    
    def prepare_data_host(self):
        print('Preparing data host for Scaphandre...')
        
        copy_prom_config = "cp /tmp/compare-software-power-meters/scaphandre/prometheus-default.yml /tmp/compare-software-power-meters/scaphandre/prometheus.yml"
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, copy_prom_config)
        print(result)
        
        configure_command = "sed -i -E \"s/'.+:8080/'%s:8080/g\" /tmp/compare-software-power-meters/scaphandre/prometheus.yml && grep 'targets' /tmp/compare-software-power-meters/scaphandre/prometheus.yml" % self.experiments.jobs["bench"].host
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, configure_command)
        print(result)
        
        self.start_scaphandre_data()
        
        print('Data host is prepared for Scaphandre...')
        
    def clean_data_host(self):    
        print("Removing Scaphandre containers and storage...")
        self.stop_scaphandre_data()
        
    # Query prometheus instance and get consumption data
    def prometheus_scaphandre_query(self, query, start, stop, metrics):
        prometheus_command = "curl -s -G \"http://localhost:9090/api/v1/query_range?query=%s&start=%s&end=%s&step=%ss\"" % (urllib.parse.quote(query), start, stop, self.frequency)
        prometheus_result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, prometheus_command)
        prometheus_result_json = json.loads(prometheus_result[0]) if len(prometheus_result) > 0 else []
        if 'status' in prometheus_result_json and prometheus_result_json['status'] == 'success' and 'data' in prometheus_result_json:
            result = []
            for el in prometheus_result_json['data']['result']:
                for timestamp, value in el['values']:
                    result_dict = {}
                    # Adding metrics to entry
                    for metric in metrics:
                        result_dict[metric] = el['metric'][metric]
                    # Adding timestamp and value to entry
                    result_dict.update({
                        'timestamp': timestamp, 
                        'value': value})
                    result.append(result_dict)
            prometheus_pd = pd.json_normalize(result)
            if not prometheus_pd.empty:
                prometheus_pd['timestamp'] = pd.to_datetime(prometheus_pd['timestamp'], unit='s', origin='unix')
                prometheus_pd['value'] = prometheus_pd['value'].astype('int')
                prometheus_pd['value'] = prometheus_pd['value'] / 1000000
            return prometheus_pd
        else:
            return []

    # Get consumption of target and of overallhost from Scaphandre
    def get_consumption(self, experiment):
        # Converting time to Prometheus format
        start_time_prometheus = experiment.start_time.timestamp()
        end_time_prometheus = experiment.end_time.timestamp()
        
        # Get targets from benchmarks
        targets = experiment.get_binaries_from_benchmarks()

        # Query for process consumption
        exe_query = "|".join(targets)
        query_process = 'scaph_process_power_consumption_microwatts{exe=~"' + exe_query + '"}'
        metrics_process = ['exe','pid']
        process_pd = self.prometheus_scaphandre_query(query_process, start_time_prometheus, end_time_prometheus, metrics_process)

        # Normalize timestamp
        if 'timestamp' in process_pd:
            process_pd['timestamp'] = pd.to_datetime(process_pd['timestamp'])

        # Query for host consumption
        query_host = 'scaph_host_power_microwatts'
        metrics_host = ['instance']
        host_pd = self.prometheus_scaphandre_query(query_host, start_time_prometheus, end_time_prometheus, metrics_host)

        # Normalize timestamp
        if 'timestamp' in host_pd:
            host_pd['timestamp'] = pd.to_datetime(host_pd['timestamp'])
            
        # Query for host RAM consumption
        query_host_ram = 'sum(scaph_domain_power_microwatts{domain_name="dram"})'
        metrics_host_ram = []
        host_ram_pd = self.prometheus_scaphandre_query(query_host_ram, start_time_prometheus, end_time_prometheus, metrics_host_ram)

        # Normalize timestamp
        if 'timestamp' in host_ram_pd:
            host_ram_pd['timestamp'] = pd.to_datetime(host_ram_pd['timestamp'])
        
        return process_pd, host_pd, host_ram_pd
    
    # Get Scaphandre scrape interval
    def get_acquisition_frequency(self):
        command = "sed -E -n 's/ *scrape_interval: *([0-9]*)s.*/\\1/p' /tmp/compare-software-power-meters/scaphandre/prometheus.yml"
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, command)
        return result[0].strip()
    
    # Set Scaphandre scrape interval
    def set_acquisition_frequency(self, frequency):
        # Change Prometheus scrape interval
        command_hwpc_change_frequency = "sed -i -E 's/(scrape_interval:).*([0-9]+)s(.*)/\\1 %ds/g' /tmp/compare-software-power-meters/scaphandre/prometheus.yml" % frequency
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, command_hwpc_change_frequency)
        print(result)
        self.frequency = frequency
        
        
    def start_data(self):
        self.start_scaphandre_data()
        
    def stop_data(self):
        self.stop_scaphandre_data()

    def start_bench_service(self, service_type):
        if service_type == 'default':
            self.start_scaphandre_service()
        else:
            self.start_scaphandre_service('scaphandre-cpu-0') 
        
    def stop_bench_service(self, service_type):
        if service_type == 'default':
            self.stop_scaphandre_service()
        else:
            self.stop_scaphandre_service('scaphandre-cpu-0')
