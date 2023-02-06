#!/usr/bin/env python3
# coding: utf8
# -*- coding:utf-8 -*-

# 2022

# Importing necessary libs
import argparse
from job import Job
from utils import *
from available_experiments import *

# Argument parser
def parse_arguments():
    parser = argparse.ArgumentParser(description='Compare software power meters experiments launch tool.')
    parser.add_argument('--g5k_site',
                        help='Site on which grid500 job was launched.',
                        required=True)
    parser.add_argument('--bench_host_jobid',
                        help='Job ID of the host on which the experiment will be launched.',
                        required=True,
                        type=int)
    parser.add_argument('--data_host_jobid',
                        help='Job ID of the host on which the data collection part will be launched.',
                        required=True,
                        type=int)
    parser.add_argument('--experiment',
                        help='Experiment to launch. For the description of the experiments, see the documentation.',
                        choices=list(available_experiments.keys()),
                        required=True)
    parser.add_argument('--experiment_repeat',
                        help='How many times to run the experiment.',
                        default=1,
                        type=int)
    parser.add_argument('--no_image_deploy',
                        help='Don\'t deploy image at Grid5000.',
                        default=False,
                        action='store_true')
    parser.add_argument('--energy_scope',
                        help='Include Enegy Scope experiments.',
                        default=False,
                        action='store_true')

    return parser.parse_args()

# Main function
def main():
    # Processing arguments
    args = parse_arguments()

    # Get from params if Energy Scope experiments are enabled
    energy_scope_enabled = bool(args.energy_scope)

    # Get already created jobs from script params
    job_bench_id = int(args.bench_host_jobid)
    job_data_id = int(args.data_host_jobid)

    # Creating job objects for each 
    job_bench = Job(bool(args.no_image_deploy))
    job_data = Job(bool(args.no_image_deploy))

    ## Getting jobs
    job_bench.get_job(args.g5k_site, job_bench_id, 'root')
    job_data.get_job(args.g5k_site, job_data_id, 'root')

    # Launching experiment
    experiment_name = args.experiment
    experiment_repeat = int(args.experiment_repeat)
    print("----- [Launching the %s experiment %s times] -----" % (experiment_name, experiment_repeat))
    available_experiments[experiment_name](job_bench, job_data, experiment_repeat, energy_scope_enabled)

if __name__ == '__main__':
    main()
