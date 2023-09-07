import sys

import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableView, QPushButton, QComboBox, QCheckBox
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QDialog


PROTOCOL_KEYS = ["trench", "MillUndercut", "fiducial", "notch", "MillRoughCut", "MillRegularCut", "MillPolishingCut", "microexpansion"]

from autolamella.structures import Experiment
import os 

# ref: https://www.pythonguis.com/faq/editing-pyqt-tableview/

class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data

    def rowCount(self, index):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole or role == Qt.EditRole:
                value = self._data.iloc[index.row(), index.column()]
                return str(value)

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            self._data.iloc[index.row(), index.column()] = value
            return True
        return False

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]

    # def flags(self, index):
    #     return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable


    # disable editting on specific columns
    def flags(self, index):
        if index.column() in [0, 1, 2]:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled
        else:
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

class AutoLamellaProtocolUI(QDialog):
    def __init__(self, experiment: Experiment):
        super().__init__()

        self.table = QTableView()
        self.exp = experiment

        # add button
        self.button = QPushButton("Print Table to Console")
        self.button.clicked.connect(self.handleButton)

        self.combobox = QComboBox()
        self.combobox.addItems(PROTOCOL_KEYS)
        self.combobox.currentIndexChanged.connect(self._update_table)


        self.comboBox_lamella = QComboBox()
        self.comboBox_lamella.addItems([lamella._petname for lamella in self.exp.positions])
        self.comboBox_lamella.currentIndexChanged.connect(self._update_table)

        self.checkBox = QCheckBox("Filter WorkflowStage")
        self.checkBox.stateChanged.connect(self._update_table)

        self.checkBox_lamella = QCheckBox("Filter Lamella")
        self.checkBox_lamella.stateChanged.connect(self._update_table)


        # add layout
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.table)
        self.layout.addWidget(self.checkBox)
        self.layout.addWidget(self.checkBox_lamella)
        self.layout.addWidget(self.combobox)
        self.layout.addWidget(self.comboBox_lamella)
        self.layout.addWidget(self.button)

        self.setLayout(self.layout)

        # update table
        self._update_table()

        # callback when table data changed
        self.table.model().dataChanged.connect(self._on_data_changed)


    def _update_table(self):

        data = self.exp._create_protocol_dataframe()

        # filter to only show trench
        if self.checkBox.isChecked():
            key = self.combobox.currentText()
            data = data[data["WorkflowStage"] == key]

        # filter to only show lamella
        if self.checkBox_lamella.isChecked():
            key = self.comboBox_lamella.currentText()
            data = data[data["Lamella"] == key]

        # drop na columns
        data = data.dropna(axis=1, how="all")

        self.model = PandasModel(data)
        self.table.setModel(self.model) 





    def handleButton(self):
        print("Printing model to console...")
        
        print(self.model._data)

        print("Done.")

        self.exp._convert_dataframe_to_protocol(self.model._data)


    def _on_data_changed(self, index):
        print("data changed")
        print(index.row(), index.column(), index.data())


def main():
    PATH = "/home/patrick/github/autolamella/autolamella/test_exp"
    experiment = Experiment.load(os.path.join(PATH, "DEV-TEST-PROTOCOL-TABLE-01", "experiment.yaml"))

    app = QApplication(sys.argv)
    window = AutoLamellaProtocolUI(experiment=experiment)
    window.show()
    app.exec_()

if __name__ == "__main__":
    main()