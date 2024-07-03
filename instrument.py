"""
file: base instrument class from which specific instrument classes are derived
author: josh
last updated: 02/07/2024
"""

# idea: create a class "instrument" that respresents a general t&m instrument with all its basic functions
# maybe implement classes that represent categories of devices like signal generator, signal analyzer, network analyzer, etc.
# instantiate the common TÜV instruments with appropriate SCPI commands and then reference those objects in code depending on IDN query

import pyvisa
import tags

class BaseInstrument:

    def __init__(self, visa_address):
        self.rm = pyvisa.ResourceManager()
        self.visa_address = visa_address
        self.instrument = None

    def connect(self, name = ""): 
        try:
            self.instrument = self.rm.open_resource(self.visa_address)
            return True
        except:
            tags.log('Instrument', f'Error connecting to instrument. {name}')
            return False

    def initialize(self, name = ""):
        if self.connect():
            id = self.instrument.query('*IDN?')
            tags.log('Instrument', f"Succesfully connected to instrument {id.strip()}")
            self.instrument.write('*RST')
            self.disconnect()
        else:
            tags.log('Instrument', f'Unable to connect to instrument. {name}')

    def disconnect(self):
        self.instrument.close()