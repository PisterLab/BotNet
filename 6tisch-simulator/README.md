# The 6TiSCH Simulator

Branch    | Build Status
--------- | -------------
`master`  | [![Build Status](https://openwsn-builder.paris.inria.fr/buildStatus/icon?job=6TiSCH%20Simulator/master)](https://openwsn-builder.paris.inria.fr/job/6TiSCH%20Simulator/job/master/)
`develop` | [![Build Status](https://openwsn-builder.paris.inria.fr/buildStatus/icon?job=6TiSCH%20Simulator/develop)](https://openwsn-builder.paris.inria.fr/job/6TiSCH%20Simulator/job/develop/)

Core Developers:

* Yasuyuki Tanaka (yasuyuki.tanaka@inria.fr)
* Keoma Brun-Laguna (keoma.brun@inria.fr)
* Mališa Vučinić (malisa.vucinic@inria.fr)
* Thomas Watteyne (thomas.watteyne@inria.fr)

Contributers:

* Kazushi Muraoka (k-muraoka@eecs.berkeley.edu)
* Nicola Accettura (nicola.accettura@eecs.berkeley.edu)
* Xavier Vilajosana (xvilajosana@eecs.berkeley.edu)
* Esteban Municio (esteban.municio@uantwerpen.be)
* Glenn Daneels (glenn.daneels@uantwerpen.be)

## Publishing

If you publish an academic paper using the results of the 6TiSCH Simulator, please cite:

E. Municio, G. Daneels, M. Vucinic, S. Latre, J. Famaey, Y. Tanaka, K. Brun, K. Muraoka, X. Vilajosana, and T. Watteyne, "Simulating 6TiSCH Networks", Wiley Transactions on Emerging Telecommunications (ETT), 2019; 30:e3494. https://doi.org/10.1002/ett.3494

## Scope

6TiSCH is an IETF standardization working group that defines a complete protocol stack for ultra reliable ultra low-power wireless mesh networks.
This simulator implements the 6TiSCH protocol stack, exactly as it is standardized.
It allows you to measure the performance of a 6TiSCH network under different conditions.

Simulated protocol stack

|                                                                                                              |                                             |
|--------------------------------------------------------------------------------------------------------------|---------------------------------------------|
| [RFC6550](https://tools.ietf.org/html/rfc6550), [RFC6552](https://tools.ietf.org/html/rfc6552)               | RPL, non-storing mode, OF0                  |
| [RFC6206](https://tools.ietf.org/html/rfc6206)                                                               | Trickle Algorithm                           |
| [draft-ietf-6lo-minimal-fragment-07](https://tools.ietf.org/html/draft-ietf-6lo-minimal-fragment-07)         | 6LoWPAN Fragment Forwarding                 |
| [RFC6282](https://tools.ietf.org/html/rfc6282), [RFC4944](https://tools.ietf.org/html/rfc4944)               | 6LoWPAN Fragmentation                       |
| [draft-ietf-6tisch-msf-10](https://tools.ietf.org/html/draft-ietf-6tisch-msf-10)                             | 6TiSCH Minimal Scheduling Function (MSF)    |
| [draft-ietf-6tisch-minimal-security-15](https://tools.ietf.org/html/draft-ietf-6tisch-minimal-security-15)   | Constrained Join Protocol (CoJP) for 6TiSCH |
| [RFC8480](https://tools.ietf.org/html/rfc8480)                                                               | 6TiSCH 6top Protocol (6P)                   |
| [RFC8180](https://tools.ietf.org/html/rfc8180)                                                               | Minimal 6TiSCH Configuration                |
| [IEEE802.15.4-2015](https://ieeexplore.ieee.org/document/7460875/)                                           | IEEE802.15.4 TSCH                           |

* connectivity models
    * Pister-hack
    * k7: trace-based connectivity
* miscellaneous
    * Energy Consumption model taken from
        * [A Realistic Energy Consumption Model for TSCH Networks](http://ieeexplore.ieee.org/xpl/login.jsp?tp=&arnumber=6627960&url=http%3A%2F%2Fieeexplore.ieee.org%2Fiel7%2F7361%2F4427201%2F06627960.pdf%3Farnumber%3D6627960). Xavier Vilajosana, Qin Wang, Fabien Chraim, Thomas Watteyne, Tengfei Chang, Kris Pister. IEEE Sensors, Vol. 14, No. 2, February 2014.

## Installation

* Install Python 2.7 (or Python 3)
* Clone or download this repository
* To plot the graphs, you need Matplotlib and scipy. On Windows, Anaconda (http://continuum.io/downloads) is a good one-stop-shop.

While 6TiSCH Simulator has been tested with Python 2.7, it should work with Python 3 as well.

## Getting Started

1. Download the code:
   ```
   $ git clone https://bitbucket.org/6tisch/simulator.git
   ```
1. Install the Python dependencies:
   `cd simulator` and `pip install -r requirements.txt`
1. Execute `runSim.py` or start the GUI:
    * runSim.py
       ```
       $ cd bin
       $ python runSim.py
       ```
        * a new directory having the timestamp value as its name is created under
          `bin/simData/` (e.g., `bin/simData/20181203-161254-775`)
        * raw output data and raw charts are stored in the newly created directory
    * GUI
       ```
       $ gui/backend/start
       Starting the backend server on 127.0.0.1:8080
       ```
        * access http://127.0.0.1:8080 with a web browser
        * raw output data are stored under `gui/simData`
        * charts are NOT generated when the simulator is run via GUI

1. Take a look at `bin/config.json` to see the configuration of the simulations you just ran.

The simulator can be run on a cluster system. Here is an example for a cluster built with OAR and Conda:

1. Edit `config.json`
    * Set `numCPUs` with `-1` (use all the available CPUs/cores) or a specific number of CPUs to be used
    * Set `log_directory_name` with `"hostname"`
1. Create a shell script, `runSim.sh`, having the following lines:

        #!/bin/sh
        #OAR -l /nodes=1
        source activate py27
        python runSim.py

1. Make the shell script file executable:
   ```
   $ chmod +x runSim.sh
   ```
1. Submit a task for your simulation (in this case, 10 separate simulation jobs are submitted):
   ```
   $ oarsub --array 10  -S "./runSim.sh"
   ```
1. After all the jobs finish, you'll have 10 log directories under `simData`, each directory name of which is the host name where a job is executed
1. Merge the resulting log files into a single log directory:
   ```
   $ python mergeLogs.py
   ```

If you want to avoid using a specific host, use `-p` option with `oarsub`:
```
$ oarsub -p "not host like 'node063'" --array 10 -S "./runSim.sh"
```
In this case, `node063` won't be selected for submitted jobs.

The following commands could be useful to manage your jobs:

* `$ oarstat`: show all the current jobs
* `$ oarstat -u`: show *your* jobs
* `$ oarstat -u -f`: show details of your jobs
* `$ oardel 87132`: delete a job whose job ID is 87132
* `$ oardel --array 87132`: delete all the jobs whose array ID is 87132

You can find your job IDs and array ID in `oarsub` outputs:

```
$ oarsub --array 4 -S "runSim.sh"
...
OAR_JOB_ID=87132
OAR_JOB_ID=87133
OAR_JOB_ID=87134
OAR_JOB_ID=87135
OAR_ARRAY_ID=87132
```

## Code Organization

* `SimEngine/`: the simulator
    * `Connectivity.py`: Simulates wireless connectivity.
    * `SimConfig.py`: The overall configuration of running a simulation campaign.
    * `SimEngine.py`: Event-driven simulation engine at the core of this simulator.
    * `SimLog.py`: Used to save the simulation logs.
    * `SimSettings.py`: The settings of a single simulation, part of a simulation campaign.
    * `Mote/`: Models a 6TiSCH mote running the different standards listed above.
* `bin/`: the scripts for you to run
* `gui/`: files for GUI (see "GUI" section for further information)
* `tests/`: the unit tests, run using `pytest`
* `traces/`: example `k7` connectivity traces

## Configuration

`runSim.py` reads `config.json` in the current working directory.
You can specify a specific `config.json` location with `--config` option.

```
python runSim.py --config=example.json
```

The `config` parameter can contain:

* the name of the configuration file in the current directory, e.g. `example.json`
* a path to a configuration file on the computer running the simulation, e.g. `c:\simulator\example.json`
* a URL of a configuration file somewhere on the Internet, e.g. `https://www.example.com/example.json`

### base format of the configuration file

```
{
    "version":               0,
    "execution": {
        "numCPUs":           1,
        "numRuns":           100
    },
    "settings": {
        "combination": {
            ...
        },
        "regular": {
            ...
        }
    },
    "logging":               "all",
    "log_directory_name":    "startTime",
    "post": [
        "python compute_kpis.py",
        "python plot.py"
    ]
}
```

* the configuration file is a valid JSON file
* `version` is the version of the configuration file format; only 0 for now.
* `execution` specifies the simulator's execution
    * `numCPUs` is the number of CPUs (CPU cores) to be used; `-1` means "all available cores"
    * `numRuns` is the number of runs per simulation parameter combination
* `settings` contains all the settings for running the simulation.
    * `combination` specifies variations of parameters
    * `regular` specifies the set of simulator parameters commonly used in a series of simulations
* `logging` specifies what kinds of logs are recorded; `"all"` or a list of log types
* `log_directory_name` specifies how sub-directories for log data are named: `"startTime"` or `"hostname"`
* `post` lists the post-processing commands to run after the end of the simulation.

See `bin/config.json` to find  what parameters should be set and how they are configured.

### more on connectivity models

#### using a *k7* connectivity model

`k7` is a popular format for connectivity traces.
You can run the simulator using connectivity traces in your K7 file instead of using the propagation model.

```
{
    ...
    "settings": {
        "conn_class": "K7"
        "conn_trace": "../traces/grenoble.k7.gz"
    },
    ...
}
```

* `conn_class` should be set with `"K7"`
* `conn_trace` should be set with your K7 file path

Requirements:

* the number of nodes in the simulation must match the number of nodes in the trace file.
* the trace duration should be longer that 1 hour has the first hour is used for initialization

### more on applications

`AppPeriodic` and `AppBurst` are available.

### configuration file format validation

The format of the configuration file you pass is validated before starting the simulation. If your configuration file doesn't comply with the format, an `ConfigfileFormatException` is raised, containing a description of the format violation. The simulation is then not started.

## GUI / 6TiSCH Simulator WebApp
The repository of 6TiSCH Simulator has only artifacts of 6TiSCH Simulator WebApp.

Full source code of the webapp is hosted at [https://github.com/yatch/6tisch-simulator-webapp/](https://github.com/yatch/6tisch-simulator-webapp/).
[WEBAPP_COMMIT_INFO.txt](./gui/WEBAPP_COMMIT_INFO.txt) has the commit (version) of the webapp code that generates the files under `gui`.

![Screenshot of GUI](figs/gui.png)

## About 6TiSCH

| what         | where                                                                                                                                  |
|--------------|----------------------------------------------------------------------------------------------------------------------------------------|
| charter      | [http://tools.ietf.org/wg/6tisch/charters](http://tools.ietf.org/wg/6tisch/charters)                                                   |
| data tracker | [http://tools.ietf.org/wg/6tisch/](http://tools.ietf.org/wg/6tisch/)                                                                   |
| mailing list | [http://www.ietf.org/mail-archive/web/6tisch/current/maillist.html](http://www.ietf.org/mail-archive/web/6tisch/current/maillist.html) |
| source       | [https://bitbucket.org/6tisch/](https://bitbucket.org/6tisch/)                                                                         |
