

# v0.4.0 (10/02/2025)

Current Status: Pre-Release

## Installation

OpenFIBSEM now has a set of optional dependencies to support different applications. The following autolamella methods require some of these optional dependencies. You can install them with pip. 

| Method               | Dependencies         |
|----------------------|----------------------|
| On-Grid           | fibsem[ui]    |
| Trench Milling    | fibsem[ui]   |
| Waffle            | fibsem[ui,ml] |

## Workflow
The workflows have a number of improvements and fixes:

### Methods
- All methods now support scan rotation (both SEM and FIB).
- A Trench Milling method has been added, that allows running only the trench milling workflow. Previously, this was only available as part of the more advanced methods. A baseline trench milling protocol has been added (autolamella/protocol/protocol-trench.yaml)

### Protocol
- Protocols have been updated to support the changes in fibsem-v0.4.0 (see release notes for details). Loading an existing protocol should be automatically converted to support the new options. If they do not, consider it a bug, and report it to me.
- There is now an option to turn off the beams after the workflows complete. 
- The additional milling protocol options include; milling strategy, milling alignment, milling acquisition.
- You can now specify the position of each pattern independently in the protocol, by editing the pattern.point. The following example shows the default positioning of the fiducial pattern (offset in x by 25um).


``` yaml
milling:
    fiducial:
    -   milling:
            application_file: Si
            hfw: 8.0e-05
            milling_current: 2.0e-09
            preset: 30 keV; 20 nA
        name: Fiducial
        pattern:
            depth: 1.0e-06
            height: 1.0e-05
            name: Fiducial
            passes: null
            rotation: 45
            width: 1.0e-06
            point: {"x": 25.0e-6, "y": 0.0e-6}
        strategy: {}
```

## User Interface
- Tooltips are being added to provide a short explanation for protocol and workflow options.
- The workflow summary has been improved, and now shows the status, defect reason, previously completed workflow, and next workflow for each lamella. The workflow summary also includes an estimated duration for the remaining workflows.
- Mark failure has been changed to Mark as Defect, and allows you to add a note for the defect reasons (e.g. contamination, cracked, etc)
- Run AutoLamella now shows a summary of the workflows to be run, and allows you to enable workflow stages / supervision. This allows you to adjust the supervision without returning to the Protocol tab.
- An additional Setup Polishing stage has been added allowing batch refinement of the final polishing position before running the milling.

### Minimap
- The minimap ui has been updated, and should be much more performant when adding many lamella. 
- You can now select the number of tiles, and field of view directly.
- You can now cancel the overview acquisition.  
- Tabs have been consolidated into a single scroll area for clarity.
- The display of milling patterns on positions on the overview is now officially supported. You can enable it by selecting Display Pattern, and selecting the pattern to display.
- Correlation controls are now easier to access, you can toggle them with the Enable Correlation Mode button.

### Analysis Tools
- AutoLamella has always recorded data and statistics about the workflows, but it was difficult for users to access the data. We believe this data is useful for users to evaluate or summarise the workflows, and are introducing some new features to make this data easier to access.   

### Report Generation
- You can now generate pdf report with statistics about run, summary images for each lamella. The report summarises the duration of each part of the run, and provides an overview of the operations performed on each lamella. 
- Generating a report will also export the underlaying data as csv into the experiment directory. This data can be used for post-run analysis or overall statistics collection.

### Developer Notes
- The protocol object is now a dataclass, instead of a dictionary. See structures.py for details.
- MicroscopeSettings (settings) is being deprecated, microscope configuration is now stored on the protocol in protocol.configuration

### Experimental Features
There is now code to support specifying the milling angle as the angle between the FIB and sample stage, rather than the stage tilt. This is the conventional definition of milling angle expected by the community.
This will be enabled in the next version (v0.4.1), and will need to be updated in the protocol.

