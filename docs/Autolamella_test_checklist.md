# Autolamella Test Checklist
## Checklist for functionality of program

This checklist is to be used from a user perspective to test for functionality and test for aspects which cannot otherwise be automatically tested. It is also used to test for functionality of the program as a whole, and not just the individual components. It also provides a sanity check and outlines expected behaviour of the program.

**This checklist is not exhaustive and is subject to change.**

### Connection

#### Connecting to microscope
1. Does not crash program if connection is unsuccessful, 
2. Able to retry connection with different settings if required
3. Can disconnect successfully
4. Can reconnect successfully

### Experiment Creation

1. Can create experiment 
2. Can load a previously created experiment
- 2.1 Successfully loads past lamella at correct stage and positions

### Protocol Loading

1. Can load a protocol
- Can load a protocol without errors
- Loads default values for keys that are not provided
- Key type is asserted
2. Can save a protocol to file
- protocol is saved correctly, modified values are saved accurately
- Value types are maintained
- Saved protocol can be reloaded successfully
- Can save to a new or existing protocol file
3. Can modify a protocol live and resulting pattern updates live

### Adding/Moving/Removing Lamella and Fiducial patterns

1. Can add lamella pattern
- Can add empty lamella
- Can alter lamella parameters
2. Can move lamella pattern to a new position
- Can move by specifying x and y coordinates 
- Can move by clicking on image
- Moving lamella does not alter any parameters other than position
- Moving lamella does not alter fiducial pattern
- Moving lamella/fiducial does not alter other lamella/fiducial patterns
- Results in warning when clicking out of bounds
- Cannot move lamella outside of image.
3. Can remove lamella
- Removes correct lamella
- In experiment list, each lamella has a unique name
- Lamella is removed from list of available lamellae
4. Can add/remove microexpansions

### Saving Lamella and Milling Fiducial

1. Can save lamella
- Warning shown if Horizontal Field Width (HFW) is too big or small for pattern
- Saving Lamella mills fiducial pattern
- Can remill fiducial
- Can move to position once lamella is saved, allowing user to move to another location for another lamella
- If lamella is not saved, position is not saved, move to position button is disabled

### Running Autolamella

1. Can run autolamella
- Lamellae are milled accurately and in position (check physically)
- Lamellae are milled in order of creation
- Can run with/without microexpansions
- Lamella data only saved if stage completed successfully

### Consistency across manufacturers

1. UI and behaviour is consistent across manufacturers where expected
- Certain features not available and is hidden away depending on manufacturer (e.g. Presets hidden for ThermoFisher system, application file hidden for TESCAN system)

### Lamella Status

1. Lamellae have status set and updated throughout each step
- Steps
    - Setup
    - Fiducial Milled
    - Microexpansion cut
    - Rough cut
    - Regular cut
    - Polishing cut
    - Finished

- Status can be accessed anytime and saved to experiment