from copy import deepcopy
from datetime import datetime

from fibsem.microscopes.odemis_microscope import add_odemis_path
from fibsem.structures import FibsemStagePosition, MicroscopeState, FibsemImage

from autolamella.structures import AutoLamellaStage, Lamella, LamellaState
from autolamella.workflows.core import log_status_message

add_odemis_path()

from odemis.acq.feature import CryoFeature
from odemis.util.dataio import open_acquisition


def create_lamella_from_feature(feature: CryoFeature, 
                                path: str, 
                                state: MicroscopeState, 
                                num: int,
                                reference_image_path: str  = None,
                                workflow_stage: AutoLamellaStage = AutoLamellaStage.SetupLamella) -> Lamella:
    """Create a Lamella object from a CryoFeature object."""
    pos = FibsemStagePosition.from_odemis_dict(feature.stage_pos.value)

    lamella = Lamella(
            _petname=feature.name.value,
            path=path,
            _number=num,
            state=LamellaState(
                stage=workflow_stage,
                microscope_state=state,
                start_timestamp=datetime.timestamp(datetime.now()),
            ),
        )

    log_status_message(lamella, "STARTED") # for logging

    lamella.state.microscope_state.stage_position = deepcopy(pos)
    lamella.state.microscope_state.stage_position.name = lamella._petname

    if reference_image_path is not None:
        save_reference_image(reference_image_path, lamella.path)

    return lamella

def save_reference_image(odemis_image_path: str, path: str, filename: str = "ref_alignment_ib") -> None:
    """Save odemis reference image as fibsem image for use in autolamella alignment."""
    
    # open odemis image, and convert to fibsem
    acq = open_acquisition(odemis_image_path)
    image: FibsemImage = FibsemImage.from_odemis(acq[0], path=odemis_image_path)
    
    # adjust md
    image.metadata.image_settings.save = True
    image.metadata.image_settings.path = path
    image.metadata.image_settings.filename = filename
    
    # save
    image.save()