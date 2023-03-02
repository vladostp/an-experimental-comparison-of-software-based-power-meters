
# An experimental comparison of software-based power meters: focus on CPU
Author: Vladimir Ostapenco

This repository contains the code for the experiments and the results of the experimental comparison of consumption measurement tools (software-based power meters).

## Software-based power meters compared
- [PowerAPI](https://powerapi-ng.github.io/) with Smartwatts
- [Scaphandre](https://hubblo-org.github.io/scaphandre-documentation/)
- [Perf](https://perf.wiki.kernel.org/index.php/Main_Page)
- Energy Scope (See [Energy Scope](#energy-scope))

## Directory layout
    .
    ├── analyze-results         # Result analyze Jupyter notebooks
    ├── bechmarks               # Benchmarks binaries
    ├── environments            # Grid'5000 environment files
    ├── experiments             # Code for the experiments
    ├── figures                 # Figures created during result analyze
    ├── node-exporter           # Node exporter configuration files and binaries
    ├── powerapi                # PowerAPI configuration files and binaries
    ├── results                 # Experiments results    
    ├── scaphandre              # Scaphandre configuration files and binaries 
    ├── scripts                 # Scripts needed to execute benchmarks 
    ├── LICENSE
    └── README.md

## Supported environment
- Grid'5000 testbed

## Launch experiments
First, you need to create a Grid'5000 account and login to a Grid'5000 frontal node. 

### Clone repository
The repository must be directly cloned to the Grid'5000 frontal node.
```bash
git clone git@gitlab.inria.fr:majay/an-experimental-comparison-of-software-based-power-meters.git
cd an-experimental-comparison-of-software-based-power-meters/CPU_Benchmarks/
```

### Create Grid'5000 environment
In order to run some experiments, you need to create a special Grid'5000 environment.
This environment is based on a minimal `Ubuntu 20.04` image with CPU `0` isolated from the operating system.
In this environment, CPU `0` is not used by the operating system scheduler, so no processes are scheduled on this CPU core.
In some experiments, we run software-based power meters on this core to assess CPU overhead.

Deploy the Grid'5000 `ubuntu2004-x64-cpu-0-isolate` environment with `kadeploy3` tool:
```bash
cd environments/
kadeploy3 -a ubuntu2004-x64-cpu-0-isolate.yaml
cd ../
```

### Compile benchamrks (Optional)
In the [./benchmarks/](./benchmarks/) directory, you can find the NAS benchmarks compiled at a Gemini cluster node of the Grid'5000 testbed.

If you want to run experiments on another node with a different architecture, you must recompile the NAS benchmarks on another node and place the result binaries in the [./benchmarks/](./benchmarks/) directory of this project.
```bash
wget https://www.nas.nasa.gov/assets/npb/NPB3.4.2.tar.gz # Download NAS benchmarks
tar -xvzf NPB3.4.2.tar.gz # Extract the archive
cd NPB3.4.2/NPB3.4-OMP # Go to NAS benchmarks OpenMP implementation
cp ./config/make.def.template ./config/make.def # Copy default configuration
make ep CLASS=C && make ep CLASS=D # Compile NAS EP Kernel
make lu CLASS=C # Compile NAS LU Kernel
make mg CLASS=D # Compile NAS MG Kernel
make is CLASS=D # Compile NAS IS Kernel
```
After compilation, the benchmark binaries will be available in [./bin/](./bin/). Copy them to the [./benchmarks/](./benchmarks/) directory of this project.

### Make Grid'5000 reservations
In order to run CPU experiments, you need to reserve two compute nodes by making two deployment-type reservations on the Grid'5000 testbed.

The first compute node is called the `bench` node and is used to evaluate software-based power meters.

The second compute node is called `data`. It is used to retrieve and store software-based power meters and operating system data from the `bench` node.

**Example:** Make two deployment-type reservations of `nova` cluster nodes for 4 hours.
```bash
oarsub -t deploy -l host=1,walltime=4:00 -p "cluster='nova'" "sleep infinity"
oarsub -t deploy -l host=1,walltime=4:00 -p "cluster='nova'" "sleep infinity"
```
The execution of these commande provides you two `OAR_JOB_ID` numbers.

These job IDs are required to launch experiments and must be provided in the `./launch_experiment.py` script call.

### Install required packages
Before launching experiments, please install the required Python packages.
```bash
pip install -r ./experiments/requirements.txt
```

## Launch experiments
The `./experiments/launch_experiment.py` command allows to launch CPU experiments. 

It deploys the necessary environment on the Grid'5000 nodes, applies the necessary system configuration, launches the components of the software-based power meters, runs the benchmarks and finally retrieves and stores the results in the [./results/](./results/) directory.

It has following parameters:
- `--g5k_site` [Mandatory] - Grid'5000 site where the nodes were reserved.
- `--bench_host_jobid` [Mandatory] - `bench` node reservation job ID.
- `--data_host_jobid` [Mandatory] - `data` node reservation job ID.
- `--experiment` [Mandatory] - Experiment to launch. (The experiences available are described below)
- `--experiment_repeat` [Optional] (Default: 1) - Number of times to repeat the experiment.
- `--no_image_deploy` [Optional] - Skip image (Grid'5000 environment) deployment step.
- `--energy_scope` [Optional] - Do Energy Scope experiments. By default, Energy Scope experiments are disabled because Energy Scope is not open source.

### Available experiments
| Experiment name | Experiment description |
|--|--|
| power_profiles | Launches one of software-based power meters. Executes EP D, LU C and MG D benchmarks with 2 minute wait between benchmarks. Repeats execution for each software-based power meter. Gets the power profiles of each software-based power meter, BMC and external power meter. |
| scaphandre_sampling_frequency | Configures and launches Scaphandre with different sampling frequencies (10 sec, 5 sec, 2 sec, 1 sec). Executes EP D benchmark. Gets the power profiles of Scaphandre, BMC and external power meter. |
| powerapi_sampling_frequency | Configures and launches PowerAPI with different sampling frequencies (1000 ms, 500 ms, 100 ms, 80 ms, 50 ms). Executes EP D benchmark. Gets the power profiles of PowerAPI, BMC and external power meter. |
| energy_scope_sampling_frequency | Configures EnergyScope with different sampling frequencies (500 ms, 200 ms, 100 ms, 50 ms, 20 ms). Executes EP D benchmark with EnergyScope. Gets the power profiles of EnergyScope, BMC and external power meter. |
| scaphandre_cpu_overhead | Launches Scaphandre on an isolated CPU core with different sampling frequencies (10 sec, 5 sec, 2 sec, 1 sec). Executes EP D, LU C and MG D benchmarks with 2 minute wait between benchmarks. Gets the power profiles of Scaphandre, BMC and external power meter. Gets the CPU load profile of the isolated CPU core where Scaphandre is running. |
| powerapi_cpu_overhead | Launches PowerAPI(HWPC) on an isolated CPU core with different sampling frequencies (1000 ms, 500 ms, 100 ms, 80 ms, 50 ms). Executes EP D, LU C and MG D benchmarks with 2 minute wait between benchmarks. Gets the power profiles of PowerAPI, BMC and external power meter. Gets the CPU load profile of the isolated CPU core where PowerAPI(HWPC) is running. |
| powerapi_max_process | Launches PowerAPI(HWPC) on an isolated CPU core. Executes a different number of instances (4, 5, 6, 7, 8, 9, 10) of EP C benchmarks running on one thread. Gets the power profiles of PowerAPI, BMC and external power meter. Gets the CPU load profile of the isolated CPU core where PowerAPI(HWPC) is running. Smartwatts version 28-02-2022. |
| powerapi_max_process_v0_9_2 | Launches PowerAPI(HWPC) on an isolated CPU core. Executes a different number of instances (4, 10, 12, 14, 16, 18, 20) of EP C benchmarks running on one thread. Gets the power profiles of PowerAPI, BMC and external power meter. Gets the CPU load profile of the isolated CPU core where PowerAPI(HWPC) is running. Smartwatts version 0.9.2.|
| scaphandre_max_process | Launches Scaphandre on an isolated CPU core. Executes a different number of instances (5, 10, 20, 30, 50, 100) of EP C benchmarks running on one thread. Gets the power profiles of Scaphandre, BMC and external power meter. Gets the CPU load profile of the isolated CPU core where Scaphandre is running. |
| is_mg_parallel_execution | Launches PowerAPI. Executes IS D and MG D benchmarks in parallel. Stops PowerAPI. Launches Scaphandre. Repeats the parallel execution of IS D and MG D benchmarks. Gets the power profiles of PowerAPI, Scaphandre, BMC and external power meter. |
| two_ep_parallel_execution | Launches PowerAPI. Executes two EP D benchmarks in parallel. Stops PowerAPI. Launches Scaphandre. Repeats the parallel execution of two EP D benchmarks. Gets the power profiles of PowerAPI, Scaphandre, BMC and external power meter. |
| two_mg_parallel_execution | Launches PowerAPI. Executes two MG D benchmarks in parallel. Stops PowerAPI. Launches Scaphandre. Repeats the parallel execution of two MG D benchmarks. Gets the power profiles of PowerAPI, Scaphandre, BMC and external power meter. |
| three_ep_parallel_execution | Launches PowerAPI. Executes three EP D benchmarks in parallel. Stops PowerAPI. Launches Scaphandre. Repeats the parallel execution of three EP D benchmarks. Gets the power profiles of PowerAPI, Scaphandre, BMC and external power meter.  |
| ep_lu_parallel_execution | Launches PowerAPI. Executes EP D and LU D benchmarks in parallel. Stops PowerAPI. Launches Scaphandre. Repeats the parallel execution of EP D and LU D benchmarks. Gets the power profiles of PowerAPI, Scaphandre, BMC and external power meter. |
| no_solution_execution | Executes EP D, LU C and MG D benchmarks with 2 minute wait between benchmarks without launching any software-based power meter. Gets the power profiles of BMC and external power meter. |
| perf_total_energy | Executes EP D, LU C and MG D benchmarks with Perf with 2 minute wait between benchmarks. Gets total energy consumed per benchmark reported by Perf and the power profiles of BMC and external power meter. |
| perf_power_profile | Executes EP D, LU C and MG D benchmarks with Perf (with interval print option) with 2 minute wait between benchmarks. Gets power profiles reported by Perf, BMC and external power meter. |
| perf_sampling_frequency | Executes EP D benchmark with Perf with different sampling frequencies (interval print options). Gets power profiles reported by Perf, BMC and external power meter. |

### Power profiles exepriment launch example
```bash
cd experiments/
./launch_experiment.py --g5k_site lyon --bench_host_jobid 1444422 --data_host_jobid 1444433 --experiment power_profiles
```

## Result data description
The execution of an exeriment produces result data containing power profiles or CPU load profiles. 
The result data is stored in the [./results/](./results/) directory.
For each experiment, the [./results/](./results/) directory has a different prefix and is postfixed by the hostname of `bench` node and the end time of benchmark execution.

### Experiments result directory prefixes
| Experiment name | Result directory prefix |
|--|--|
| power_profiles | 3-solutions-compare |
| scaphandre_sampling_frequency | scaphandre-frequency-change |
| powerapi_sampling_frequency | powerapi-frequency-change |
| energy_scope_sampling_frequency | energy-scope-frequency-change |
| scaphandre_cpu_overhead | scaphandre-cpu-overhead |
| powerapi_cpu_overhead | powerapi-cpu-overhead |
| powerapi_max_process | powerapi-max-process-number |
| powerapi_max_process_v0_9_2 | powerapi-max-process-number-new |
| scaphandre_max_process | scaphandre-max-process-number |
| is_mg_parallel_execution | 2-solutions-compare-2-parallel-different-ram |
| two_ep_parallel_execution | 2-solutions-compare-2-parallel-same |
| two_mg_parallel_execution | 2-solutions-compare-2-parallel-same-ram |
| three_ep_parallel_execution | 2-solutions-compare-3-parallel-same |
| ep_lu_parallel_execution | 2-solutions-compare-parallel-different |
| no_solution_execution | no-solution |
| perf_total_energy | perf-evaluate |
| perf_power_profile | perf-power-profile |
| perf_sampling_frequency | perf-sampling-frequency |

Each result directory contains:
- `experiments.json` file - Contains experiment metadata, description, and runtime logs.
- `.csv` files - Contain power profiles of software-based power meters or external power meters (kwollect).
- `cpu-load-*.csv` files - Contain CPU load profiles if present.

## Analyze results
In order to analyze the results, we use Jupyter notebooks available in the [./analyze-results/](./analyze-results/) directory.

Some Jupyter notebooks produce figures and save them in `.pdf` and `.png` formats in the [./figures/](./figures/) folder.

### Install required packages
Before executing Jupyter notebooks, please install the required Python packages.
```bash
pip install -r ./analyze-results/requirements.txt
```

### Available Jupyter notebooks
| Jupyter notebook name | Description |
|--|--|
| [./analyze-results/application-process-study.ipynb](./analyze-results/application-process-study.ipynb) | In this notebook, we study how PowerAPI and Scaphandre estimate consumption at the application process level. |
| [./analyze-results/correlation-study.ipynb](./analyze-results/correlation-study.ipynb) | In this notebook, we study the offset and the correlation between the values given by each tool and the values reported by the external power meter. |
| [./analyze-results/cpu-overhead-study.ipynb](./analyze-results/cpu-overhead-study.ipynb) | In this notebook, we study the CPU overhead of PowerAPI and Scaphandre by running each solution with different sampling frequency configurations on an isolated CPU core and by tracking the utilization rate of that core. |
| [./analyze-results/energy-overhead-study.ipynb](./analyze-results/energy-overhead-study.ipynb) | In this notebook, we study the additional energy cost of each solution. We proceed by comparing the energy consumed by executions with and without tools. |
| [./analyze-results/maximum-sampling-frequency-study.ipynb](./analyze-results/maximum-sampling-frequency-study.ipynb) | In this notebook, we study the maximum sampling frequency supported by each solution. |
| [./analyze-results/maximum-simultaneous-processes-study.ipynb](./analyze-results/maximum-simultaneous-processes-study.ipynb) | In this notebook, we study the maximum number of simultaneously estimated processes supported by each solution. |
| [./analyze-results/power-profile-study.ipynb](./analyze-results/power-profile-study.ipynb) | In this notebook, we compare the power profiles given by each software power meter, BMC and external power meter. |
| [./analyze-results/total-energy-study.ipynb](./analyze-results/total-energy-study.ipynb) | In this notebook, we calculate and compare total energy values given by each software power meter, BMC and external power meter. |


### Available Jupyter notebooks without Energy Scope
These Jupyter notebooks can be used with experiments performed without Energy Scope.
| Jupyter notebook name | Description |
|--|--|
| [./analyze-results/power-profile-study-no-energy-scope.ipynb](./analyze-results/power-profile-study-no-energy-scope.ipynb) | In this notebook, we compare the power profiles given by each software power meter, BMC and external power meter. |
| [./analyze-results/total-energy-study-no-energy-scope.ipynb](./analyze-results/total-energy-study-no-energy-scope.ipynb) | In this notebook, we calculate and compare total energy values given by each software power meter, BMC and external power meter. |


## Energy Scope
Energy Scope is not open source and not publicly available. To ask the Energy Scope code, please contact herve.mathieu@inria.fr.
The supplied code should be placed in the `./energy_scope` folder and the experiments should be launched with the `--energy_scope` option.

# Contact
If you have any questions or suggestions please contact me at vladimir.ostapenco@inria.fr.

# Acknowledgement
Experiments are carried out using the Grid’5000 testbed, supported by a scientific interest group hosted by Inria and including CNRS, RENATER and several Universities as well as other organizations (see https://www.Grid'5000.fr).

# License
This work is licensed under a Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) License.
You should have received a copy of the license along with this work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
