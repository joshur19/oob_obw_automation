"""
file: derived instrument class for Spitzenberger Spies "power supply system"
author: rueck.joshua@gmail.com
last updated: 02/08/2024
"""

import instrument
import tags
from time import sleep

class SPS(instrument.BaseInstrument):

    def __init__(self, visa_address):
        super().__init__(visa_address)
        self.stop_flag = False

    # initialize system for direct voltage supply
    def initialize(self):
        if self.connect('SPS'):
            self.instrument.write('DCL')   # reset SyCore to default settings
            sleep(2)
            id = self.instrument.query('*IDN?')
            tags.log('Instrument', f"Succesfully connected to instrument {id.strip()}")
            self.disconnect()

        try:
            ars = self.rm.open_resource(tags.ars_addr)
            sleep(1)
            ars.write('SET_IMPEDANCE=OFF')
            sleep(1)
            ars.write('H_I_RANGE=8')        # configuration for ARS direct mode without harmonics/flicker
            sleep(1)
            ars.close()
            tags.log('SPS', 'Succesfully initialized ARS to direct mode.')
        except:
            tags.log('SPS', 'Initialization: Error initializing ARS to direct mode.')

    # set stop flag for interruption
    def stop_operation(self):
        self.stop_flag = True

    # check if stop flag has been set
    def check_stop(self):
        if self.stop_flag:
            raise InterruptedError('Measurement was stopped.')

    # reset
    def reset(self):
        if self.connect('SPS'):
            self.instrument.write('DCL')
            sleep(2)
            self.disconnect()

    # turn amp off
    def set_amp_off(self):
        if self.connect():
            self.instrument.write(f'OSC:AMP 1,0V')              # reset oscillator amplitude to 0V
            sleep(3)
            self.instrument.write('AMP:OUTPUT 0')               # turn amplifier output off
            sleep(2)

            self.disconnect()
            tags.log('SPS', 'Amplifier turned off.')

    # set voltage DC
    def set_voltage_dc(self, voltage):
        try:
            if self.connect():

                self.instrument.write('DCL')                        # reset instrument to default state
                sleep(2)

                range = self.determine_range(voltage)
                
                self.instrument.write(f'AMP:RANGE {range}')         # set appropriate amplifier range
                self.check_stop()
                sleep(3)
                self.instrument.write('AMP:MODE:DC')                # set amplifier to DC mode
                sleep(0.5)
                self.instrument.write('OSC:PAGE:FUNC 1,"DC"')       # set oscillator to DC mode (phase 1)
                sleep(1)
                self.instrument.write(f'OSC:AMP 1,{voltage}V')      # set oscillator amplitude to voltage (phase 1)
                self.check_stop()
                sleep(7)
                self.check_stop()
                self.instrument.write('AMP:OUTPUT 1')               # turn on amplifier output
                sleep(2)
                
                self.disconnect()
                tags.log('SPS', f'DC voltage set to {voltage}V')

                return True

        except InterruptedError:
            self.disconnect()
            tags.log('SPS', 'Measurement interrupted.')
            return False
    
    # change voltage DC without turning amp off
    def change_voltage_dc(self, voltage):
        if self.connect():
            self.instrument.write(f'OSC:AMP 1,{voltage}V')
            sleep(1)
            self.disconnect()
            tags.log('SPS', f'DC voltage adjusted to {voltage} V')
            return True
        return False

    # set voltage AC
    def set_voltage_ac(self, voltage, freq):
        try:
            if self.connect():

                self.instrument.write('DCL')                        # reset instrument to default state
                sleep(2)

                range = self.determine_range(voltage)

                self.instrument.write(f'AMP:RANGE {range}')         # set appropriate amplifier range
                self.check_stop()
                sleep(3)    
                self.instrument.write('AMP:MODE:AC')                # set amplifier to DC mode
                sleep(0.5)
                self.instrument.write(f'OSC:FREQ {freq}')           # set oscillator frequency
                sleep(0.5)
                self.instrument.write(f'OSC:AMP 1,{voltage}V')      # set oscillator amplitude to voltage (phase 1)
                self.check_stop()
                sleep(7)
                self.check_stop()
                self.instrument.write('AMP:OUTPUT 1')               # turn on amplifier output
                sleep(2)

                self.disconnect()
                tags.log('SPS', f'AC voltage set to {voltage}V at {freq}Hz')

                return True

        except InterruptedError:
            self.disconnect()
            tags.log('SPS', 'Measurement interrupted.')
            return False

    # change voltage AC without turning amp off  
    def change_voltage_ac(self, voltage):
        if self.connect():
            self.instrument.write(f'OSC:AMP 1,{voltage}V')
            sleep(1)
            self.disconnect()
            tags.log('SPS', f'AC voltage adjusted to {voltage} V')
            return True
        return False

    # helper function for range selection
    def determine_range(self, voltage):
        if 0 < voltage <= 65:
            return 1
        elif voltage <= 135:
            return 2
        elif voltage <= 270:
            return 3
        else: 
            return 0
        
    def query_status(self):
        if self.connect():
            voltage = self.instrument.query('MEAS:VOLT?')
            sleep(0.2)
            amp_on = self.instrument.query('AMP:OUTPUT?')
            sleep(0.2)
            self.disconnect()
            return voltage, amp_on
        return False