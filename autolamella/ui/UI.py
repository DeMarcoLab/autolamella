# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'UI.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(920, 989)
        MainWindow.setBaseSize(QtCore.QSize(0, 100))
        MainWindow.setWindowOpacity(1.0)
        MainWindow.setAutoFillBackground(True)
        MainWindow.setStyleSheet("")
        MainWindow.setDocumentMode(False)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.formLayout_3 = QtWidgets.QFormLayout(self.centralwidget)
        self.formLayout_3.setObjectName("formLayout_3")
        self.tabWidget_2 = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget_2.setObjectName("tabWidget_2")
        self.tab_3 = QtWidgets.QWidget()
        self.tab_3.setObjectName("tab_3")
        self.formLayout = QtWidgets.QFormLayout(self.tab_3)
        self.formLayout.setObjectName("formLayout")
        self.label_3 = QtWidgets.QLabel(self.tab_3)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_3.setFont(font)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.log_txt = QtWidgets.QPlainTextEdit(self.tab_3)
        self.log_txt.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.log_txt.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.log_txt.setObjectName("log_txt")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.SpanningRole, self.log_txt)
        self.tabWidget_2.addTab(self.tab_3, "")
        self.tab_5 = QtWidgets.QWidget()
        self.tab_5.setObjectName("tab_5")
        self.verticalLayoutWidget = QtWidgets.QWidget(self.tab_5)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 0, 421, 261))
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.instructions_textEdit = QtWidgets.QPlainTextEdit(self.verticalLayoutWidget)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.instructions_textEdit.setFont(font)
        self.instructions_textEdit.setLineWidth(2)
        self.instructions_textEdit.setReadOnly(True)
        self.instructions_textEdit.setObjectName("instructions_textEdit")
        self.verticalLayout.addWidget(self.instructions_textEdit)
        self.tabWidget_2.addTab(self.tab_5, "")
        self.formLayout_3.setWidget(1, QtWidgets.QFormLayout.SpanningRole, self.tabWidget_2)
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.label_7 = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_7.setFont(font)
        self.label_7.setObjectName("label_7")
        self.gridLayout_3.addWidget(self.label_7, 2, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_3.addItem(spacerItem, 16, 0, 1, 2)
        self.show_lamella = QtWidgets.QCheckBox(self.tab)
        self.show_lamella.setChecked(False)
        self.show_lamella.setTristate(False)
        self.show_lamella.setObjectName("show_lamella")
        self.gridLayout_3.addWidget(self.show_lamella, 3, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem1, 14, 0, 1, 2)
        self.comboBox_moving_pattern = QtWidgets.QComboBox(self.tab)
        self.comboBox_moving_pattern.setObjectName("comboBox_moving_pattern")
        self.comboBox_moving_pattern.addItem("")
        self.comboBox_moving_pattern.addItem("")
        self.gridLayout_3.addWidget(self.comboBox_moving_pattern, 8, 1, 1, 1)
        self.label_8 = QtWidgets.QLabel(self.tab)
        self.label_8.setObjectName("label_8")
        self.gridLayout_3.addWidget(self.label_8, 1, 0, 1, 1)
        self.add_button = QtWidgets.QPushButton(self.tab)
        self.add_button.setObjectName("add_button")
        self.gridLayout_3.addWidget(self.add_button, 5, 0, 1, 1)
        self.protocol_txt = QtWidgets.QLabel(self.tab)
        self.protocol_txt.setText("")
        self.protocol_txt.setObjectName("protocol_txt")
        self.gridLayout_3.addWidget(self.protocol_txt, 1, 1, 1, 1)
        self.microexpansionCheckBox = QtWidgets.QCheckBox(self.tab)
        self.microexpansionCheckBox.setObjectName("microexpansionCheckBox")
        self.gridLayout_3.addWidget(self.microexpansionCheckBox, 3, 1, 1, 1)
        self.label_11 = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_11.setFont(font)
        self.label_11.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_11.setObjectName("label_11")
        self.gridLayout_3.addWidget(self.label_11, 0, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.tab)
        self.label_2.setObjectName("label_2")
        self.gridLayout_3.addWidget(self.label_2, 9, 0, 1, 2)
        self.save_button = QtWidgets.QPushButton(self.tab)
        self.save_button.setObjectName("save_button")
        self.gridLayout_3.addWidget(self.save_button, 10, 0, 1, 2)
        self.label_4 = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_4.setFont(font)
        self.label_4.setObjectName("label_4")
        self.gridLayout_3.addWidget(self.label_4, 6, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.tab)
        self.label.setObjectName("label")
        self.gridLayout_3.addWidget(self.label, 8, 0, 1, 1)
        self.remove_button = QtWidgets.QPushButton(self.tab)
        self.remove_button.setStyleSheet("")
        self.remove_button.setObjectName("remove_button")
        self.gridLayout_3.addWidget(self.remove_button, 5, 1, 1, 1)
        self.run_button = QtWidgets.QPushButton(self.tab)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.run_button.setFont(font)
        self.run_button.setStyleSheet("background-color: darkGreen")
        self.run_button.setObjectName("run_button")
        self.gridLayout_3.addWidget(self.run_button, 15, 0, 1, 2)
        self.lamella_count_txt = QtWidgets.QPlainTextEdit(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.MinimumExpanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lamella_count_txt.sizePolicy().hasHeightForWidth())
        self.lamella_count_txt.setSizePolicy(sizePolicy)
        self.lamella_count_txt.setMaximumSize(QtCore.QSize(16777215, 100))
        self.lamella_count_txt.setBaseSize(QtCore.QSize(0, 100))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.lamella_count_txt.setFont(font)
        self.lamella_count_txt.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.lamella_count_txt.setObjectName("lamella_count_txt")
        self.gridLayout_3.addWidget(self.lamella_count_txt, 12, 0, 1, 2)
        spacerItem2 = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_3.addItem(spacerItem2, 4, 0, 1, 2)
        self.remill_fiducial = QtWidgets.QPushButton(self.tab)
        self.remill_fiducial.setObjectName("remill_fiducial")
        self.gridLayout_3.addWidget(self.remill_fiducial, 13, 0, 1, 2)
        self.go_to_lamella = QtWidgets.QPushButton(self.tab)
        self.go_to_lamella.setObjectName("go_to_lamella")
        self.gridLayout_3.addWidget(self.go_to_lamella, 11, 0, 1, 2)
        self.lamella_index = QtWidgets.QComboBox(self.tab)
        self.lamella_index.setObjectName("lamella_index")
        self.gridLayout_3.addWidget(self.lamella_index, 6, 1, 1, 1)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.formLayout_2 = QtWidgets.QFormLayout(self.tab_2)
        self.formLayout_2.setObjectName("formLayout_2")
        self.application_file_label = QtWidgets.QLabel(self.tab_2)
        self.application_file_label.setObjectName("application_file_label")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.application_file_label)
        self.comboBoxapplication_file = QtWidgets.QComboBox(self.tab_2)
        self.comboBoxapplication_file.setObjectName("comboBoxapplication_file")
        self.formLayout_2.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.comboBoxapplication_file)
        self.beamShiftAttemptsLabel = QtWidgets.QLabel(self.tab_2)
        self.beamShiftAttemptsLabel.setObjectName("beamShiftAttemptsLabel")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.beamShiftAttemptsLabel)
        self.beamshift_attempts = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.beamshift_attempts.setObjectName("beamshift_attempts")
        self.formLayout_2.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.beamshift_attempts)
        self.scanDirectionLabel = QtWidgets.QLabel(self.tab_2)
        self.scanDirectionLabel.setObjectName("scanDirectionLabel")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.scanDirectionLabel)
        self.scanDirectionComboBox = QtWidgets.QComboBox(self.tab_2)
        self.scanDirectionComboBox.setObjectName("scanDirectionComboBox")
        self.formLayout_2.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.scanDirectionComboBox)
        self.fiducial_length = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.fiducial_length.setMaximum(1000.0)
        self.fiducial_length.setObjectName("fiducial_length")
        self.formLayout_2.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.fiducial_length)
        self.lengthLabel = QtWidgets.QLabel(self.tab_2)
        self.lengthLabel.setObjectName("lengthLabel")
        self.formLayout_2.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.lengthLabel)
        self.widthLabel = QtWidgets.QLabel(self.tab_2)
        self.widthLabel.setObjectName("widthLabel")
        self.formLayout_2.setWidget(6, QtWidgets.QFormLayout.LabelRole, self.widthLabel)
        self.width_fiducial = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.width_fiducial.setMaximum(1000.0)
        self.width_fiducial.setObjectName("width_fiducial")
        self.formLayout_2.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.width_fiducial)
        self.depthLabel = QtWidgets.QLabel(self.tab_2)
        self.depthLabel.setObjectName("depthLabel")
        self.formLayout_2.setWidget(7, QtWidgets.QFormLayout.LabelRole, self.depthLabel)
        self.depth_fiducial = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.depth_fiducial.setMaximum(1000.0)
        self.depth_fiducial.setObjectName("depth_fiducial")
        self.formLayout_2.setWidget(7, QtWidgets.QFormLayout.FieldRole, self.depth_fiducial)
        self.millingCurrentLabel = QtWidgets.QLabel(self.tab_2)
        self.millingCurrentLabel.setObjectName("millingCurrentLabel")
        self.formLayout_2.setWidget(8, QtWidgets.QFormLayout.LabelRole, self.millingCurrentLabel)
        self.current_fiducial = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.current_fiducial.setMaximum(1000.0)
        self.current_fiducial.setObjectName("current_fiducial")
        self.formLayout_2.setWidget(8, QtWidgets.QFormLayout.FieldRole, self.current_fiducial)
        self.presetLabel_2 = QtWidgets.QLabel(self.tab_2)
        self.presetLabel_2.setObjectName("presetLabel_2")
        self.formLayout_2.setWidget(10, QtWidgets.QFormLayout.LabelRole, self.presetLabel_2)
        self.presetComboBox_fiducial = QtWidgets.QComboBox(self.tab_2)
        self.presetComboBox_fiducial.setObjectName("presetComboBox_fiducial")
        self.formLayout_2.setWidget(10, QtWidgets.QFormLayout.FieldRole, self.presetComboBox_fiducial)
        self.label_5 = QtWidgets.QLabel(self.tab_2)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")
        self.formLayout_2.setWidget(4, QtWidgets.QFormLayout.SpanningRole, self.label_5)
        self.label_9 = QtWidgets.QLabel(self.tab_2)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_9.setFont(font)
        self.label_9.setObjectName("label_9")
        self.formLayout_2.setWidget(11, QtWidgets.QFormLayout.SpanningRole, self.label_9)
        self.stageLabel = QtWidgets.QLabel(self.tab_2)
        self.stageLabel.setObjectName("stageLabel")
        self.formLayout_2.setWidget(13, QtWidgets.QFormLayout.LabelRole, self.stageLabel)
        self.stage_lamella = QtWidgets.QComboBox(self.tab_2)
        self.stage_lamella.setObjectName("stage_lamella")
        self.stage_lamella.addItem("")
        self.stage_lamella.addItem("")
        self.stage_lamella.addItem("")
        self.formLayout_2.setWidget(13, QtWidgets.QFormLayout.FieldRole, self.stage_lamella)
        self.widthLabel_2 = QtWidgets.QLabel(self.tab_2)
        self.widthLabel_2.setObjectName("widthLabel_2")
        self.formLayout_2.setWidget(14, QtWidgets.QFormLayout.LabelRole, self.widthLabel_2)
        self.lamella_width = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.lamella_width.setMaximum(1000.0)
        self.lamella_width.setObjectName("lamella_width")
        self.formLayout_2.setWidget(14, QtWidgets.QFormLayout.FieldRole, self.lamella_width)
        self.heightLabel = QtWidgets.QLabel(self.tab_2)
        self.heightLabel.setObjectName("heightLabel")
        self.formLayout_2.setWidget(15, QtWidgets.QFormLayout.LabelRole, self.heightLabel)
        self.lamella_height = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.lamella_height.setMaximum(1000.0)
        self.lamella_height.setObjectName("lamella_height")
        self.formLayout_2.setWidget(15, QtWidgets.QFormLayout.FieldRole, self.lamella_height)
        self.trenchHeightLabel = QtWidgets.QLabel(self.tab_2)
        self.trenchHeightLabel.setObjectName("trenchHeightLabel")
        self.formLayout_2.setWidget(16, QtWidgets.QFormLayout.LabelRole, self.trenchHeightLabel)
        self.trench_height = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.trench_height.setMaximum(1000.0)
        self.trench_height.setObjectName("trench_height")
        self.formLayout_2.setWidget(16, QtWidgets.QFormLayout.FieldRole, self.trench_height)
        self.millingDepthLabel = QtWidgets.QLabel(self.tab_2)
        self.millingDepthLabel.setObjectName("millingDepthLabel")
        self.formLayout_2.setWidget(17, QtWidgets.QFormLayout.LabelRole, self.millingDepthLabel)
        self.depth_trench = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.depth_trench.setMaximum(1000.0)
        self.depth_trench.setObjectName("depth_trench")
        self.formLayout_2.setWidget(17, QtWidgets.QFormLayout.FieldRole, self.depth_trench)
        self.offsetLabel = QtWidgets.QLabel(self.tab_2)
        self.offsetLabel.setObjectName("offsetLabel")
        self.formLayout_2.setWidget(18, QtWidgets.QFormLayout.LabelRole, self.offsetLabel)
        self.offset = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.offset.setObjectName("offset")
        self.formLayout_2.setWidget(18, QtWidgets.QFormLayout.FieldRole, self.offset)
        self.sizeRatioLabel = QtWidgets.QLabel(self.tab_2)
        self.sizeRatioLabel.setObjectName("sizeRatioLabel")
        self.formLayout_2.setWidget(19, QtWidgets.QFormLayout.LabelRole, self.sizeRatioLabel)
        self.size_ratio = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.size_ratio.setObjectName("size_ratio")
        self.formLayout_2.setWidget(19, QtWidgets.QFormLayout.FieldRole, self.size_ratio)
        self.millingCurrentLabel_2 = QtWidgets.QLabel(self.tab_2)
        self.millingCurrentLabel_2.setObjectName("millingCurrentLabel_2")
        self.formLayout_2.setWidget(20, QtWidgets.QFormLayout.LabelRole, self.millingCurrentLabel_2)
        self.current_lamella = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.current_lamella.setMaximum(1000.0)
        self.current_lamella.setObjectName("current_lamella")
        self.formLayout_2.setWidget(20, QtWidgets.QFormLayout.FieldRole, self.current_lamella)
        self.presetLabel = QtWidgets.QLabel(self.tab_2)
        self.presetLabel.setObjectName("presetLabel")
        self.formLayout_2.setWidget(21, QtWidgets.QFormLayout.LabelRole, self.presetLabel)
        self.presetComboBox = QtWidgets.QComboBox(self.tab_2)
        self.presetComboBox.setObjectName("presetComboBox")
        self.formLayout_2.setWidget(21, QtWidgets.QFormLayout.FieldRole, self.presetComboBox)
        self.label_10 = QtWidgets.QLabel(self.tab_2)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_10.setFont(font)
        self.label_10.setObjectName("label_10")
        self.formLayout_2.setWidget(22, QtWidgets.QFormLayout.SpanningRole, self.label_10)
        self.widthLabel_3 = QtWidgets.QLabel(self.tab_2)
        self.widthLabel_3.setObjectName("widthLabel_3")
        self.formLayout_2.setWidget(23, QtWidgets.QFormLayout.LabelRole, self.widthLabel_3)
        self.micro_exp_width = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.micro_exp_width.setMaximum(1000.0)
        self.micro_exp_width.setObjectName("micro_exp_width")
        self.formLayout_2.setWidget(23, QtWidgets.QFormLayout.FieldRole, self.micro_exp_width)
        self.heightLabel_2 = QtWidgets.QLabel(self.tab_2)
        self.heightLabel_2.setObjectName("heightLabel_2")
        self.formLayout_2.setWidget(24, QtWidgets.QFormLayout.LabelRole, self.heightLabel_2)
        self.micro_exp_height = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.micro_exp_height.setMaximum(1000.0)
        self.micro_exp_height.setObjectName("micro_exp_height")
        self.formLayout_2.setWidget(24, QtWidgets.QFormLayout.FieldRole, self.micro_exp_height)
        self.distanceLabel = QtWidgets.QLabel(self.tab_2)
        self.distanceLabel.setObjectName("distanceLabel")
        self.formLayout_2.setWidget(25, QtWidgets.QFormLayout.LabelRole, self.distanceLabel)
        self.micro_exp_distance = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.micro_exp_distance.setMaximum(10000.0)
        self.micro_exp_distance.setObjectName("micro_exp_distance")
        self.formLayout_2.setWidget(25, QtWidgets.QFormLayout.FieldRole, self.micro_exp_distance)
        self.export_protocol = QtWidgets.QPushButton(self.tab_2)
        self.export_protocol.setObjectName("export_protocol")
        self.formLayout_2.setWidget(26, QtWidgets.QFormLayout.SpanningRole, self.export_protocol)
        self.label_6 = QtWidgets.QLabel(self.tab_2)
        self.label_6.setObjectName("label_6")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.label_6)
        self.comboBox_current_alignment = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_current_alignment.setObjectName("comboBox_current_alignment")
        self.formLayout_2.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.comboBox_current_alignment)
        self.tabWidget.addTab(self.tab_2, "")
        self.formLayout_3.setWidget(0, QtWidgets.QFormLayout.SpanningRole, self.tabWidget)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 920, 21))
        self.menubar.setObjectName("menubar")
        self.menuAutoLamella = QtWidgets.QMenu(self.menubar)
        self.menuAutoLamella.setObjectName("menuAutoLamella")
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.create_exp = QtWidgets.QAction(MainWindow)
        self.create_exp.setObjectName("create_exp")
        self.load_exp = QtWidgets.QAction(MainWindow)
        self.load_exp.setObjectName("load_exp")
        self.platinum = QtWidgets.QAction(MainWindow)
        self.platinum.setObjectName("platinum")
        self.action_load_protocol = QtWidgets.QAction(MainWindow)
        self.action_load_protocol.setObjectName("action_load_protocol")
        self.menuAutoLamella.addAction(self.create_exp)
        self.menuAutoLamella.addAction(self.load_exp)
        self.menuAutoLamella.addAction(self.action_load_protocol)
        self.menuTools.addAction(self.platinum)
        self.menubar.addAction(self.menuAutoLamella.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget_2.setCurrentIndex(1)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_3.setText(_translate("MainWindow", "Console Log"))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_3), _translate("MainWindow", "Log"))
        self.instructions_textEdit.setPlainText(_translate("MainWindow", "1. Create experiment (file menu) \n"
"2. Take images \n"
"3. Modify protocol if needed\n"
"4. Add lamella\n"
"5. Move to region of interest on the sample\n"
"6. Adjust lamella and fiducial positions\n"
"7. Save lamella\n"
"8. Check fiducial milling\n"
"9. Repeat 3-8 as needed\n"
"10. Run autolamella\n"
""))
        self.tabWidget_2.setTabText(self.tabWidget_2.indexOf(self.tab_5), _translate("MainWindow", "Instructions"))
        self.label_7.setText(_translate("MainWindow", "Setup"))
        self.show_lamella.setText(_translate("MainWindow", "Show Lamella Pattern"))
        self.comboBox_moving_pattern.setItemText(0, _translate("MainWindow", "Fiducial"))
        self.comboBox_moving_pattern.setItemText(1, _translate("MainWindow", "Lamella"))
        self.label_8.setText(_translate("MainWindow", "Protocol Name"))
        self.add_button.setText(_translate("MainWindow", "Add Lamella"))
        self.microexpansionCheckBox.setText(_translate("MainWindow", "Microexpansion Joints"))
        self.label_11.setText(_translate("MainWindow", "Autolamella"))
        self.label_2.setText(_translate("MainWindow", "Right click where you want the pattern centre to be."))
        self.save_button.setText(_translate("MainWindow", "Mill fiducila for current lamella"))
        self.label_4.setText(_translate("MainWindow", "Current Lamella"))
        self.label.setText(_translate("MainWindow", "Moving pattern :"))
        self.remove_button.setText(_translate("MainWindow", "Remove Lamella"))
        self.run_button.setText(_translate("MainWindow", "Run Autolamella"))
        self.remill_fiducial.setText(_translate("MainWindow", "Remill fiducial"))
        self.go_to_lamella.setText(_translate("MainWindow", "Go to position"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Experiment"))
        self.application_file_label.setText(_translate("MainWindow", "Application file"))
        self.beamShiftAttemptsLabel.setText(_translate("MainWindow", "Beam shift attempts"))
        self.scanDirectionLabel.setText(_translate("MainWindow", "Scan Direction"))
        self.lengthLabel.setText(_translate("MainWindow", "Length (µm)"))
        self.widthLabel.setText(_translate("MainWindow", "Width (µm)"))
        self.depthLabel.setText(_translate("MainWindow", "Depth (µm)"))
        self.millingCurrentLabel.setText(_translate("MainWindow", "Milling current (nA)"))
        self.presetLabel_2.setText(_translate("MainWindow", "Preset"))
        self.label_5.setText(_translate("MainWindow", "Fiducial Parameters"))
        self.label_9.setText(_translate("MainWindow", "Lamella Parameters "))
        self.stageLabel.setText(_translate("MainWindow", "Stage"))
        self.stage_lamella.setItemText(0, _translate("MainWindow", "1. Rough Cut"))
        self.stage_lamella.setItemText(1, _translate("MainWindow", "2. Regular Cut"))
        self.stage_lamella.setItemText(2, _translate("MainWindow", "3. Polishing Cut"))
        self.widthLabel_2.setText(_translate("MainWindow", "Lamella width (µm)"))
        self.heightLabel.setText(_translate("MainWindow", "Lamella height (µm)"))
        self.trenchHeightLabel.setText(_translate("MainWindow", "Trench height (µm)"))
        self.millingDepthLabel.setText(_translate("MainWindow", "Milling depth (µm)"))
        self.offsetLabel.setText(_translate("MainWindow", "Offset (µm)"))
        self.sizeRatioLabel.setText(_translate("MainWindow", "Size ratio"))
        self.millingCurrentLabel_2.setText(_translate("MainWindow", "Milling current (nA)"))
        self.presetLabel.setText(_translate("MainWindow", "Preset"))
        self.label_10.setText(_translate("MainWindow", "Microexpansion Joints Parameters"))
        self.widthLabel_3.setText(_translate("MainWindow", "Width (µm)"))
        self.heightLabel_2.setText(_translate("MainWindow", "Height (µm)"))
        self.distanceLabel.setText(_translate("MainWindow", "Distance (µm)"))
        self.export_protocol.setText(_translate("MainWindow", "Save protocol to file"))
        self.label_6.setText(_translate("MainWindow", "Align at:"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Protocol"))
        self.menuAutoLamella.setTitle(_translate("MainWindow", "File"))
        self.menuTools.setTitle(_translate("MainWindow", "Tools"))
        self.create_exp.setText(_translate("MainWindow", "Create Experiment"))
        self.load_exp.setText(_translate("MainWindow", "Load Experiment"))
        self.platinum.setText(_translate("MainWindow", "Splutter Platinum"))
        self.action_load_protocol.setText(_translate("MainWindow", "Load Protocol"))
