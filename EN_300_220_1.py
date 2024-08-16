"""
file: EN 300 220-1 class for handling standard-specific test parameters
author: rueck.joshua@gmail.com
last updated: 02/07/2024
"""

class EN_300_220_1:

    def __init__(self):
        pass

    # calculate parameters to be set on spectrum analyzer for occupied bandwidth measurement
    def calc_obw_parameters(self, ocw):
        if 0.02*ocw <= 100:
            rbw = 100
        else:
            rbw = 0.02*ocw
        
        return {
            "rbw": rbw,
            "vbw_ratio": 3,
            "span": 3*ocw,
            "det_mode": "rms"
        }
    
    # calculate parameters to be set on spectrum analyzer for out-of-band emissions measurement
    def calc_oob_parameters(self, ocw):
        return {
            "rbw": 1000,
            "span": 6*ocw,
            "det_mode": "rms"
        }
    
    # calculate limit points for spectral mask for out-of-band emissions measurement of operating channel
    def calc_limit_oc(self, centre_freq, ocw):
        return [
                (int(centre_freq - 2.5*ocw), -36),
                (int(centre_freq - 0.5*ocw), 0),
                (int(centre_freq - 0.5*ocw), 14),
                (int(centre_freq + 0.5*ocw), 14),
                (int(centre_freq + 0.5*ocw), 0),
                (int(centre_freq + 2.5*ocw), -36)
            ]
    
    # calculate limit points for spectral mask for out-of-band emissions measurement of operational frequency band
    def calc_limit_ofb(self, f_lower_border, f_higher_border):
        return [
                    (f_lower_border - 400000, -36),
                    (f_lower_border - 200000, -36),
                    (f_lower_border, 0),
                    (f_lower_border, 14),
                    (f_higher_border, 14),
                    (f_higher_border, 0),
                    (f_higher_border + 200000, -36),
                    (f_higher_border + 400000, -36)
                ]