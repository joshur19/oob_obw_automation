"""
file: base instrument class from which specific instrument classes are derived
author: josh
last updated: 26/06/2024
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

    def connect(self): 
        try:
            self.instrument = self.rm.open_resource(self.visa_address)
            self.instrument.write_termination = '\n'
            self.instrument.read_termination = '\n'
            return True
        except:
            tags.log('Instrument', 'Error connecting to instrument.')
            return False

    def initialize(self):
        if self.connect():
            id = self.instrument.query('*IDN?')
            tags.log('Instrument', f"Succesfully connected to instrument {id}")
            self.disconnect()
        else:
            tags.log('Instrument', 'Unable to connect to instrument.')

    def disconnect(self):
        self.instrument.close()