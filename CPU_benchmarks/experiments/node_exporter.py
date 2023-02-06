import urllib.parse
import pandas as pd
import json

from utils import *
from solution import Solution

# Node exporter
class NodeExporter(Solution):
    def __init__(self, experiments):
        self.experiments = experiments
    
    def prepare_bench_host(self):
        print('Preparing bench host for node exporter...')
        
        # Copy bins, configs and creating services
        print('Copy node exporter binary into /opt dir...')
        copy_bin_files_command = "sudo cp -n /tmp/compare-software-power-meters/node-exporter/node_exporter /opt && ls /opt"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, copy_bin_files_command)
        print(result)
    
        print('Copy node exporter service file into /etc/systemd/system/...')
        copy_service_files_command = "sudo cp /tmp/compare-software-power-meters/node-exporter/node-exporter.service /etc/systemd/system/ && ls /etc/systemd/system/node-exporter*"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, copy_service_files_command)
        print(result)
    
        print('Check services...')
        check_services_command = "sudo sh -c 'systemctl daemon-reload; service node-exporter status'"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, check_services_command)
        print(result)
        
        print('Staring node exporter service...')
        self.start_node_exporter_service()
        
        print('Bench host is prepared for node exporter...')
        
    def clean_bench_host(self):
        print('Stopping node exporter service...')
        self.stop_node_exporter_service()
    
    def prepare_data_host(self):
        print('Preparing data host for node exporter...')
        
        print('Configuring node exporter prometheus instance...')
        configure_command = "sed -i -E \"s/'.+:9100/'%s:9100/g\" /tmp/compare-software-power-meters/node-exporter/prometheus.yml && grep 'targets' /tmp/compare-software-power-meters/node-exporter/prometheus.yml" % self.experiments.jobs["bench"].host
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, configure_command)
        print(result)
        
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, 'cd /tmp/compare-software-power-meters/node-exporter && /tmp/docker-compose up -d && docker ps', False)
        print(result)
        
        print('Data host is prepared for node exporter...')
        
    def clean_data_host(self):
        print('Removing node exporter containers and storage...')
        result = ssh_exec_command(self.experiments.jobs["data"].user, self.experiments.jobs["data"].host, 'cd /tmp/compare-software-power-meters/node-exporter && /tmp/docker-compose down -v && docker ps', False)
        print(result)
        
    def start_node_exporter_service(self):
        start_node_exporter_service = "sudo sh -c 'service node-exporter start && sleep 1 && service node-exporter status'"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, start_node_exporter_service)
        print(result)

    def stop_node_exporter_service(self):
        stop_node_exporter_service = "sudo sh -c 'service node-exporter stop && sleep 1 && service node-exporter status'"
        result = ssh_exec_command(self.experiments.jobs["bench"].user, self.experiments.jobs["bench"].host, stop_node_exporter_service)
        print(result)
        
    # Query prometheus instance and get cpu data
    def prometheus_node_exporter_query(self, query, start, stop, metrics):
        prometheus_command = "curl -s -G \"http://localhost:9091/api/v1/query_range?query=%s&start=%s&end=%s&step=5s\"" % (urllib.parse.quote(query), start, stop)
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
                prometheus_pd['value'] = prometheus_pd['value'].astype('float')
            return prometheus_pd
        else:
            return []

    # Get CPU load from node exporter prometheus instance
    def get_cpu_load(self, experiment):
        # Converting time to Prometheus format
        start_time_prometheus = experiment.start_time.timestamp()
        end_time_prometheus = experiment.end_time.timestamp()

        query = '100 - (avg by (cpu, instance) (irate(node_cpu_seconds_total{mode="idle"}[10s])) * 100)'
        metrics = ['cpu']
        
        cpu_load_pd = self.prometheus_node_exporter_query(query, start_time_prometheus, end_time_prometheus, metrics)

        # Normalize timestamp
        if 'timestamp' in  cpu_load_pd:
             cpu_load_pd['timestamp'] = pd.to_datetime(cpu_load_pd['timestamp'])

        return cpu_load_pd
    