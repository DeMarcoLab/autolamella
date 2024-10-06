from copy import deepcopy
from datetime import datetime

from fibsem.microscopes.odemis_microscope import add_odemis_path
from fibsem.structures import FibsemStagePosition, MicroscopeState

from autolamella.structures import AutoLamellaStage, Lamella, LamellaState
from autolamella.workflows.core import log_status_message

add_odemis_path()

from odemis.acq.feature import CryoFeature


def create_lamella_from_feature(feature: CryoFeature, path: str, state: MicroscopeState, num: int) -> Lamella:
    """Create a Lamella object from a CryoFeature object."""
    pos = FibsemStagePosition.from_odemis_dict(feature.stage_pos.value)

    workflow_stage = AutoLamellaStage.SetupLamella

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

    log_status_message(lamella, "STARTED")

    lamella.state.microscope_state.stage_position = deepcopy(pos)
    lamella.state.microscope_state.stage_position.name = lamella._petname

    return lamella