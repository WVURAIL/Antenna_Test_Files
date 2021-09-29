############################################
#@Purpose:Measure_S11.py: A script designed to test Chime feed antennas for S11. The script walks you through
#testing of antennas, saves files and graphs locally then uploads touchstone files to github.
#
#@Authors: Pranav Sanghavani and Joseph Shepard
#
#@Date: 9/13/2021
###############################################

import numpy as np
import os 
import skrf as rf
import matplotlib.pyplot as plt
import time
import pyvisa as visa
import csv
import time
import base64
from github import Github
from github import InputGitTreeElement


def set_freq_lims(start, stop):
            VNA.write('SENSe:FREQuency:STARt ' + str(start))
            VNA.write('SENSe:FREQuency:STOp ' + str(stop))
            """
                Set frequency limits of measurement
                Commands:
                http://na.support.keysight.com/pna/help/latest/Programming/GP-IB_Command_Finder/Sense/Frequency.htm
            """
def check_power_mode():
    print(f"Current Output power is{VNA.query('SOURce:POWer:ALC:MODE?')}")
    """
    CHECK POWER MODE
    """
def set_power_mode(output_power, nominal_power = -15):
    print(f"Setting output power to {output_power}")
    VNA.write('SOURce:POWer:ALC:MODE ' + str(output_power))
    check_power_mode()
    if str(output_power) == "MAN":
        print(f"Setting nominal power level {nominal_power}")
# define a 2x2 s-matrix at a given frequency
def measure_s_parameter(measurement, output_power,serial_num, start_freq, stop_freq):
    print("setting frequency limits")
    set_freq_lims(start_freq,stop_freq)
    check_power_mode()
    set_power_mode(output_power)
    print(f"Measuring {measurement} with Output mode {output_power}")
    VNA.write(':CALCulate:PARameter1:DEFine ' + measurement)
    # http://na.support.keysight.com/pna/help/latest/Programming/GP-IB_Command_Finder/Calculate/Parameter.htm COMMANDS FOR MEASUREMENT PARAMETERS
    VNA.write(':CALCulate:SELected:FORMat MLOGarithmic')
    # MLINear, MLOGarithmic, PHASe, UPHase 'Unwrapped phase, IMAGinary,REAL
    # POLar SMITh, SADMittance 'Smith Admittance, SWR, GDELay 'Group Delay
    # http://na.support.keysight.com/pna/help/latest/Programming/GP-IB_Command_Finder/Calculate/Format_Calc.htm
    time.sleep(1)
    VNA.write(':DISPlay:WINDow:TRACe:Y:SCALe:AUTO')# scaling plot on the VNA screen
    #### OTHER VNA COMMANDS THAT CONTROL THE SCREEN
    # http://na.support.keysight.com/pna/help/latest/Programming/GP-IB_Command_Finder/Display.htm#yauto
    ##########
    data = VNA.query('CALCulate:DATA:FDaTa?')
    ### http://na.support.keysight.com/pna/help/latest/Programming/GP-IB_Command_Finder/Calculate/Data.htm # COMMANDS TO SAVE DATA
    data = data_real = np.asarray(data.split(',')[:-1] + [data.split(',')[-1][:-1]])   
    data = np.array([float(i.lower()) for i in data])

    plt.figure()
    plt.plot(np.linspace(start_freq/1e6,stop_freq/1e6,data.shape[-1]),data)
    plt.xlabel("MHz")
    plt.ylabel("dBm")
    plt.title(f"{measurement}_{serial_num}")
    print(f"DONE measuring {measurement}")
    plt.savefig(f"C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\LNA\\{measurement}_{serial_num}.png")
    VNA.write(':CALCulate:SELected:FORMat REAL')
    time.sleep(1)
    data_real = VNA.query('CALCulate:DATA:FDaTa?')
    data_real = np.asarray(data_real.split(',')[:-1] + [data_real.split(',')[-1][:-1]])   
    VNA.write(':CALCulate:SELected:FORMat IMAG')
    time.sleep(1)
    data_imag = VNA.query('CALCulate:DATA:FDaTa?')
    data_imag = np.asarray(data_imag.split(',')[:-1] + [data_imag.split(',')[-1][:-1]])   
    data_raw = np.array([float(i[0].lower())+float(i[1].lower())*1j  for i in zip(data_real,data_imag)])
    plt.show()
    return data, data_raw

i="1"
while i == "1":
    con = input("Please Connect the VNA and ensure it is powered on! Once connected press y: ")
    if con == 'y':
        ##############################################################################
        # load visa library 
        rm=visa.ResourceManager('C:\\Windows\\System32\\visa64.dll') # windows
        # TODO linux
        # https://edadocs.software.keysight.com/kkbopen/linux-io-libraries-faq-589309025.html
        # https://www.keysight.com/us/en/lib/software-detail/computer-software/io-libraries-suite-downloads-2175637.html click linux 
        # 
        print(rm.list_resources())# find connected instrument and get instrument address
        instrument_address = rm.list_resources()
        VNA = rm.open_resource(instrument_address[0])# load  instrument object
        VNA.write('*IDN?')
        IDN=VNA.read()
        print(IDN)
        VNA.timeout = 10000
        # # select NA mode
        # ```
        # Relevant Modes
        #  ALL
        #  
        # Parameters
        #   
        #  
        # <string>
        #  Operating Mode. Case-sensitive. Choose from the modes that are installed on your FieldFox:
        # 
        # "CAT"
        # "IQ"
        # "NA"
        # "SA"
        # "Power Meter"
        # "VVM"
        # "Pulse Measurements"
        # "ERTA"
        #  
        # Examples
        #  INST "NA";*OPC?
        #  ```
        # 
        # common commands: http://na.support.keysight.com/pna/help/latest/Programming/GP-IB_Command_Finder/Common_Commands.htm
        print(VNA.query('INSTrument:CATalog?'))# print available modes of intrsument
      
        VNA.write('INST "NA";*OPC?')# set in network analyzer mode 
        
        if VNA.read()[0] == '1':
            print("Successfully set NA mode")



       
       
        # ```
        # For NA Mode:
        # Reverse measurements are available ONLY with full S-parameter option.
        # 
        # S11 - Forward reflection measurement
        # S21 - Forward transmission measurement
        # S12 - Reverse transmission
        # S22 - Reverse reflection
        # A - A receiver measurement
        # B - B receiver measurement
        # R1 - Port 1 reference receiver measurement
        # R2 - Port 2 reference receiver measurement
        # ```
        ##########################################################################
        ## set start and stop freq

        start_freq = 1e7
        stop_freq = 2e9
        set_freq_lims(start_freq,stop_freq)
        ##########################################################################

        serial_num= input("Please Enter LNA Serial Number: ")
        z = input("Please Connect VNA to LNA! Press Enter when Finished: ")
        serial_num_1=serial_num
        
        output_power="LOW"
        m="S11"
        S11, S11_raw = measure_s_parameter(m, output_power,serial_num_1, start_freq=start_freq, stop_freq=stop_freq)
        m="S12"
        S12, S12_raw = measure_s_parameter(m, output_power,serial_num_1, start_freq=start_freq, stop_freq=stop_freq)
        m="S21"
        S21, S21_raw = measure_s_parameter(m, output_power,serial_num_1, start_freq=start_freq, stop_freq=stop_freq)
        m="S22"
        S22, S22_raw = measure_s_parameter(m, output_power,serial_num_1, start_freq=start_freq, stop_freq=stop_freq)
       
        f = np.linspace(start_freq,stop_freq,S11_raw.shape[-1])
        nw2 = rf.Network(name=f"{serial_num_1}_S11",s=S11_raw,frequency=f, z0=50)
        nw3 = rf.Network(name=f"{serial_num_1}_S12",s=S12_raw,frequency=f, z0=50)
        nw4 = rf.Network(name=f"{serial_num_1}_S21",s=S21_raw,frequency=f, z0=50)
        nw5 = rf.Network(name=f"{serial_num_1}_S22",s=S22_raw,frequency=f, z0=50)

        print(nw2)

        nw2.write_touchstone(filename = f"{serial_num_1}_S11",dir= 'C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\LNA')
        nw3.write_touchstone(filename = f"{serial_num_1}_S12",dir= 'C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\LNA')
        nw4.write_touchstone(filename = f"{serial_num_1}_S21",dir= 'C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\LNA')
        nw5.write_touchstone(filename = f"{serial_num_1}_S22",dir= 'C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\LNA')
        s = np.zeros((len(f), 2, 2))
        s[:,0,0] = S11_raw
        s[:,0,1] = S12_raw
        s[:,1,0] = S21_raw
        s[:,1,1] = S22_raw
        nw6 = rf.Network(name=f"{serial_num_1}_S22",s=s,frequency=f, z0=50)
        serial_num_2 = "Bandura_LNA"
        nw6.write_touchstone(filename = f"{serial_num_1}",dir= 'C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\LNA')
        plt.title(f"{serial_num_2} S Parameters")

        plot2 = nw2.plot_s_db(m=0,n=0, label='S11')
        plot2 = nw3.plot_s_db(m=0,n=0, label='S12')
        plot2 = nw4.plot_s_db(m=0,n=0, label='S21')
        plot2 = nw5.plot_s_db(m=0,n=0, label='S22')
        plt.savefig(f"C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\LNA\\{serial_num_2}multi_comparison.jpg")
        plt.show()
        
        
    i= input("Finsihed? Press 0. Test again? Press 1 : ")
    print("Thanks for testing with us!")
