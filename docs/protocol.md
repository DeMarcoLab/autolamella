# AutoLamella Protocol
The new AutoLamella program utilises the OpenFIBSEM code package to build a more streamlined and robust automated lamella workflow that includes a new user interface. This updated AutoLamella program also includes a more intuitive system for the lamella protocol. AutoLamella protocol's should now be easier to make, without requiring any calculations. 

## The new protocol format
![New Protocol Format](img/NewProtocolFormat.bmp)

Each of the colours indicates a different protocol stage. In this case there are three: Rough Cut in yellow, Regular Cut in blue, and Polishing Cut in magenta. Additionally the optional microexpansion joints are indicated in yellow as they are milled during the Rough Cut stage if the user opts to use them. 

The Lamella width and height are indicated at the centre, and must be input for each protocol stage. The placement of each trench is based on two factors: the offset, and the trench height. For example, the Polishing Cut (magenta) has an offset of 0 as it is situated directly above and below the Lamella, and in our default protocol example, has a trench height of 1e-6m. The Regular Cut (blue) has an offset of 1e-6m, and a trench height of 2e-6m. Finally, the offset of the Rough Cut (yellow) is the cumulative trench height of the previous stages, 3e-6m; and has a trench height of 10e-6m. It should be mentioned that in practice the order of the protocol stages would be the reverse, as the stages are milled sequentially, it is just easier to explain in this manner. Additionally, if you would like overlap between stages, the offset of the stage simply needs to be less than the cumulative trench heights of the other stages.

As previously mentioned the microexpansion joints are optional and can be enabled/disabled in within the UI. If they are enabled they must have the height, width, and distance from the Lamella within the protocol. The distance does NOT include the Lamella width itself, and is accounted for when milling.

The fiducial requires the width and height of a rectangle, which will then be rotated +/- 45 degrees to create the 'X'. Currently the fiducial is hard coded to be milled approximately one fifth of way through the view from the left. A visual of a completed protocol working within the UI might look like so: 

![Protocol visual](img/ui.png)

All milling operations for the fiducial and trenches must also contain the milling depth and current for each stage. The depth and current for the microexpansion joint is assumed to be the same as that of the first stage. Additionally, the number of attempts the program should make when attempting to align the imaging beam to the fiducial should be stored within the Lamella section of the protocol.

Finally, here is what a completed protocol in the new format might look like as a .yaml file:

![Protocol yaml file](img/protocol.png)

## How to convert to the new protocol format
A tool has been created to automatically convert an old protocol file to the new format. 

Simply navigate to the autolamella folder that contains protocol_converter.py in a terminal and write the following:

```shellscript
python protocol_converter.py("path/old_protocol.yaml", "path/new_protocol.yaml")
```

The first argument refers to the curent file path of the old protocol yaml file. The second location indicates the file location you would like the converted protocol yaml file saved to.