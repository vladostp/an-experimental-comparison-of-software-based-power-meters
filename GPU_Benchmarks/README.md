# An experimental comparison of software-based power meters: GPU side
Author: Mathilde Jay   
Last update: February, the 3rd 2023

- [How to use this repository](#how-to-use-this-repository)
    - [Node and OS](#node-and-os)
    - [How to use the Grid'5000 testbed](#how-to-use-the-grid5000-testbed)
    - [Launch experiments locally](#launch-experiments-locally)
    - [Result data description](#result-data-description)
    - [Process results](#process-results)
    - [Analyse results](#analyse-results)
- [Add a tool to the framework](#add-a-tool-to-the-framework)
- [Contact](#contact)
- [Acknowledgement](#acknowledgement)
- [License](#license)

# Tool included in this work
- CarbonTracker: [https://github.com/lfwa/carbontracker/](https://github.com/lfwa/carbontracker/)
- CodeCarbon: [https://github.com/mlco2/codecarbon/blob/master/README.md](https://github.com/mlco2/codecarbon/blob/master/README.md)
- EnergyScope [Not open sourced]
- ExperimentImpactTracker: [https://github.com/Breakend/experiment-impact-tracker](https://github.com/Breakend/experiment-impact-tracker)

# How to use this repository
## Execution environment
This framework was tested on the gemini cluster of the grid'5000 plateform. The node in this cluster have the following specifications:
- System model: Nvidia DGX-1
- CPU: 2 x Intel Xeon E5-2698 v4 (Broadwell, 2.20GHz,
20 cores/CPU)
- Memory: 512 GiB
- GPU: 8 x Nvidia Tesla V100-SXM2-32GB (32 GiB) 
- OS: Ubuntu 20.04
    
Most of the tools require Intel RAPL and NVIDIA NVML to monitor the energy consumption.

## EnergyScope
If you are able to get the right version of EnergyScope, please create a folder `software-installation` in the `GPU_Benchmarks` folder and place the code in it. It should be called `energy-scope_v2022-03-24_acquisition.tar`.
It was developed by Hervé Mathieu. Please contact him at herve.mathieu@inria.fr to ask for the code.

## How to use the Grid'5000 testbed
### Log into the Lyon site
```
  $ ssh yourlogin@access.grid5000.fr
  $ ssh lyon
```

### Book a node
Here are examples on how to deploy and reserve grid5000 nodes.
- To book a node a soon as it is available:
```
user@flyon:~$ oarsub -t deploy -t exotic -p "host='gemini-1.lyon.grid5000.fr'" -l walltime=2 -I
user@flyon:~$ oarsub -C $JOB_ID
```
- To book a node at a specific time:
```
user@flyon:~$ oarsub -t deploy -r "2022-04-20 19:00:00" -t exotic -p "host='gemini-1.lyon.grid5000.fr'" -l walltime=14:00
user@flyon:~$ oarsub -C $JOB_ID
```

### Deploy the image
To reduce the impact of the OS on our experiment, we chose to use a minimalist OS.
To do that we will use the kadeploy option of grid5000:
```
user@flyon:~$ kadeploy3 -k -e ubuntu2004-x64-min -f $OAR_FILE_NODES
user@flyon:~$ ssh -A root@gemini-1.lyon.grid5000.fr
```
or, if the ressource was reserved:
```
user@flyon:~$ oarsub -C JOBID
user@flyon:~$ kadeploy3 -k -e ubuntu2004-x64-min -m gemini-1
user@flyon:~$ ssh -A root@gemini-1.lyon.grid5000.fr
```
You can access the node with ssh (see below). However, we advise you to use the script `code/automation_scripts/gemini1.sh` where all the steps described in the following section are launched automatically. To do so, you need to modify the script to add you login. 
Either do
```
# Please replace YOURLOGIN in the file and in the following command
user@flyon:~$ bash /home/YOURLOGIN/an-experimental-comparison-of-software-based-power-meters/code/automation_scripts/gemini1.sh
```
or execute the commands below and follow the steps on the following section.
```
user@flyon:~$ ssh root@gemini-1 "mkdir /root/comparison/"
user@flyon:~$ rsync -avzh bash /home/YOURLOGIN/an-experimental-comparison-of-software-based-power-meters/ root@gemini-1:/root/comparison/
user@flyon:~$ ssh -A root@gemini-1.lyon.grid5000.fr
```

## Launch experiments locally
### Set up the environment
This repository contains scripts automating the deployement of series of experiments. All the source code can be found in the `code/` repository.

```
REPO=./an-experimental-comparison-of-software-based-power-meters/GPU_Benchmarks/
cd $REPO
```

- Execute the installation script 
```
bash code/install_scripts/installation.sh
```
It will install all the needed packages.

- Get the environement ready
Disable theads and turbo boost and set the CPU frequency to its maximum to improve the reproducibility of the results:
```
bash code/install_scripts/get_env_ready.sh
```

- Compile the benchmarks
To make sure that the benchmarks will compile, check the compute capability in make.def. It needs to match your GPU.   
For the gemini cluster of Grid'5000, we changed it to `COMPUTE_CAPABILITY = -gencode arch=compute_70,code=sm_70`.
   
To compile the NAS benchmark implemented in CUDA, for 2 GPUs:
```
cd ../../
git clone git@github.com:GMAP/NPB-GPU.git
bash $REPO/GPU_benchmark_binaries/compile_all.sh 2 ./NPB-GPU/CUDA/ $REPO/GPU_benchmark_binaries/
bash $REPO/GPU_benchmark_binaries/copy_idle.sh 2 $REPO/GPU_benchmark_binaries/
```
A list of folder should be created in the `GPU_benchmark_binaries/` folder for each GPU. Each folder should contain the binary code of each benchmark application in addition to the `idle.sh` script.

- Create a result directory for your set of exeriments

```
mkdir $REPO/results/test/
```

### Start experiments
The script `code/start_exp.py` start the experiments. Here is a list of its arguments:

- git_repo: Path to this git repo.
- benchmark_binary_dir: Path to the directory containing the benchmark binaries.
- result_folder: Path to the folder to save the results in.
- energy_scope_folder: Path to energy scope folder.
- repetitions: Number of repetitions.
- gpu_range: Number of GPU to use.
- sleep_before
- sleep_after
- NoTool: Launch the benchmarks without tools.
- ExperimentImpactTracker: Whether to test ExperimentImpactTracker or not.
- PyJoules: Whether to test PyJoules or not.
- EnergyScope: Whether to test EnergyScope or not.
- CarbonTrackerTool: Whether to test CarbonTrackerTool or not.
- CodeCarbon: Whether to test CodeCarbon or not.
- monitor_one_process: Whether to test the tool on one process or all processes.
- benchmark_id: If only one benchmark, which one. 
    - The id corresponds to the index in the list [('idle', 'sh'), ("mg", "D"), ("lu", "D"), ("ep", "E")] for the GPU benchmarks
    - and in the list [('idle', 'sh'), ("mg", "D"), ("lu", "C"), ("ep", "D")] for the CPU benchmarks.
- CPU: Whether to launch the CPU benchmarks instead of the GPU benchmarks, False by default.

For example, to start one experiment with 2 GPUs on Code Carbon on the EP GPU NAS benchmark:
```
python3.7 $REPO/code/start_exp.py --git_repo $REPO/ --result_folder $REPO/results/test/ --CodeCarbon --repetitions 1 --gpu_range 2 --benchmark_id 3
```

The `automation_scripts` folder contains examples of how the script can be used to fully automate the experimentations.    
Helper functions and classes can be found in the folder `code/utils/`.   

`code/start_exp.py` creates Benchmark objects and an Experiment object as defined in `code/utils/experiments.py`.
The Benchmark objects create the Bash script to be executed and the Experiment object is in charge of retrieving information on the execution environment, turning the tool on while executing the benchmarks and processing the results.
   
## Result data description
Each experiment is assigned a random identificator.   
A folder per experiment is created in the result folder you provided to the script (here in `test/`), named `ID_#`. They contain both the data as reported by the studied tool (named `ID_#_#`) and the bash script that was used to execute the benchmark (`gpu#`)). For more details on the resulting data, please refer to the documentation of the corresponding tool.   
In the result folder, you will also find a csv file called `experiment_table.csv` which summarises the results and associates each experiment with meta data describing the environment of the experiments.   

## Process results
Preprocessing is needed to use the resulting data. `code/utils/process_results.py` will do it for you. It merges the resulting files so that they can be easily processed and synchronises them with the `experiment_table.csv` table. The power meter data is retrieved from the Grid'5000 plateform. The energy results are converted to the same unit. The total energy of executing from tools only reporting power are computed. Simple data cleaning steps are also performed. Please check the script for more details.   
The output is a single dataframe containing all results. A separate dataframe will contain the timeseries of the power used by Energy Scope and the Wattmeters.   
Example of how to use this script: 

```
python utils/process_results.py --local_git_dir $REPO/ --distant_directory $REPO/ --result_folder $REPO/results/test/
# OR
python utils/process_results.py --local_git_dir /home/YOURLOGIN/an-experimental-comparison-of-software-based-power-meters/ --distant_directory /root/comparison/  --result_folder /home/YOURLOGIN/an-experimental-comparison-of-software-based-power-meters /results/test/
```
The two first argument are usefull when the analysis is done in a different machine.   
`wattmeter.ipynb` can be used to retrieve the wattmeter data separately.     

## Analyse results
The analysis notebooks can be found in `code/analysis`.
    
We focused on:
- Offset between the wattmeters and the tools (`Offset.ipynb`)
- Timseries comparisons (`Timeseries.ipynb`)
- Comparison in energy (`Energy.ipynb`)
- Overhead in energy of the softwares (`Overhead.ipynb`)
- Computation of energy through Energy calculators (`Energy calculators.ipynb`)

# Add a tool in the framework
To include another tool to the comparison, you need to modify the following files:
1) `code/utils/tools.py` contains objects describing each tool, as child of the class PowerTool. You need to create a new object e.g. TestTool and overwrite the methods `self.start_tool` and `self.process_power_results`. 
    - The PowerTool `self.start_tool` method is a template that you need to complete with the command to start and stop the software-based power meter where it is indicated.
    - `self.process_power_results` should return a dictionnary containing the reports of the tool e.g.  `{'testtool_energy(joules)': 10, testtool_duration(seconds): 50}`. It will automatically be concatenated to the result table and saved in `experiment_table.csv`.
2) `start_exp.py` calls the PowerTool child previously defined. First, you need to add your tool to the list of arguments:
```
    parser.add_argument('--TestTool', 
                        help='Whether to test TestTool or not.', 
                        action='store_true', default=False)
```
Add your tool to the two lists `to_test`, `power_tools`.

# Contact
Please contact me at mathilde.jay@univ-grenoble-alpes.fr.

# Acknowledgement
Experiments are carried out using the Grid’5000 testbed, supported by a scientific interest group hosted by Inria and including CNRS, RENATER and several Universities as well as other organizations (see https://www.grid5000.fr).

# License
This work is licensed under a Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) License.
You should have received a copy of the license along with this work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
