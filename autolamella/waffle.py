from fibsem.microscope import FibsemMicroscope
from fibsem.structures import MicroscopeSettings
from autolamella.structures import (
    AutoLamellaWaffleStage,
    Experiment,
)
from autolamella.ui.AutoLamellaUI import AutoLamellaUI
from autolamella.workflows.core import ( log_status_message, mill_trench, mill_undercut, mill_feature, mill_lamella, setup_lamella, start_of_stage_update, end_of_stage_update)

WORKFLOW_STAGES = {
    AutoLamellaWaffleStage.MillTrench: mill_trench,
    AutoLamellaWaffleStage.MillUndercut: mill_undercut,
    AutoLamellaWaffleStage.ReadyLamella: setup_lamella,
    AutoLamellaWaffleStage.MillFeatures: mill_feature,
    AutoLamellaWaffleStage.MillRoughCut: mill_lamella,
    AutoLamellaWaffleStage.MillRegularCut: mill_lamella,
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
                AutoLamellaWaffleStage(lamella.state.stage.value + 1), 
                parent_ui=parent_ui
            )

            lamella = mill_trench(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            parent_ui.update_experiment_signal.emit(experiment)
    
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
            parent_ui.update_experiment_signal.emit(experiment)

            # ready lamella for next stage
            lamella = start_of_stage_update(microscope, lamella, AutoLamellaWaffleStage.SetupLamella, parent_ui=parent_ui,_restore_state=False,)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)
            parent_ui.update_experiment_signal.emit(experiment)
    
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
                AutoLamellaWaffleStage(lamella.state.stage.value + 1),
                parent_ui=parent_ui
            )

            lamella = setup_lamella(microscope, settings, lamella, parent_ui)

            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

            parent_ui.update_experiment_signal.emit(experiment)
    
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
        AutoLamellaWaffleStage.MillFeatures,
        AutoLamellaWaffleStage.MillRoughCut,
        AutoLamellaWaffleStage.MillRegularCut,
        AutoLamellaWaffleStage.MillPolishingCut,
    ]
    for stage in stages:
        for lamella in experiment.positions:
            if lamella.state.stage == AutoLamellaWaffleStage(stage.value - 1) and not lamella._is_failure:
                lamella = start_of_stage_update(microscope, lamella, stage, parent_ui)
                lamella = WORKFLOW_STAGES[lamella.state.stage](microscope, settings, lamella, parent_ui)
                experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui)

                parent_ui.update_experiment_signal.emit(experiment)


    # finish
    for lamella in experiment.positions:
        if lamella.state.stage == AutoLamellaWaffleStage.MillPolishingCut and not lamella._is_failure:
            lamella = start_of_stage_update(microscope, lamella, AutoLamellaWaffleStage.Finished, parent_ui, _restore_state=False)
            experiment = end_of_stage_update(microscope, experiment, lamella, parent_ui, _save_state=False)
            parent_ui.update_experiment_signal.emit(experiment)

    log_status_message(lamella, "NULL_END") # for logging purposes

    return experiment
