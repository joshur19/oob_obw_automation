"""
file: implementation of class for climatic test chamber based on work by Matias Senger on GitHub
author: rueck.joshua@gmail.com
last updated: 16/07/2024
"""

import tags
from VotschTechnikClimateChamber.ClimateChamber import ClimateChamber

class WKL(ClimateChamber):

    def __init__(self, ip: str, temperature_min: float, temperature_max: float, timeout=1):
        super().__init__(ip, temperature_min, temperature_max, timeout)

    def set_temperature(self, temp):
        try:
            if self.temperature_min < float(temp) < self.temperature_max:
                if not self.is_running:
                    self.temperature_set_point = temp
                    self.start()
                    tags.log('WKL', f'Chamber set to {temp}°C and started operation')
                    return True
                else:
                    tags.log('WKL', 'Tried to set chamber temp but chamber already running.')
                    return False
            else:
                tags.log('WKL', 'Temperature value entered not in valid range.')
                return False
        except ValueError:
            tags.log('WKL', 'Invalid temperature value entered.')
            return False