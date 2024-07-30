"""
file: base instrument class from which specific instrument classes are derived
author: rueck.joshua@gmail.com
last updated: 02/07/2024
"""

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
            self.instrument.write_termination = '\n'
            self.instrument.read_termination = '\n'
            return True
        except:
            tags.log('Instrument', f'Connection: Error connecting to instrument {name}')
            return False

    def initialize(self, name = ""):
        if self.connect(name):
            id = self.instrument.query('*IDN?')
            tags.log('Instrument', f"Succesfully connected to instrument {id.strip()}")
            self.instrument.write('*RST')
            self.disconnect()
        else:
            tags.log('Instrument', f'Initialization: Unable to connect to instrument {name}')

    def disconnect(self):
        self.instrument.close()