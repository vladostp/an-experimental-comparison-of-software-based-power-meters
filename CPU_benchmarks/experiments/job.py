import grid5000
from time import sleep
from typing import List
from pathlib import Path

gk = grid5000.Grid5000()

# Job class
class Job:
    def __init__(self, no_image_deploy=True):
        self.host = None
        self.user = None
        self.g5k_job_instance = None
        self.deployment = None
        self.uid = None
        self.job_type = None
        self.no_image_deploy = no_image_deploy
        
    # Job is a simple host (not G5k job)
    def host_job(self,
                 host,
                 user):
        self.host = host
        self.user = user
        self.job_type = "host"
        
    def get_job(self,
                site,
                jobid,
                user):
        self.site = site
        self.uid = jobid
        self.g5k_job_instance = gk.sites[self.site].jobs.get(self.uid)
        self.user = user
        
        if self.g5k_job_instance:
            print("Found job %s at %s site." % (self.uid, self.site))
        else:
            raise Exception("Job %s was not found at %s site." % (self.uid, self.site))
            
        self.g5k_job_instance.refresh()
        while self.g5k_job_instance.state not in ("running", "error"):
            print('Waiting for job %s to be ready...' % str(self.uid))
            sleep(15)
            self.g5k_job_instance.refresh()
            
        self.host = self.g5k_job_instance.assigned_nodes[0]
        
        print("Job is running and job machine is %s" % self.host)
        
        self.job_type = "got"
        
    def create_job(self,
                site,
                cluster,
                walltime,
                queue,
                types,
                user,
                environment=""
              ) -> None: 
        """
        Creates a job at Grid 5000
        """
        self.site = site
        self.cluster = cluster
        self.walltime = walltime
        self.queue = queue
        self.types = types
        self.user = user
        self.environment = environment
        
        # If job type is not deploy adding allow_classic_ssh if necessary
        if 'deploy' not in self.types and 'allow_classic_ssh' not in self.types:
            self.types.append('allow_classic_ssh')
        
        properties = "cluster='%s'" % self.cluster

        oarcall = dict(
            command="sleep 3d",
            resources="host=1,walltime=%s" % self.walltime,
            properties=properties,
            queue=self.queue,
            types=self.types,
        )
        
        self.g5k_job_instance = gk.sites[self.site].jobs.create(oarcall)
        
        self.uid = self.g5k_job_instance.uid
        
        print("Created job %s on %s (%s)." % (self.uid, self.cluster, self.site))
        
        self.type = "created"
        
    def wait_for_job(self):
        """
        Waiting for job to be ready
        """
        if self.g5k_job_instance is None:
            print("Job instance was not found, so nothing to wait.")
            return
        
        self.g5k_job_instance.refresh()
        while self.g5k_job_instance.state not in ("running", "error"):
            sleep(5)
            self.g5k_job_instance.refresh()
            
        self.host = self.g5k_job_instance.assigned_nodes[0]
        
        if 'deploy' in self.types:
            self.create_deployment(self.environment, self.user)
            self.wait_for_deployment()
            
        print("We can now access our machine %s" % self.host)
            
            
    def create_deployment(self,
                         environment,
                         user):
        """
        Create a deployment at Grid5000
        """
        if self.no_image_deploy:
            print("Image deployment is disabled.")
            return

        if 'deploy' not in self.g5k_job_instance.types:
            print("No deployment type was found for this job")
            return
        
        print("Creating a deployment for deploy job %s." % self.uid)
        deployment_create = {
            "nodes": self.g5k_job_instance.assigned_nodes,
            "environment": environment
        }

        deployment_create["key"] = Path.home().joinpath(".ssh", "id_rsa.pub").read_text()

        self.deployment = gk.sites[self.site].deployments.create(deployment_create)
        self.user = user
        
    def wait_for_deployment(self):
        """
        Wait to deployment to be ready
        """
        if self.no_image_deploy:
            print("Image deployment is disabled.")
            return
        if self.deployment is None:
            print("No deployment found for this job.")
            return
        
        while self.deployment.status != "terminated":
            self.deployment.refresh()
            print("Waiting for the deployment [%s] to be finished. Must take 2-5 minutes." % self.deployment.uid)
            sleep(10)
        print("A deployment for deploy job %s was created." % self.uid)
        print(self.deployment.uid)
        
    def release(self):
        if not self.g5k_job_instance:
            raise Exception("Can't release non G5K job.")
        self.g5k_job_instance.delete()
        
    def wait_for_release(self):
        if not self.g5k_job_instance:
            raise Exception("Can't release non G5K job.")
        self.g5k_job_instance.refresh()
        while self.g5k_job_instance.state not in ("finishing","error"):
            sleep(5)
            self.g5k_job_instance.refresh()
        print("Job %s is done..." % self.uid)
