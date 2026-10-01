Antenna Testing Procedures
Kholoud Khairy 2022
Step 1
- Before beginning a testing session first calibrate your Feildfox VNA if need. This is very simple and can be done before taking the testing setup outdoors. 
***Before starting this procedure, ensure a double sided, co-axial terminal connector and a 50 Ohm Load (resistor) are available.  

You will need: 
	Power On Keysight Vector Network Analyzer model N9923A 
	Ensure Port 1 and Port 2 cables are of equal length cable 3ft silver clear
	a 50Ohm Dummy Load Press the CAL button on the vna Mechanical Cal ECal and follow the on-screen instructions for the QUICK cal setting do only S11 port
	Using the dummyload when it asks for a load to be connected.
•	Start frequency 100 MHz
•	Stop frequency 1 GHz
Step 2
	Set up the testing apparatus outside. 
	Ensure that the reflector is level with the sky and that you are away from any sources of interference. 
	The site most used is the WVU is the grassy area between the AERB and the PRT. From here it is as easy as attaching an antenna with 1/2 screws and running the test script.
Step 3
	Running the script is very simple: 
	First open the CMD. 
	Then type: CD Desktop CD Enigma_Testing_2022
	CD Antenna_Test_Files 
	Python Measure_S11.py

 
Then follow the on-screen instructions to acquire test data for the antennas. The serial number can be found on the antenna label. NOTE: When testing antennas make sure to connect the dummy load to the unused port.
Step 4 
	Once you have finished testing make sure to upload your touchstone files to this GitHub and share al of your files in the Microsoft teams.

