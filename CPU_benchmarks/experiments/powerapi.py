import subprocess
import pytz
import pandas as pd
import pymongo

from utils import *
from solution import Solution

# PowerAPI Class
class PowerAPI(Solution):
    def __init__(self, experiment, version='march'):
        self.name = 'powerapi'
        if 'data' not in experiment.jobs or 'bench' not in experiment.jobs:
            raise Exception("To use PowerAPI both data and bench jobs must be set in experiment...")
        self.experiment = experiment
        self.cgroups = []
        self.version = version
        
    def prepare_bench_host(self):
        print('Preparing bench host for PowerAPI...')
        # Prepare Smartwatts configuration file at bench host
        smartwatts_config_create_command = "cd /tmp/compare-software-power-meters/powerapi && ./create_config_smartwatts.sh && ls -al ./smartwatts_config.json"
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, smartwatts_config_create_command)
        print(result)
        
        # Get current host user
        get_user_command = "id -u -n"
        process = subprocess.run(get_user_command, shell=True, check=True, text=True, stdout=subprocess.PIPE)
        user = process.stdout.rstrip("\n")
        print(user)
        
        # Copy Smartwatts configuration file to current host
        path = "/tmp/compare-software-power-meters"
        scp_copy_file(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, "%s/powerapi/smartwatts_config.json" % path, "../powerapi/")
        
        # Copy bins, configs and creating services
        print('Copy HWPC binary into /opt dir...')
        copy_bin_files_command = "sudo cp -n /tmp/compare-software-power-meters/powerapi/hwpc-sensor /opt && ls /opt"
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, copy_bin_files_command)
        print(result)
    
        print('Copy hwpc config file into /opt dir...')
        copy_config_files_command = "sudo cp /tmp/compare-software-power-meters/powerapi/hwpc_config.json /opt && ls /opt"
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, copy_config_files_command)
        print(result)
        
        # Configuring HWPC on bench host
        configure_hwpc_command = "sed -i -E 's/\\\"mongodb:\/\/(.+)\\\"/\\\"mongodb:\/\/%s\\\"/g' /opt/hwpc_config.json && jq '.output.uri' /opt/hwpc_config.json" % self.experiment.jobs["data"].host
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, configure_hwpc_command)
        print(result)
    
        print('Copy hwpc service file into /etc/systemd/system/...')
        copy_service_files_command = "sudo cp /tmp/compare-software-power-meters/powerapi/hwpc-sensor*.service* /etc/systemd/system/ && ls /etc/systemd/system/hwpc*"
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, copy_service_files_command)
        print(result)
    
        print('Check services...')
        check_services_command = "sudo sh -c 'systemctl daemon-reload; service hwpc-sensor status; service hwpc-sensor-cpu-0 status'"
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, check_services_command)
        print(result)
        
        print('Bench host is prepared for PowerAPI...')
    
    def clean_bench_host(self):
        print("Stopping HWPC service...")
        self.stop_hwpc_service('hwpc-sensor')
        self.stop_hwpc_service('hwpc-sensor-cpu-0')
    
    def start_powerapi_data(self):
        result = ssh_exec_command(self.experiment.jobs["data"].user, self.experiment.jobs["data"].host, 'cd /tmp/compare-software-power-meters/powerapi && /tmp/docker-compose up -d && docker ps', False)
        print(result)
    
    def stop_powerapi_data(self):
        result = ssh_exec_command(self.experiment.jobs["data"].user, self.experiment.jobs["data"].host, 'cd /tmp/compare-software-power-meters/powerapi && /tmp/docker-compose down -v && docker ps', False)
        print(result)
    
    def prepare_data_host(self):
        print('Preparing data host for PowerAPI...')
        self.set_smartwatts_version()
        self.start_powerapi_data()
        print('Data host is prepared for PowerAPI...')
        
    def set_smartwatts_version(self):
        # Change smartwatts version in docker compose file
        change_smartwatts_version = "sed -i -E 's/vladost\/smartwatts:(.+)/vladost\/smartwatts:%s/g' /tmp/compare-software-power-meters/powerapi/docker-compose.yml" % self.version
        result = ssh_exec_command(self.experiment.jobs["data"].user, self.experiment.jobs["data"].host, change_smartwatts_version)
        print(result)

    def clean_data_host(self):
        print("Removing PowerAPI containers and storage...")
        self.stop_powerapi_data()
       
    def start_hwpc_service(self, service_name='hwpc-sensor'):
        start_hwpc_service = "sudo sh -c 'service %s start && sleep 1 && service %s status'" % (service_name, service_name)
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, start_hwpc_service)
        print(result)
    
    def check_hwpc_report_send(self):
        show_logs_command = "docker logs --tail 10 powerapi_smartwatts_1"
        result = ssh_exec_command(self.experiment.jobs["data"].user, self.experiment.jobs["data"].host, show_logs_command)
        print(result)

    def stop_hwpc_service(self, service_name='hwpc-sensor'):
        stop_hwpc_service = "sudo sh -c 'service %s stop && sleep 1 && service %s status'" % (service_name, service_name)
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, stop_hwpc_service)
        print(result)
       
    def add_cgroup(self, cgroup):
        print('Creating %s cgroup...' % cgroup)
        create_cgroup_command = "sudo cgcreate -g perf_event:%s" % cgroup
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, create_cgroup_command)
        print(result)
        
        print('Checking if cgroup was created...')
        check_cgroup_command = "sudo lscgroup -g perf_event:%s" % cgroup
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, check_cgroup_command)
        print(result)
        
        # If Cgroup is not already present in targets adding it
        if cgroup not in self.cgroups:
            print("Adding cgroup to PowerAPI targets...")
            self.cgroups.append(cgroup)
            
    def delete_cgroup(self, cgroup):
        print('Removing %s cgroup...' % cgroup)
        delete_cgroup_command = "sudo cgdelete perf_event:%s" % cgroup
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, delete_cgroup_command)
        print(result)
        
        if cgroup in self.cgroups:
            self.cgroups.remove(cgroup)
        
    # Get PowerAPI PowerReports from MongoDB
    def get_consumption(self, experiment):
        # Get start and end time and converting them to UTC
        start_time_mongo = experiment.start_time.astimezone(pytz.utc)
        end_time_mongo = experiment.end_time.astimezone(pytz.utc)

        # Connection to MongoDB instance
        mongo_client = pymongo.MongoClient("mongodb://%s:27017/" % self.experiment.jobs["data"].host)
        # Getting database and collection
        db = mongo_client["smartwatts"]
        collection = db["power"]
        
        # Select finding entries between start and stop time
        cursor = collection.find({ "timestamp" : { "$gte" :  start_time_mongo, "$lte" : end_time_mongo}})
        
        # Creating a dataframe from mongodb results
        powerapi_pd = pd.DataFrame(cursor)
        
        # Creating new columns from metadata
        if 'metadata' in powerapi_pd:
            powerapi_pd['scope'] = powerapi_pd['metadata'].apply(lambda v: v.get('scope') if isinstance(v, dict) else '')
            powerapi_pd['socket'] = powerapi_pd['metadata'].apply(lambda v: v.get('socket') if isinstance(v, dict) else '')
            powerapi_pd['formula'] = powerapi_pd['metadata'].apply(lambda v: v.get('formula') if isinstance(v, dict) else '')
            powerapi_pd['ratio'] = powerapi_pd['metadata'].apply(lambda v: v.get('ratio') if isinstance(v, dict) else '')
            powerapi_pd['predict'] = powerapi_pd['metadata'].apply(lambda v: v.get('predict') if isinstance(v, dict) else '')
        
        # Removing unnecessary columns
        if '_id' in powerapi_pd and 'sender_name' in powerapi_pd and 'sensor' in powerapi_pd and 'dispatcher_report_id' in powerapi_pd and 'metadata' in powerapi_pd:
            powerapi_pd = powerapi_pd.drop(columns=['_id', 'sender_name', 'sensor', 'dispatcher_report_id', 'metadata'])

        # Normalize timestamp
        if 'timestamp' in powerapi_pd:
            powerapi_pd['timestamp'] = pd.to_datetime(powerapi_pd['timestamp'])
            
        # Close mongodb connection
        mongo_client.close()
        
        return powerapi_pd
   
    def get_acquisition_frequency(self):
        command = "cat /opt/hwpc_config.json | jq '.frequency'"
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, command)
        return result[0].strip()

    def set_acquisition_frequency(self, frequency):
        # Change HWPC frequency
        command_hwpc_change_frequency = "sed -i -E 's/(\"frequency\":)(.*)/\\1 %d,/g' /opt/hwpc_config.json" % frequency
        result = ssh_exec_command(self.experiment.jobs["bench"].user, self.experiment.jobs["bench"].host, command_hwpc_change_frequency)
        print(result)

        # Change Smartwatts frequency
        command_change_smartwatts_frequency = "sed -i -E 's/(\"sensor-report-sampling-interval\":)(.*)/\\1 %d/g' /tmp/compare-software-power-meters/powerapi/smartwatts_config.json" % frequency
        result = ssh_exec_command(self.experiment.jobs["data"].user, self.experiment.jobs["data"].host, command_change_smartwatts_frequency)
        print(result)

    def start_data(self):
        self.start_powerapi_data()
        
    def stop_data(self):
        self.stop_powerapi_data()

    def start_bench_service(self, service_type):
        if service_type == 'default':
            self.start_hwpc_service()
        else:
            self.start_hwpc_service('hwpc-sensor-cpu-0') 
        
    def stop_bench_service(self, service_type):
        if service_type == 'default':
            self.stop_hwpc_service()
        else:
            self.stop_hwpc_service('hwpc-sensor-cpu-0')
            
    def clean_after_experiment(self):
        print('Removing cgroups after experiment...')
        for cgroup in self.cgroups[:]:
            self.delete_cgroup(cgroup)