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

nw2 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\ANT1351H_P2.s1p')
nw3 = Network('C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\Touchstone_Files\\ANT1350H_P2.s1p')


serial_num_2 = "S11_ANT1351H_P2 vs S11_ANT1350H_P2"
plt.title(f"{serial_num_2} (Single Location [L] /Multiple Antenna [A]")

plot2 = nw2.plot_s_db(m=0,n=0, label='L1_A1')
plot2 = nw3.plot_s_db(m=0,n=0, label='L1_A2')



plt.savefig(f"C:\\Users\\RadioLab\\Desktop\\Enigma_Testing\\c\\{serial_num_2}_Cover_comparison.jpg")
plt.show()