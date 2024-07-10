"""
file: contains constants referenced in other parts of program, constant values and such
author: rueck.joshua@gmail.com
last updated: 25/06/2024
"""

import datetime

sps_addr = 'GPIB0::6::INSTR' 
ars_addr = 'GPIB0::3::INSTR'
fsv_addr = 'TCPIP0::172.16.111.222::inst0::INSTR' 

inputfield_width = 80

def log(tag, message):
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} -- LOG -- [{tag}] {message}')