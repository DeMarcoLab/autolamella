import logging
import time

import numpy as np

from fibsem.structures import BeamType, MicroscopeSettings, FibsemStagePosition, FibsemManipulatorPosition
from fibsem.microscope import FibsemMicroscope

def move_to_trenching_angle(
    microscope: FibsemMicroscope, settings: MicroscopeSettings
) -> None:
    """Tilt the sample stage to the correct angle for milling trenches.
    Assumes trenches should be milled with the sample surface flat to ion beam.

    Args:
        microscope (FibsemMicroscope): autoscript microscope instance
        settings (MicroscopeSettings): microscope settings
    """
    microscope.move_flat_to_beam(
        settings=settings,
        beam_type=BeamType.ION,
    )


def move_to_liftout_angle(
    microscope: FibsemMicroscope, settings: MicroscopeSettings
) -> None:
    """Tilt the sample stage to the correct angle for liftout.

    Args:
        microscope (FibsemMicroscope): autoscript microscope instance
        settings (MicroscopeSettings): microscope settings
    """

    microscope.move_flat_to_beam(
        settings=settings,
        beam_type=BeamType.ELECTRON,
    )


def move_sample_stage_out(
    microscope: FibsemMicroscope, settings: MicroscopeSettings
) -> None:
    """Move stage completely out of the way, so it is not visible at all.

    Args:
        microscope (FibsemMicroscope): autoscript microscope instance
        settings (MicroscopeSettings): microscope settings
    """

    # Must set tilt to zero, so we don't see reflections from metal stage base
    current_position = microscope.get_stage_position()
    microscope._safe_absolute_stage_movement(FibsemStagePosition(x = current_position.x, 
                                                        y = current_position.y,    
                                                        z = current_position.z,
                                                        r = current_position.r,
                                                       t=0))  # important!
    #TODO remove hard coded position
    sample_stage_out = FibsemStagePosition(
        x=-0.002507,
        y=0.025962792,
        z=0.0039559049,
        r=np.deg2rad(settings.system.stage.rotation_flat_to_electron),
    )

    # TODO: probably good enought to just move down a fair bit.
    # TODO: make these dynamically set based on initial_position
    # TODO: MAGIC_NUMBER
    logging.info(f"move sample grid out to {sample_stage_out}")
    microscope._safe_absolute_stage_movement(sample_stage_out)
    logging.info(f"move sample stage out complete.")


def move_needle_to_liftout_position(
    microscope: FibsemMicroscope,
    position: str = "EUCENTRIC", 
    dx: float = -25.0e-6,
    dy: float = 0.0e-6,
    dz: float = 10.0e-6,
) -> None:
    """Insert the needle to just above the eucentric point, ready for liftout.

    Args:
        microscope (FibsemMicroscope): autoscript microscope instance
        dz (float): distance to move above the eucentric point (ManipulatorCoordinateSystem.RAW -> up = negative)
    """

    # insert to park position
    microscope.insert_manipulator("PARK")

    # move to  offset position
    offset = FibsemManipulatorPosition(dx, dy, dz, coordinate_system="RAW")                                                                         
    microscope.move_manipulator_to_position_offset(offset = offset, name=position)


def move_needle_to_landing_position(
    microscope: FibsemMicroscope,
    position: str= "PARK",
    dx: float = -125.0e-6,
    dy: float = 0.0e-6,
    dz: float = 0.0e-6,
) -> None:
    """Insert the needle to just above, and left of the eucentric point, ready for land
    .+ing.

    Args:
        microscope (FibsemMicroscope): microscope instance
        dz (float): distance to move above the eucentric point (ManipulatorCoordinateSystem.RAW -> up = negative)

    Returns:
        ManipulatorPosition: current needle position
    """

    # insert to park position
    microscope.insert_manipulator("PARK")

    # move to  offset position 
    offset = FibsemManipulatorPosition(dx, dy, dz, coordinate_system="RAW")
    microscope.move_manipulator_to_position_offset(offset = offset, name=position)

    
    return microscope.get_manipulator_position()


def move_needle_to_reset_position(microscope: FibsemMicroscope, name: str = "EUCENTRIC") -> None:
    """Move the needle into position, ready for reset"""

    # insert to park
    microscope.insert_manipulator("PARK")

    # move to eucentric
    position = microscope._get_saved_manipulator_position(name)
    microscope.move_manipulator_absolute(position)

    return microscope.get_manipulator_position()

def move_needle_to_park_position(microscope: FibsemMicroscope, name: str = "PARK") -> None:
    """Move the needle to the park position"""

    # insert to park
    microscope.insert_manipulator("PARK")

    return microscope.get_manipulator_position()


def move_to_lamella_angle(
    microscope: FibsemMicroscope, protocol: dict
) -> FibsemStagePosition:
    """Rotate and tilt the stage to the thinning angle, assumes from the landing position"""

    # thinning position
    thinning_rotation_angle = np.deg2rad(protocol["lamella"]["rotation_angle"])
    thinning_tilt_angle = np.deg2rad(protocol["lamella"]["tilt_angle"])

    stage_position = FibsemStagePosition(
        r=thinning_rotation_angle,
        t=thinning_tilt_angle,
        )
    microscope._safe_absolute_stage_movement(stage_position)


