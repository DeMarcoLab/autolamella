import os

BASE_PATH = os.path.dirname(__file__)
LOG_PATH = os.path.join(BASE_PATH, 'log')

DEFAULT_PROTOCOL = {

"main_headers" : {
            "name": "autolamella_demo",
            "application_file": "autolamella",
            "stage_rotation": 230,
            "stage_tilt": 52,
        },

"fiducial_headers" : {
    "height": 10.e-6,
    "width": 1.e-6,
    "depth": 1.0e-6,
    "rotation": 45,
    "milling_current": 28.e-9,
    "preset": "30 keV; 20 nA"
},

"lamella_headers" : {
    "beam_shift_attempts": 3,
    "lamella_width": 10.e-6,
    "lamella_length": 10.e-6,
    "alignment_current": "Imaging Current",
},

"protocol_stage_1" : {
    "trench_height":10.e-6,
    "depth": 1.e-6,
    "offset": 2.e-6,
    "size_ratio": 1.0,
    "milling_current": 2.e-9,
    "preset": "30 keV; 2.5 nA"
},

"protocol_stage_2" : {
    "trench_height":2.e-6,
    "depth": 1.e-6,
    "offset": 0.5e-6,
    "size_ratio": 1.0,
    "milling_current": 0.74e-9,
    "preset": "30 keV; 2.5 nA"
},

"protocol_stage_3" : {
    "trench_height":0.5e-6,
    "depth": 0.4e-6,
    "offset": 0.0e-6,
    "size_ratio": 1.0,
    "milling_current": 60.0e-12,
    "preset": "30 keV; 2.5 nA"
},

"microexpansion_headers" : {
    "width": 0.5e-6,
    "height": 18.e-6,
    "distance": 10.e-6,
}
}
