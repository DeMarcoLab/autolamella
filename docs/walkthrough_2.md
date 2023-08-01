# Walkthrough

This is a general walkthrough on running an autolamella workflow. Further details can be viewed in their respective documentation and some are linked within this walkthrough.

## Methods

The autolamella program has incorporated two possible workflows that can be achieved. One is the default auto lamella workflow which is the standard lamella preparation workflow. The other is the waffle method workflow which has been recently developed as outlined in this [paper](https://www.nature.com/articles/s41467-022-29501-3). 

From a user interface perspective, both methods can be setup and run in a near identical fashion. The core processes of selecting lamella positions, milling parameters, supervision and monitoring can be set up the same way for both methods.

## Connection and Setup

The first step is to connect to the microscope. This can be setup to be done manually or automatically if the system parameters are setup in the system.yaml file.

To connect, first launch the autolamella program. Then in the connect tab (Under the system tab), enter the IP address of the microscope server and select the manufacturer of the microscope. Then click connect. 

![connect to microscope](img/walkthrough_2/connect_to_microscope.png)

Once connected, create an experiment from the file menu by clicking create experiment. This will prompt you to choose a location to save the experiment folder which contains the experiment.yaml file. 

Once an experiment has been created, the experiment can be reloaded anytime by clicking load experiment from the file menu. This will prompt you to select the experiment.yaml file to load.

The next step is to load a protocol. Select load protocol from the file menu. This will prompt you to select a protocol.yaml file to load. A default one is provided, however, it can be modified to suit your needs. In the protocol tab, changes can be made and then saved. Details on each parameter is explained in the features section of the documentation. !! LINK TO FEATURES !! #TODO

![load protocol](img/walkthrough_2/change_protocol.png)

To update the changes for the current session, click update protocol. To save these changes to a new protocol file, click save protocol. This will prompt you to select a location to save the protocol.yaml file. 

## Adding Lamellae

Once the system is setup, the first step is to acquire images and move to a location for creating a lamella. This can be done by clicking acquire all images in the imaging tab. This will acquire all the images and display them in the napari viewer. To move, directly to some coordinates, you can move to a position in the movement tab. Alternatively, you can also click on the image to move to that position. The movement tab also has controls for tilting and moving flat to the ion or electron beam.

Once at a desired location, click add lamella to add a lamella to the experiment. This will setup a position. To move around, double clicking on the image will move the stage to that position. Alternatively, you can also move to a position in the movement tab. 

![add lamella](img/walkthrough_2/add_lamella.png)

This image shows an example of the setup when using the waffle method workflow. However, the initial placement phase is identical for the default workflow. 

![add lamella](img/walkthrough_2/default_method_setup.png)


To remove a lamella, click remove lamella and this will remove it from the experiment. The dropdown next to current lamella can be used to select a lamella individually and remove it or change its placement as necessary.
Once satisfied with the placement, click save position to confirm its location. Additional lamellae can be added and saved in the same way. Once all the lamellae location have been saved, the process can continue to the next step.

## Workflow

The process now diverges based on which workflow is being used. 

### Default Workflow

With lamellae chosen and position saved. The button labelled "Run Setup Autolamella" will be highlighted. Clicking this will begin the process of setting up the lamellae and confirming the position. To make any changes to the milling parameters, click on the milling tab. In the dropdown labelled milling stage, the specific aspect can be selected. The paraemters such as width and height can then be changed. 


