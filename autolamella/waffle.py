from fibsem.microscope import FibsemMicroscope
from fibsem.structures import MicroscopeSettings
from autolamella.structures import (
    AutoLamellaWaffleStage,
    Experiment,
)
from autolamella.ui import AutoLamellaUI
from autolamella.workflows.core import ( log_status_message, mill_trench, mill_undercut, mill_lamella, setup_lamella, start_of_stage_update, end_of_stage_update)
from autolamella.workflows.ui import ask_user, ask_user_continue_workflow, update_experiment_ui

WORKFLOW_STAGES = {
    AutoLamellaWaffleStage.MillTrench: mill_trench,
    AutoLamellaWaffleStage.MillUndercut: mill_undercut,
    AutoLamellaWaffleStage.ReadyLamella: setup_lamella,
    AutoLamellaWaffleStage.MillRoughCut: mill_lamella,
    AutoLamellaWaffleStage.MillPolishingCut: mill_lamella,
}


def run_trench_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI=None,
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.state.stage == AutoLamellaWaffleStage.ReadyTrench and not lamella._is_failure:
                        
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage.MillTrench, 
                parent_ui=parent_ui
            )

            lamella = mill_trench(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            update_experiment_ui(parent_ui, experiment)
    
    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment


def run_undercut_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.state.stage == AutoLamellaWaffleStage.MillTrench and not lamella._is_failure:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage.MillUndercut,
                parent_ui=parent_ui
            )
            lamella = mill_undercut(microscope, settings, lamella, parent_ui)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)
            update_experiment_ui(parent_ui, experiment)

            # ready lamella for next stage
            lamella = start_of_stage_update(microscope, lamella, AutoLamellaWaffleStage.SetupLamella, parent_ui=parent_ui,_restore_state=False,)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)
            update_experiment_ui(parent_ui, experiment)
    
    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment

def run_setup_lamella(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    for lamella in experiment.positions:

        if lamella.state.stage == AutoLamellaWaffleStage.SetupLamella and not lamella._is_failure:
            lamella = start_of_stage_update(
                microscope,
                lamella,
                AutoLamellaWaffleStage.ReadyLamella,
                parent_ui=parent_ui
            )

            lamella = setup_lamella(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            update_experiment_ui(parent_ui, experiment)
    
    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment

# autolamella
def run_lamella_milling(
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:


    stages = [
        AutoLamellaWaffleStage.MillRoughCut,
        AutoLamellaWaffleStage.MillPolishingCut,
    ]
    for stage in stages:
        for lamella in experiment.positions:
            if lamella.state.stage == AutoLamellaWaffleStage(stage.value - 1) and not lamella._is_failure:
                lamella = start_of_stage_update(microscope, lamella, stage, parent_ui)
                lamella = WORKFLOW_STAGES[lamella.state.stage](microscope, settings, lamella, parent_ui)
                experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

                update_experiment_ui(parent_ui, experiment)


    # finish
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLamellaWaffleStage.MillPolishingCut and not lamella._is_failure:
            lamella = start_of_stage_update(microscope, lamella, AutoLamellaWaffleStage.Finished, parent_ui, _restore_state=False)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)
            update_experiment_ui(parent_ui, experiment)

    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment


def run_autolamella(    
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    
    # run setup
    experiment = run_setup_lamella(microscope, settings, experiment, parent_ui)

    validate = settings.protocol["options"]["supervise"].get("setup_lamella", True)
    if validate:
        ret = ask_user(parent_ui=parent_ui, msg="Start AutoLamella Milling?", pos="Continue", neg="Exit")
        if ret is False:
            return experiment

    # run lamella milling
    experiment = run_lamella_milling(microscope, settings, experiment, parent_ui)

    return experiment

def run_autolamella_waffle(    
    microscope: FibsemMicroscope,
    settings: MicroscopeSettings,
    experiment: Experiment,
    parent_ui: AutoLamellaUI = None,
) -> Experiment:
    """Run the waffle method workflow."""

    # run trench milling
    experiment = run_trench_milling(microscope, settings, experiment, parent_ui)

    ret = ask_user_continue_workflow(parent_ui, msg="Continue to Mill Undercut?", 
        validate=settings.protocol["options"]["supervise"].get("undercut", True))
    if ret == False:
        return experiment

    # run undercut milling
    experiment = run_undercut_milling(microscope, settings, experiment, parent_ui)

    ret = ask_user_continue_workflow(parent_ui, msg="Continue to Setup Lamella?", 
        validate=settings.protocol["options"]["supervise"].get("setup_lamella", True))
    if ret == False:
        return experiment

    # run autolamella
    experiment = run_autolamella(microscope, settings, experiment, parent_ui)

    return experiment
