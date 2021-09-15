# Testing Procdures
Step 1-
  Before beggining a testing session first calibrate your Feildfox VNA. This is very simple and can be done before taking the testing setup outdoors. 
  You will need:
  -The VNA
  -A cable
  -a 50Ohm Dummy Load
  Press the CAL button on the vna and follow the on screen instructions for the QUICK cal setting. Using the dummyload when it asks for a load to be connected. 
  
Step 2-
  Set up the testing apperatus outside. Ensure that the reflector is level with the sky and that you are away from any sources of interference. THe site most commonly used is the   WVU is the grassy area between the AERB and the PRT. From here it is as easy as attatching an antenna with 1/2 screws and running the test script. 
  
Step 3- 
  Running the script is very simple: First open the CMD. 
  Then type: 
    CD Desktop
    CD Enigma_Testing
    Activate RAILVNA
    Python Measure_S11.py
    
Then follow the on screen instructions to aqquire test data for the antennas. 
The serial number can be found on the antenna label. 
NOTE: When testing antennas make sure to connect the dummy load to the unused port.

Step 5 -
  Once you have finished testing make sure to upload your touchstone files to this github and share al of your files in the microsoft teams. 
