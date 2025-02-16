import logging
from typing import List

from fibsem.microscope import FibsemMicroscope
from fibsem.structures import MicroscopeSettings

from autolamella.structures import (
    AutoLamellaMethod,
    AutoLamellaStage,
    Experiment,
    AutoLamellaProtocol,
    is_ready_for,
)
from autolamella.ui import AutoLamellaUI
from autolamella.workflows.core import (
    end_of_stage_update,
    log_status_message,
    mill_lamella,
    mill_trench,
    mill_undercut,
    setup_lamella,
    start_of_stage_update,
    pass_through_stage,
    setup_polishing,
)
from autolamella.workflows.ui import ask_user, ask_user_continue_workflow

WORKFLOW_STAGES = {
    AutoLamellaStage.MillTrench: mill_trench,
    AutoLamellaStage.MillUndercut: mill_undercut,
    AutoLamellaStage.SetupLamella: setup_lamella,
    AutoLamellaStage.MillRough: mill_lamella,
    AutoLamellaStage.SetupPolishing: setup_polishing,
    AutoLamellaStage.MillPolishing: mill_lamella,
}
LAMELLA_MILLING_WORKFLOW = [AutoLamellaStage.MillRough,
                            AutoLamellaStage.SetupPolishing,
                            AutoLamellaStage.MillPolishing]

def run_trench_milling(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    experiment: Experiment,
    parent_ui: AutoLamellaUI=None,
    stages_to_complete: List[AutoLamellaStage] = AutoLamellaMethod.TRENCH.workflow
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.workflow is AutoLamellaStage.PositionReady and not lamella.is_failure:
        # if is_ready_for(lamella, protocol.method, AutoLamellaStage.MillTrench):
        # TODO: if we integrate this, we need to be more careful about which state we restore from,
        # e.g. if we are in mill undercut, we need to go back to the PositionReady state.. not just current, needs more work
                        
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaStage.MillTrench, 
                parent_ui=parent_ui
            )

            lamella = mill_trench(microscope, protocol, lamella, parent_ui)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment

def run_undercut_milling(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.workflow is AutoLamellaStage.MillTrench and not lamella.is_failure:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaStage.MillUndercut,
                parent_ui=parent_ui
            )
            lamella = mill_undercut(microscope, protocol, lamella, parent_ui)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

        log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment

def run_setup_lamella(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    for lamella in experiment.positions:

        # TODO: migrate to is_ready_for:
        #  protocol.method.get_next(lamella.workflow) is AutoLamellaStage.SetupLamella
        if lamella.workflow in [AutoLamellaStage.PositionReady, 
                                AutoLamellaStage.MillUndercut, 
                                AutoLamellaStage.LandLamella] and not lamella.is_failure:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaStage.SetupLamella,
                parent_ui=parent_ui
            )

            lamella = setup_lamella(microscope, protocol, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)
    
    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment

# autolamella
def run_lamella_milling(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
    stages_to_complete: List[AutoLamellaStage] = LAMELLA_MILLING_WORKFLOW
) -> Experiment:

    for stage in LAMELLA_MILLING_WORKFLOW:
        if stage not in stages_to_complete:
            logging.info(f"Skipping stage {stage} as it is not in stages_to_complete {stages_to_complete}")
            continue
        for lamella in experiment.positions:
            if lamella.workflow is AutoLamellaStage(stage.value - 1) and not lamella.is_failure:
                lamella = start_of_stage_update(microscope, lamella, stage, parent_ui)
                lamella = WORKFLOW_STAGES[lamella.workflow](microscope, protocol, lamella, parent_ui)
                experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

    # finish # TODO: separate this into a separate function
    for lamella in experiment.positions:
        if lamella.workflow is AutoLamellaStage.MillPolishing and not lamella.is_failure:
            lamella = start_of_stage_update(microscope, lamella, AutoLamellaStage.Finished, parent_ui, restore_state=False)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, save_state=False)

    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment

def run_autolamella(
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
    stages_to_complete: List[AutoLamellaStage] = AutoLamellaMethod.ON_GRID.workflow
) -> Experiment:
    
    # run setup
    if AutoLamellaStage.SetupLamella in stages_to_complete:
        experiment = run_setup_lamella(microscope, protocol, experiment, parent_ui)

        if protocol.supervision[AutoLamellaStage.SetupLamella]:
            ret = ask_user(parent_ui=parent_ui, msg="Start AutoLamella Milling?", pos="Continue", neg="Exit")
            if ret is False:
                return experiment

    # run lamella milling
    experiment = run_lamella_milling(microscope, protocol, experiment, parent_ui, stages_to_complete)

    return experiment

def run_autolamella_waffle(    
    microscope: FibsemMicroscope,
    protocol: AutoLamellaProtocol,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
    stages_to_complete: List[AutoLamellaStage] = AutoLamellaMethod.WAFFLE.workflow
) -> Experiment:
    """Run the waffle method workflow."""
    # TODO: add more validation, so we only ask the user to complete a stage
    # if a lamella is ready that stage

    # run trench milling
    if AutoLamellaStage.MillTrench in stages_to_complete and experiment.at_stage(AutoLamellaStage.PositionReady):
        experiment = run_trench_milling(microscope, protocol, experiment, parent_ui)

    if AutoLamellaStage.MillUndercut in stages_to_complete and experiment.at_stage(AutoLamellaStage.MillTrench):
        ret = ask_user_continue_workflow(
            parent_ui=parent_ui,
            msg="Continue to Mill Undercut?",
            validate=protocol.supervision[AutoLamellaStage.MillUndercut],
        )
        if ret is False:
            return experiment

        # run undercut milling
        experiment = run_undercut_milling(microscope=microscope, 
                                          protocol=protocol, 
                                          experiment=experiment, 
                                          parent_ui=parent_ui)

    if AutoLamellaStage.SetupLamella in stages_to_complete and experiment.at_stage(AutoLamellaStage.MillUndercut):
        ret = ask_user_continue_workflow(
            parent_ui=parent_ui,
            msg="Continue to Setup Lamella?",
            validate=protocol.supervision[AutoLamellaStage.SetupLamella],
        )
        if ret is False:
            return experiment

    # run autolamella
    experiment = run_autolamella(microscope=microscope, 
                                 protocol=protocol, 
                                 experiment=experiment, 
                                 parent_ui=parent_ui, 
                                 stages_to_complete=stages_to_complete)

    return experiment

METHOD_WORKFLOWS_FN = {
    AutoLamellaMethod.ON_GRID: run_autolamella,
    AutoLamellaMethod.WAFFLE: run_autolamella_waffle,
    AutoLamellaMethod.TRENCH: run_trench_milling,
}
