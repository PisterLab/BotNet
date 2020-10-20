For Linux:

-unzip the source code:

    unzip swarm-world.zip


-install the following python packages:

    1. sudo apt-get install python3.6 python3-pip 

    2. sudo pip3 install numpy

    3. sudo pip3 install pandas

    4. sudo pip3 install PyOpenGL
    
    5. sudo pip3 install Pillow
    
    6. sudo pip3 install PyQt5
    
    7. sudo pip3 install opencv-python
    
for older Systems (e.g. Ubuntu 14.04) install the PyQt5 version 5.10.1

    6. sudo pip3 install PyQt5==5.10.1

- install Gnuplot:

    sudo apt-get install gnuplot-x11

- go to the main folder of the SNS-Folder and start it with:

    python3.6 swarm-sim.py


For development the IDE Pycharm is recommended:

https://www.jetbrains.com/help/pycharm/install-and-set-up-pycharm.html


For Windows/Linux/MacOs:
- unzip souce code
- install python3.6
- install pycharm
- run pycharm
- open swarm-world as a project
- Open File->Settings-"Project-Interpreter"
- Chose python3.6 as an interpreter
- Chose the plus sign and install:
    1. pip3
    2. numpy
    3. pandas
    4. PyOpenGL
    5. Pillow
    6. PyQt5 (in version 5.10.1 for older Systems like Ubuntu 14.04)
    7. opencv-python
- press Okey
- wait until everything is installed
- chose Run->swarm-sim.py
    - If it gives an error that it cannot find the interpretetor
       Open Run->"Edit Configuration" Chose the python3.6 as an interpretetor