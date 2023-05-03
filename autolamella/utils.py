from pathlib import Path
import os
import fibsem.config as config
from fibsem.microscope import FibsemMicroscope, TescanMicroscope, ThermoMicroscope, DemoMicroscope
import config as autolamella_config

# PPP: remove this and use the fibsem one with a default path in experiment
def make_logging_directory(path: Path = None, name="run"):
    if path is None:
        path = os.path.join(config.BASE_PATH, "log")
    directory = os.path.join(path, name)
    os.makedirs(directory, exist_ok=True)
    return directory


def check_loaded_protocol(microscope_protocol: dict, _THERMO: bool = False,_TESCAN: bool = False, _DEMO: bool = False):

        
        if microscope_protocol is None:
            return 

        def _check_helper(answer_dict, microscope_dict, exception,acceptable_values = None):
            
            for name in answer_dict:
                if name in exception:
                    continue
                if name not in microscope_dict:
                    microscope_dict[name] = answer_dict[name]
                item = microscope_dict[name]
                if item is None:
                    microscope_dict[name] = answer_dict[name]
                    item = microscope_dict[name]
                
                default_type = type(answer_dict[name])

                if isinstance(answer_dict[name],int):
                    default_type = float

                if type(item) != default_type:
                    return f'Protocol value error: {name} is not of type {default_type}'
                
                if acceptable_values is None:
                    continue
                else:
                    if name in acceptable_values:
                        if item not in acceptable_values[name]:
                            return f'Protocol value error: {item} is not an acceptable value for {name}'




        main_headers = autolamella_config.DEFAULT_PROTOCOL["main_headers"]
        fiducial_headers = autolamella_config.DEFAULT_PROTOCOL["fiducial_headers"]
        lamella_headers = autolamella_config.DEFAULT_PROTOCOL["lamella_headers"]
        protocol_stage_1 = autolamella_config.DEFAULT_PROTOCOL["protocol_stage_1"]
        protocol_stage_2 = autolamella_config.DEFAULT_PROTOCOL["protocol_stage_2"]
        protocol_stage_3 = autolamella_config.DEFAULT_PROTOCOL["protocol_stage_3"]
        microexpansion_headers = autolamella_config.DEFAULT_PROTOCOL["microexpansion_headers"]
        
        main_header_exception = ["application_file"]  if _TESCAN and _DEMO else []
        
        

        error_check =_check_helper(main_headers, microscope_protocol, main_header_exception)

        if error_check is not None:
            return error_check

        fiducial_exception = ["preset"] if (_THERMO and _DEMO) else []

        error_check = _check_helper(fiducial_headers, microscope_protocol["fiducial"], fiducial_exception)

        if error_check is not None:
            return error_check
        

        lamella_exception = ["protocol_stages"]

        error_check = _check_helper(lamella_headers, microscope_protocol["lamella"], lamella_exception)

        if error_check is not None:
            return error_check


        protocol_stages = [protocol_stage_1, protocol_stage_2, protocol_stage_3]

        for idx in range(len(protocol_stages)):

            stage = protocol_stages[idx]

            protocol_stage_exception = ["preset"] if (_THERMO and _DEMO) else []

            error_check =_check_helper(stage,  microscope_protocol["lamella"]["protocol_stages"][idx], protocol_stage_exception)

            if error_check is not None:
                return error_check
            


        microexpansion_exception = []
        error_check = _check_helper(microexpansion_headers, microscope_protocol["microexpansion"], microexpansion_exception)    

        if error_check is not None:
            return error_check