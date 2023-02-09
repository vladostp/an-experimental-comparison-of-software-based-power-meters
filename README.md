# Introduction
Authors: Mathilde Jay, Vladimir Ostapenco

The repository is divided between the CPU benchmarks and the GPU benchmarks. Mathilde Jay developed the framework for the GPU benchmarks while Vladimir Ostapenco was in charge of the CPU benchmark experiments. More details on the functionality and instructions of both parts can be found in the corresponding folders.

# Description
The objective of this project is to experimentally compare software-based power meters. This work automates measuring benchmarks' power and energy consumption with various software-based power meters. It automatically retrieves and processes the results and proposes notebooks to visualize them and study metrics.

## Language
The project is developed mainly in Python, for the collection of environment information, the management of the databases, and the process of the results. 
Scripts in Bash are used to compile and execute the benchmarks.

# Replicate experiments
## Request access to the Grid'5000 testbed
To get access to the testbed, one needs to ask for an account at: [https://www.grid5000.fr/w/Grid5000:Get_an_account](https://www.grid5000.fr/w/Grid5000:Get_an_account). 
Once you have access to the testbed, please follow the first steps described in the [Getting started](https://www.grid5000.fr/w/Getting_Started) tutorial.

## Compilation and execution environment
Our framework was tested on the Gemini cluster of the Grid'5000 testbed.
To start experimenting, please follow the steps described in [CPU_benchmarks](https://gitlab.inria.fr/majay/an-experimental-comparison-of-software-based-power-meters/-/tree/main/CPU_Benchmarks) and [GPU_Benchmarks](https://gitlab.inria.fr/majay/an-experimental-comparison-of-software-based-power-meters/-/tree/main/GPU_Benchmarks).

# Outputs
For each experiment, we gather environment description (duration, number of GPU/CPU, etc.) and energy measurement metrics as reported by selected tools and the power meters (BMC, OmegaWatt). The output of all experiments can be found in the result folders. Its structure is described in the respective readme-files in the Gitlab repository.

In the result folder can be found the data from ten experiments for each tool and benchmark we selected. Experiments were also conducted without a software-based power meter to study their overhead. Finally, the tools were launched on idle machines to study how they would react.

To compare the software-based power meters on the various benchmarks, we study the following metrics:
- Power profiles reported: We visualize the relative evolution of power as reported by the tools and the external power meters.
- Total energy consumed per benchmark: We study the differences between the tool reports.
- Correlation with the external power meter: We study the correlation between the values given by each tool and the values reported by the external power meter.
- Offset: We investigate the relationship between the power time series as reported by the external power meters and the tools. 
- Energy overhead: We compare the total energy consumed by the benchmarks (as reported by the external power meter) with and without the tools monitoring the executions.
- CPU overhead: We study the CPU overhead of PowerAPI and Scaphandre by running each solution with different sampling frequency configurations on an isolated CPU core and by tracking the utilization rate of that core.
- Consumption reported at the process level: We study how PowerAPI and Scaphandre estimate consumption at the application process level.
- Maximum sampling frequency supported by each solution.
- Maximum simultaneous processes supported by each solution.
- Total energy consumed by the project: We computed the total energy consumed by our experiments (test and production), from the power reported by the external power meter.

Each metric is associated with a notebook in the repository.

# Estimated time of all the compilation and run steps
Opening a Grid'5000 account can take a few hours as a manager of the testbed needs to verify the demand and grant access.
Reserving the node and building the environment can take up to ten minutes. 
The compilation steps last less than one second per benchmark application. 
The duration of the experiments corresponds to the duration of the given benchmark, with a slight time overhead due to the installation and configuration of the given measurement tool. 
Processing the outputs and visualizing the results requires less than a minute.

# Disclaimer
Energy Scope is not open source and not publicly available. Thus it is not provided and the experiments for Energy Scope are not reproducible at the moment.

# Acknowledgement
This research is partially supported by the FrugalCloud collaboration between Inria and OVHCloud.
Experiments are carried out using the Grid’5000 testbed, supported by a scientific interest group hosted by Inria and including CNRS, RENATER and several Universities as well as other organizations (see https://www.grid5000.fr).

# Contact
Please contact us at mathilde.jay@univ-grenoble-alpes.fr or at vladimir.ostapenco@inria.fr.

# License
This work is licensed under a Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0) License.
