# Features

## Minimap

## Supervision

The supervision parameter outlines how much of the process can be user supervised. The example outlined shows the process being fully supervised. This ensures that the user has control of milling parameters before running, detected features and the ability to redo milling if necessary.

The process can be done fully unsupervised if required. You may also selectively supervise and unsupervise relevant stages as necessary. In the protocol tab under supervision, the supervision checkbox can be set for each stage.

![supervision](img/walkthrough_2/supervision.png)

## Workflows

## Time Travel

## Lamella Protocol

## Statistics, Data and Logging

The tools folder in the project directory contains a number of useful tools for analysing data and logging. The stats.py file allows the user to generate statistics from the data collected during the autolamella process. The stats.py file can be run from the command line using the following command:

streamlit run stats.py

The experiments analytics include information about the following:

- The number of lamellas that went through each stage of the process ( Trenches, Undercut, Polish)
- The experiment timeline
- The durtion of each step with reference images
- Each lamella's history


