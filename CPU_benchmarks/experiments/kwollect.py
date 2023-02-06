import requests
import pandas as pd

from utils import *
from solution import Solution

# Kwollect Class
class Kwollect(Solution):
    def __init__(self, experiments):
        self.experiments = experiments
        self.name = 'kwollect'
        self.api_link = 'https://api.grid5000.fr'
        self.metrics = 'wattmetre_power_watt,pdu_outlet_power_watt,bmc_node_power_watt'
    
    # Get Kwollect consumption
    def get_consumption(self, experiment):
        # Converting time to Kwollect time format
        start_time_kwollect = experiment.start_time.timestamp()
        end_time_kwollect = experiment.end_time.timestamp()
        site_kwollect = self.experiments.jobs["bench"].site
        host_kwollect = self.experiments.jobs["bench"].host

        api_link_kwollect = "%s/stable/sites/%s/metrics?nodes=%s&metrics=%s&start_time=%s&end_time=%s" % (self.api_link, site_kwollect, host_kwollect, self.metrics, start_time_kwollect, end_time_kwollect)
        result_kwollect = requests.get(api_link_kwollect).json()
        kwollect_pd = pd.json_normalize(result_kwollect)
    
        # Normalize timestamp
        if 'timestamp' in kwollect_pd:
            kwollect_pd['timestamp'] = pd.to_datetime(kwollect_pd['timestamp'], utc=True).dt.tz_localize(None)

        return kwollect_pd