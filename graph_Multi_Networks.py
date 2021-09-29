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

from skrf import Network

nw2 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\ANT1351H_P1.s1p')
nw3 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\ANT1351H_Covered_P1.s1p')
nw4 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_1_P1.s1p')
nw5 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_2_P1.s1p')
nw6 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_3_P1.s1p')
nw7 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_4_P1.s1p')

nw8 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\ANT1351H_P2.s1p')
nw9 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\ANT1351H_Covered_P2.s1p')
nw10 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_1_P2.s1p')
nw11 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_2_P2.s1p')
nw12 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_3_P2.s1p')
nw13 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\Covered_4_P2.s1p')


serial_num_2 = "ANT1351H_P2"
plt.title(f"{serial_num_2} covered vs. Uncovered")

plot2 = nw8.plot_s_db(m=0,n=0, label='Uncovered')
plot2 = nw9.plot_s_db(m=0,n=0, label='Covered_1')
plot2 = nw10.plot_s_db(m=0,n=0, label='Covered_2')
plot2 = nw11.plot_s_db(m=0,n=0, label='Covered_3')
plot2 = nw12.plot_s_db(m=0,n=0, label='Covered_4')
plot2 = nw13.plot_s_db(m=0,n=0, label='Covered_5')
plt.savefig(f"C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Smith_Charts\\{serial_num_2}multi_comparison.jpg")
plt.show()