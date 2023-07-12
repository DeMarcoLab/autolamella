## Changes 

### 11th - July - 2023

- New features
    - refactor UI updates
    - Threaded milling for live updates
    - Install and run UI .bat scripts 
- Fixed bugs
    - experiment saved consistently
    

### 24th - May - 2023

- Added new feature
    - Using Milling stages data structure from FIBSEM
    - Added Instructions:
        There are now instructions available in the bottom of the main UI as a general guide for a lamella prep 
    - Added better logging
    - Added statistics: 
        Statistics are now added and viewed from the new logging
    - Protocol checking:
        Protocols are now checked for missing or bad values, checks are raised or default values are used for improper values
    - Protocol converter function:
        New function to convert the old protocol format to the new one for backwards compatibility
    - Added Default experiment names:
        Default experiment names are now added to the experiment name field
    - Added test checklist: 
        There is now an internal test checklist which can be used to test and confirm general functionality of the software


- Fixed bugs
    - Fixed incorrect experiment loading
    - Updated docs and read me
