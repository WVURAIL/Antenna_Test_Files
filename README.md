# Testing Procdures
Step 1- 
Before beginning a testing session first calibrate your Feildfox VNA if need.
This is very simple and can be done before taking the testing setup outdoors. 
You will need: 
-The VNA -A cable 3ft silver clear 
-a 50Ohm Dummy Load Press the CAL button on the vna Mechanical Cal ECal and follow the on-screen instructions for the QUICK cal setting do only S11 port 1. Using the dummyload when it asks for a load to be connected.
•	Start frequency 100 MHz
•	Stop frequency 1 GHz
Step 2-
Set up the testing apparatus outside. Ensure that the reflector is level with the sky and that you are away from any sources of interference. The site most used is the WVU is the grassy area between the AERB and the PRT. From here it is as easy as attaching an antenna with 1/2 screws and running the test script.
Step 3- Running the script is very simple: First open the CMD. Then type: CD Desktop CD Enigma_Testing_2022 CD Antenna_Test_Files Python Measure_S11.py

    
![image](https://user-images.githubusercontent.com/43184800/209993202-c515da83-4605-4401-8a7d-9aad3b6d5966.png)


    
Then follow the on screen instructions to aqquire test data for the antennas. 
The serial number can be found on the antenna label. 
NOTE: When testing antennas make sure to connect the dummy load to the unused port.

Step 5 -
  Once you have finished testing make sure to upload your touchstone files to this github and share al of your files in the microsoft teams. 
