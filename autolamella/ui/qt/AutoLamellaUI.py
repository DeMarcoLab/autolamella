# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AutoLamellaUI.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(521, 857)
        MainWindow.setBaseSize(QtCore.QSize(0, 100))
        MainWindow.setWindowOpacity(1.0)
        MainWindow.setAutoFillBackground(True)
        MainWindow.setStyleSheet("")
        MainWindow.setDocumentMode(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName("gridLayout")
        self.label_instructions = QtWidgets.QLabel(self.centralwidget)
        self.label_instructions.setObjectName("label_instructions")
        self.gridLayout.addWidget(self.label_instructions, 2, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 1, 0, 1, 2)
        self.pushButton_no = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_no.setObjectName("pushButton_no")
        self.gridLayout.addWidget(self.pushButton_no, 3, 1, 1, 1)
        self.pushButton_yes = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_yes.setObjectName("pushButton_yes")
        self.gridLayout.addWidget(self.pushButton_yes, 3, 0, 1, 1)
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.label_protocol_name = QtWidgets.QLabel(self.tab)
        self.label_protocol_name.setObjectName("label_protocol_name")
        self.gridLayout_3.addWidget(self.label_protocol_name, 2, 0, 1, 2)
        self.pushButton_run_waffle_trench = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_waffle_trench.setObjectName("pushButton_run_waffle_trench")
        self.gridLayout_3.addWidget(self.pushButton_run_waffle_trench, 15, 0, 1, 2)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_3.addItem(spacerItem1, 21, 0, 1, 2)
        self.label_experiment_name = QtWidgets.QLabel(self.tab)
        self.label_experiment_name.setObjectName("label_experiment_name")
        self.gridLayout_3.addWidget(self.label_experiment_name, 1, 0, 1, 2)
        self.label_title = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_title.setObjectName("label_title")
        self.gridLayout_3.addWidget(self.label_title, 0, 0, 1, 1)
        self.pushButton_add_lamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_add_lamella.setObjectName("pushButton_add_lamella")
        self.gridLayout_3.addWidget(self.pushButton_add_lamella, 7, 0, 1, 1)
        self.pushButton_run_autolamella = QtWidgets.QPushButton(self.tab)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.pushButton_run_autolamella.setFont(font)
        self.pushButton_run_autolamella.setStyleSheet("background-color: darkGreen")
        self.pushButton_run_autolamella.setObjectName("pushButton_run_autolamella")
        self.gridLayout_3.addWidget(self.pushButton_run_autolamella, 19, 0, 1, 2)
        self.pushButton_go_to_lamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_go_to_lamella.setObjectName("pushButton_go_to_lamella")
        self.gridLayout_3.addWidget(self.pushButton_go_to_lamella, 10, 1, 1, 1)
        self.label_info = QtWidgets.QLabel(self.tab)
        self.label_info.setObjectName("label_info")
        self.gridLayout_3.addWidget(self.label_info, 12, 0, 1, 2)
        self.comboBox_current_lamella = QtWidgets.QComboBox(self.tab)
        self.comboBox_current_lamella.setObjectName("comboBox_current_lamella")
        self.gridLayout_3.addWidget(self.comboBox_current_lamella, 8, 1, 1, 1)
        self.pushButton_remove_lamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_remove_lamella.setStyleSheet("")
        self.pushButton_remove_lamella.setObjectName("pushButton_remove_lamella")
        self.gridLayout_3.addWidget(self.pushButton_remove_lamella, 7, 1, 1, 1)
        self.label_current_lamella_header = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_current_lamella_header.setFont(font)
        self.label_current_lamella_header.setObjectName("label_current_lamella_header")
        self.gridLayout_3.addWidget(self.label_current_lamella_header, 8, 0, 1, 1)
        self.pushButton_run_waffle_undercut = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_waffle_undercut.setObjectName("pushButton_run_waffle_undercut")
        self.gridLayout_3.addWidget(self.pushButton_run_waffle_undercut, 16, 0, 1, 2)
        self.label_setup_header = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_setup_header.setFont(font)
        self.label_setup_header.setObjectName("label_setup_header")
        self.gridLayout_3.addWidget(self.label_setup_header, 3, 0, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_3.addItem(spacerItem2, 11, 0, 1, 2)
        self.pushButton_save_position = QtWidgets.QPushButton(self.tab)
        self.pushButton_save_position.setObjectName("pushButton_save_position")
        self.gridLayout_3.addWidget(self.pushButton_save_position, 10, 0, 1, 1)
        spacerItem3 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_3.addItem(spacerItem3, 13, 0, 1, 2)
        self.pushButton_run_setup_autolamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_setup_autolamella.setObjectName("pushButton_run_setup_autolamella")
        self.gridLayout_3.addWidget(self.pushButton_run_setup_autolamella, 17, 0, 1, 2)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.formLayout_2 = QtWidgets.QFormLayout(self.tab_2)
        self.formLayout_2.setObjectName("formLayout_2")
        self.label_4 = QtWidgets.QLabel(self.tab_2)
        self.label_4.setObjectName("label_4")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_4)
        self.comboBox_method = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_method.setObjectName("comboBox_method")
        self.comboBox_method.addItem("")
        self.comboBox_method.addItem("")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.comboBox_method)
        self.beamShiftAttemptsLabel = QtWidgets.QLabel(self.tab_2)
        self.beamShiftAttemptsLabel.setObjectName("beamShiftAttemptsLabel")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.beamShiftAttemptsLabel)
        self.beamshift_attempts = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.beamshift_attempts.setObjectName("beamshift_attempts")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.beamshift_attempts)
        self.label_6 = QtWidgets.QLabel(self.tab_2)
        self.label_6.setObjectName("label_6")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_6)
        self.comboBox_current_alignment = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_current_alignment.setObjectName("comboBox_current_alignment")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.comboBox_current_alignment)
        self.label = QtWidgets.QLabel(self.tab_2)
        self.label.setObjectName("label")
        self.formLayout_2.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.label)
        self.doubleSpinBox_undercut_tilt = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.doubleSpinBox_undercut_tilt.setMinimum(-180.0)
        self.doubleSpinBox_undercut_tilt.setMaximum(180.0)
        self.doubleSpinBox_undercut_tilt.setObjectName("doubleSpinBox_undercut_tilt")
        self.formLayout_2.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.doubleSpinBox_undercut_tilt)
        self.label_2 = QtWidgets.QLabel(self.tab_2)
        self.label_2.setObjectName("label_2")
        self.formLayout_2.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.doubleSpinBox_undercut_step = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.doubleSpinBox_undercut_step.setMinimum(-180.0)
        self.doubleSpinBox_undercut_step.setMaximum(180.0)
        self.doubleSpinBox_undercut_step.setObjectName("doubleSpinBox_undercut_step")
        self.formLayout_2.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.doubleSpinBox_undercut_step)
        self.label_3 = QtWidgets.QLabel(self.tab_2)
        self.label_3.setObjectName("label_3")
        self.formLayout_2.setWidget(6, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.comboBox_stress_relief = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_stress_relief.setObjectName("comboBox_stress_relief")
        self.comboBox_stress_relief.addItem("")
        self.comboBox_stress_relief.addItem("")
        self.formLayout_2.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.comboBox_stress_relief)
        self.label_5 = QtWidgets.QLabel(self.tab_2)
        self.label_5.setObjectName("label_5")
        self.formLayout_2.setWidget(8, QtWidgets.QFormLayout.SpanningRole, self.label_5)
        self.pushButton_update_protocol = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_update_protocol.setObjectName("pushButton_update_protocol")
        self.formLayout_2.setWidget(16, QtWidgets.QFormLayout.SpanningRole, self.pushButton_update_protocol)
        self.export_protocol = QtWidgets.QPushButton(self.tab_2)
        self.export_protocol.setObjectName("export_protocol")
        self.formLayout_2.setWidget(17, QtWidgets.QFormLayout.SpanningRole, self.export_protocol)
        self.checkBox_trench = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_trench.setObjectName("checkBox_trench")
        self.formLayout_2.setWidget(9, QtWidgets.QFormLayout.LabelRole, self.checkBox_trench)
        self.checkBox_undercut = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_undercut.setObjectName("checkBox_undercut")
        self.formLayout_2.setWidget(10, QtWidgets.QFormLayout.LabelRole, self.checkBox_undercut)
        self.checkBox_setup = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_setup.setObjectName("checkBox_setup")
        self.formLayout_2.setWidget(11, QtWidgets.QFormLayout.LabelRole, self.checkBox_setup)
        self.checkBox_features = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_features.setObjectName("checkBox_features")
        self.formLayout_2.setWidget(12, QtWidgets.QFormLayout.LabelRole, self.checkBox_features)
        self.checkBox_lamella = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_lamella.setObjectName("checkBox_lamella")
        self.formLayout_2.setWidget(13, QtWidgets.QFormLayout.LabelRole, self.checkBox_lamella)
        self.checkBox_fiducial = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_fiducial.setObjectName("checkBox_fiducial")
        self.formLayout_2.setWidget(7, QtWidgets.QFormLayout.LabelRole, self.checkBox_fiducial)
        self.label_7 = QtWidgets.QLabel(self.tab_2)
        self.label_7.setObjectName("label_7")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_7)
        self.lineEdit_name = QtWidgets.QLineEdit(self.tab_2)
        self.lineEdit_name.setObjectName("lineEdit_name")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.lineEdit_name)
        self.tabWidget.addTab(self.tab_2, "")
        self.gridLayout.addWidget(self.tabWidget, 0, 0, 1, 2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 521, 21))
        self.menubar.setObjectName("menubar")
        self.menuAutoLamella = QtWidgets.QMenu(self.menubar)
        self.menuAutoLamella.setObjectName("menuAutoLamella")
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionNew_Experiment = QtWidgets.QAction(MainWindow)
        self.actionNew_Experiment.setObjectName("actionNew_Experiment")
        self.actionLoad_Experiment = QtWidgets.QAction(MainWindow)
        self.actionLoad_Experiment.setObjectName("actionLoad_Experiment")
        self.actionCryo_Sputter = QtWidgets.QAction(MainWindow)
        self.actionCryo_Sputter.setObjectName("actionCryo_Sputter")
        self.actionLoad_Protocol = QtWidgets.QAction(MainWindow)
        self.actionLoad_Protocol.setObjectName("actionLoad_Protocol")
        self.actionLoad_Positions = QtWidgets.QAction(MainWindow)
        self.actionLoad_Positions.setObjectName("actionLoad_Positions")
        self.actionOpen_Minimap = QtWidgets.QAction(MainWindow)
        self.actionOpen_Minimap.setObjectName("actionOpen_Minimap")
        self.menuAutoLamella.addAction(self.actionNew_Experiment)
        self.menuAutoLamella.addAction(self.actionLoad_Experiment)
        self.menuAutoLamella.addAction(self.actionLoad_Protocol)
        self.menuTools.addAction(self.actionCryo_Sputter)
        self.menuTools.addAction(self.actionLoad_Positions)
        self.menuTools.addAction(self.actionOpen_Minimap)
        self.menubar.addAction(self.menuAutoLamella.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_instructions.setText(_translate("MainWindow", "Instructions"))
        self.pushButton_no.setText(_translate("MainWindow", "No"))
        self.pushButton_yes.setText(_translate("MainWindow", "Yes"))
        self.label_protocol_name.setText(_translate("MainWindow", "Protocol:"))
        self.pushButton_run_waffle_trench.setText(_translate("MainWindow", "Run Waffle Trench Milling"))
        self.label_experiment_name.setText(_translate("MainWindow", "Experiment:"))
        self.label_title.setText(_translate("MainWindow", "Autolamella"))
        self.pushButton_add_lamella.setText(_translate("MainWindow", "Add Lamella"))
        self.pushButton_run_autolamella.setText(_translate("MainWindow", "Run AutoLamella"))
        self.pushButton_go_to_lamella.setText(_translate("MainWindow", "Go to position"))
        self.label_info.setText(_translate("MainWindow", "No Lamella Selected"))
        self.pushButton_remove_lamella.setText(_translate("MainWindow", "Remove Lamella"))
        self.label_current_lamella_header.setText(_translate("MainWindow", "Current Lamella"))
        self.pushButton_run_waffle_undercut.setText(_translate("MainWindow", "Run Waffle Undercut Milling"))
        self.label_setup_header.setText(_translate("MainWindow", "Setup"))
        self.pushButton_save_position.setText(_translate("MainWindow", "Save Position"))
        self.pushButton_run_setup_autolamella.setText(_translate("MainWindow", "Run Setup AutoLamella"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Experiment"))
        self.label_4.setText(_translate("MainWindow", "Method"))
        self.comboBox_method.setItemText(0, _translate("MainWindow", "Default"))
        self.comboBox_method.setItemText(1, _translate("MainWindow", "Waffle"))
        self.beamShiftAttemptsLabel.setText(_translate("MainWindow", "Beam shift attempts"))
        self.label_6.setText(_translate("MainWindow", "Align at:"))
        self.label.setText(_translate("MainWindow", "Undercut Tilt Angle"))
        self.label_2.setText(_translate("MainWindow", "Undercut Tilt Step"))
        self.label_3.setText(_translate("MainWindow", "Stress Relief"))
        self.comboBox_stress_relief.setItemText(0, _translate("MainWindow", "Notch"))
        self.comboBox_stress_relief.setItemText(1, _translate("MainWindow", "Microexpansion "))
        self.label_5.setText(_translate("MainWindow", "Supervision"))
        self.pushButton_update_protocol.setText(_translate("MainWindow", "Update Protocol"))
        self.export_protocol.setText(_translate("MainWindow", "Save protocol to file"))
        self.checkBox_trench.setText(_translate("MainWindow", "Trench Stage"))
        self.checkBox_undercut.setText(_translate("MainWindow", "Undercut Stage"))
        self.checkBox_setup.setText(_translate("MainWindow", "Setup Stage"))
        self.checkBox_features.setText(_translate("MainWindow", "Features Stage"))
        self.checkBox_lamella.setText(_translate("MainWindow", "Lamella Stage"))
        self.checkBox_fiducial.setText(_translate("MainWindow", "Fiducial Enabled"))
        self.label_7.setText(_translate("MainWindow", "Name"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Protocol"))
        self.menuAutoLamella.setTitle(_translate("MainWindow", "File"))
        self.menuTools.setTitle(_translate("MainWindow", "Tools"))
        self.actionNew_Experiment.setText(_translate("MainWindow", "Create Experiment"))
        self.actionLoad_Experiment.setText(_translate("MainWindow", "Load Experiment"))
        self.actionCryo_Sputter.setText(_translate("MainWindow", "Cryo Sputter"))
        self.actionLoad_Protocol.setText(_translate("MainWindow", "Load Protocol"))
        self.actionLoad_Positions.setText(_translate("MainWindow", "Load Positions"))
        self.actionOpen_Minimap.setText(_translate("MainWindow", "Open Minimap"))
