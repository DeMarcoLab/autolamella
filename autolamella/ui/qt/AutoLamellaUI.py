# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'AutoLamellaUI.ui'
#
# Created by: PyQt5 UI code generator 5.15.11
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(788, 1234)
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
        self.gridLayout.addWidget(self.label_instructions, 4, 0, 1, 2)
        self.label_title = QtWidgets.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_title.setObjectName("label_title")
        self.gridLayout.addWidget(self.label_title, 0, 0, 1, 2)
        self.label_workflow_information = QtWidgets.QLabel(self.centralwidget)
        self.label_workflow_information.setObjectName("label_workflow_information")
        self.gridLayout.addWidget(self.label_workflow_information, 3, 0, 1, 2)
        self.pushButton_no = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_no.setObjectName("pushButton_no")
        self.gridLayout.addWidget(self.pushButton_no, 5, 1, 1, 1)
        self.pushButton_yes = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_yes.setObjectName("pushButton_yes")
        self.gridLayout.addWidget(self.pushButton_yes, 5, 0, 1, 1)
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        self.pushButton_run_serial_liftout_landing = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_serial_liftout_landing.setObjectName("pushButton_run_serial_liftout_landing")
        self.gridLayout_3.addWidget(self.pushButton_run_serial_liftout_landing, 12, 0, 1, 2)
        self.label_experiment_name = QtWidgets.QLabel(self.tab)
        self.label_experiment_name.setObjectName("label_experiment_name")
        self.gridLayout_3.addWidget(self.label_experiment_name, 0, 0, 1, 2)
        self.pushButton_stop_workflow = QtWidgets.QPushButton(self.tab)
        self.pushButton_stop_workflow.setObjectName("pushButton_stop_workflow")
        self.gridLayout_3.addWidget(self.pushButton_stop_workflow, 36, 0, 1, 2)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_3.addItem(spacerItem, 7, 0, 1, 2)
        self.pushButton_run_setup_autolamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_setup_autolamella.setObjectName("pushButton_run_setup_autolamella")
        self.gridLayout_3.addWidget(self.pushButton_run_setup_autolamella, 13, 0, 1, 2)
        self.groupBox_setup = QtWidgets.QGroupBox(self.tab)
        self.groupBox_setup.setObjectName("groupBox_setup")
        self.gridLayout_5 = QtWidgets.QGridLayout(self.groupBox_setup)
        self.gridLayout_5.setObjectName("gridLayout_5")
        self.pushButton_add_lamella = QtWidgets.QPushButton(self.groupBox_setup)
        self.pushButton_add_lamella.setObjectName("pushButton_add_lamella")
        self.gridLayout_5.addWidget(self.pushButton_add_lamella, 0, 0, 1, 1)
        self.pushButton_remove_lamella = QtWidgets.QPushButton(self.groupBox_setup)
        self.pushButton_remove_lamella.setStyleSheet("")
        self.pushButton_remove_lamella.setObjectName("pushButton_remove_lamella")
        self.gridLayout_5.addWidget(self.pushButton_remove_lamella, 0, 1, 1, 1)
        self.gridLayout_3.addWidget(self.groupBox_setup, 2, 0, 1, 2)
        self.pushButton_setup_autoliftout = QtWidgets.QPushButton(self.tab)
        self.pushButton_setup_autoliftout.setObjectName("pushButton_setup_autoliftout")
        self.gridLayout_3.addWidget(self.pushButton_setup_autoliftout, 8, 0, 1, 2)
        self.label_protocol_name = QtWidgets.QLabel(self.tab)
        self.label_protocol_name.setObjectName("label_protocol_name")
        self.gridLayout_3.addWidget(self.label_protocol_name, 1, 0, 1, 2)
        self.pushButton_run_autoliftout = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_autoliftout.setObjectName("pushButton_run_autoliftout")
        self.gridLayout_3.addWidget(self.pushButton_run_autoliftout, 11, 0, 1, 2)
        self.groupBox_selected_lamella = QtWidgets.QGroupBox(self.tab)
        self.groupBox_selected_lamella.setObjectName("groupBox_selected_lamella")
        self.gridLayout_7 = QtWidgets.QGridLayout(self.groupBox_selected_lamella)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.comboBox_lamella_history = QtWidgets.QComboBox(self.groupBox_selected_lamella)
        self.comboBox_lamella_history.setObjectName("comboBox_lamella_history")
        self.gridLayout_7.addWidget(self.comboBox_lamella_history, 3, 0, 1, 1)
        self.label_current_lamella_header = QtWidgets.QLabel(self.groupBox_selected_lamella)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_current_lamella_header.setFont(font)
        self.label_current_lamella_header.setText("")
        self.label_current_lamella_header.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_current_lamella_header.setObjectName("label_current_lamella_header")
        self.gridLayout_7.addWidget(self.label_current_lamella_header, 0, 0, 1, 1)
        self.pushButton_lamella_landing_selected = QtWidgets.QPushButton(self.groupBox_selected_lamella)
        self.pushButton_lamella_landing_selected.setObjectName("pushButton_lamella_landing_selected")
        self.gridLayout_7.addWidget(self.pushButton_lamella_landing_selected, 2, 0, 1, 1)
        self.pushButton_save_position = QtWidgets.QPushButton(self.groupBox_selected_lamella)
        self.pushButton_save_position.setObjectName("pushButton_save_position")
        self.gridLayout_7.addWidget(self.pushButton_save_position, 1, 0, 1, 1)
        self.comboBox_current_lamella = QtWidgets.QComboBox(self.groupBox_selected_lamella)
        self.comboBox_current_lamella.setObjectName("comboBox_current_lamella")
        self.gridLayout_7.addWidget(self.comboBox_current_lamella, 0, 1, 1, 1)
        self.pushButton_go_to_lamella = QtWidgets.QPushButton(self.groupBox_selected_lamella)
        self.pushButton_go_to_lamella.setObjectName("pushButton_go_to_lamella")
        self.gridLayout_7.addWidget(self.pushButton_go_to_lamella, 1, 1, 1, 1)
        self.pushButton_fail_lamella = QtWidgets.QPushButton(self.groupBox_selected_lamella)
        self.pushButton_fail_lamella.setObjectName("pushButton_fail_lamella")
        self.gridLayout_7.addWidget(self.pushButton_fail_lamella, 2, 1, 1, 1)
        self.pushButton_revert_stage = QtWidgets.QPushButton(self.groupBox_selected_lamella)
        self.pushButton_revert_stage.setObjectName("pushButton_revert_stage")
        self.gridLayout_7.addWidget(self.pushButton_revert_stage, 3, 1, 1, 1)
        self.gridLayout_selected_lamella_history = QtWidgets.QGridLayout()
        self.gridLayout_selected_lamella_history.setObjectName("gridLayout_selected_lamella_history")
        self.gridLayout_7.addLayout(self.gridLayout_selected_lamella_history, 4, 0, 1, 2)
        self.gridLayout_3.addWidget(self.groupBox_selected_lamella, 4, 0, 1, 2)
        self.pushButton_run_waffle_trench = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_waffle_trench.setDefault(False)
        self.pushButton_run_waffle_trench.setFlat(False)
        self.pushButton_run_waffle_trench.setObjectName("pushButton_run_waffle_trench")
        self.gridLayout_3.addWidget(self.pushButton_run_waffle_trench, 9, 0, 1, 2)
        self.pushButton_run_waffle_undercut = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_waffle_undercut.setObjectName("pushButton_run_waffle_undercut")
        self.gridLayout_3.addWidget(self.pushButton_run_waffle_undercut, 10, 0, 1, 2)
        self.label_run_autolamella_info = QtWidgets.QLabel(self.tab)
        self.label_run_autolamella_info.setObjectName("label_run_autolamella_info")
        self.gridLayout_3.addWidget(self.label_run_autolamella_info, 14, 0, 1, 1)
        self.groupBox_lamella = QtWidgets.QGroupBox(self.tab)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_lamella.sizePolicy().hasHeightForWidth())
        self.groupBox_lamella.setSizePolicy(sizePolicy)
        self.groupBox_lamella.setObjectName("groupBox_lamella")
        self.gridLayout_6 = QtWidgets.QGridLayout(self.groupBox_lamella)
        self.gridLayout_6.setObjectName("gridLayout_6")
        self.scrollArea_lamella_info = QtWidgets.QScrollArea(self.groupBox_lamella)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea_lamella_info.sizePolicy().hasHeightForWidth())
        self.scrollArea_lamella_info.setSizePolicy(sizePolicy)
        self.scrollArea_lamella_info.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scrollArea_lamella_info.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.scrollArea_lamella_info.setWidgetResizable(True)
        self.scrollArea_lamella_info.setObjectName("scrollArea_lamella_info")
        self.scrollAreaWidgetContents_2 = QtWidgets.QWidget()
        self.scrollAreaWidgetContents_2.setGeometry(QtCore.QRect(0, 0, 722, 68))
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.gridLayout_8 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents_2)
        self.gridLayout_8.setObjectName("gridLayout_8")
        self.gridLayout_lamella_info = QtWidgets.QGridLayout()
        self.gridLayout_lamella_info.setObjectName("gridLayout_lamella_info")
        self.gridLayout_8.addLayout(self.gridLayout_lamella_info, 0, 0, 1, 1)
        self.scrollArea_lamella_info.setWidget(self.scrollAreaWidgetContents_2)
        self.gridLayout_6.addWidget(self.scrollArea_lamella_info, 0, 0, 1, 1)
        self.gridLayout_3.addWidget(self.groupBox_lamella, 5, 0, 1, 2)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.tab_2)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.pushButton_update_protocol = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_update_protocol.setObjectName("pushButton_update_protocol")
        self.gridLayout_2.addWidget(self.pushButton_update_protocol, 24, 0, 1, 2)
        self.scrollArea = QtWidgets.QScrollArea(self.tab_2)
        self.scrollArea.setMinimumSize(QtCore.QSize(0, 0))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 746, 632))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.label_options_landing_joining_method = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_options_landing_joining_method.setObjectName("label_options_landing_joining_method")
        self.gridLayout_4.addWidget(self.label_options_landing_joining_method, 10, 0, 1, 1)
        self.lineEdit_name = QtWidgets.QLineEdit(self.scrollAreaWidgetContents)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_name.sizePolicy().hasHeightForWidth())
        self.lineEdit_name.setSizePolicy(sizePolicy)
        self.lineEdit_name.setObjectName("lineEdit_name")
        self.gridLayout_4.addWidget(self.lineEdit_name, 0, 1, 1, 1)
        self.label_alignment_header = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        font = QtGui.QFont()
        font.setBold(True)
        font.setUnderline(False)
        font.setWeight(75)
        self.label_alignment_header.setFont(font)
        self.label_alignment_header.setObjectName("label_alignment_header")
        self.gridLayout_4.addWidget(self.label_alignment_header, 13, 0, 1, 1)
        self.comboBox_method = QtWidgets.QComboBox(self.scrollAreaWidgetContents)
        self.comboBox_method.setObjectName("comboBox_method")
        self.gridLayout_4.addWidget(self.comboBox_method, 1, 1, 1, 1)
        self.beamshift_attempts = QtWidgets.QDoubleSpinBox(self.scrollAreaWidgetContents)
        self.beamshift_attempts.setMinimum(-180.0)
        self.beamshift_attempts.setMaximum(180.0)
        self.beamshift_attempts.setObjectName("beamshift_attempts")
        self.gridLayout_4.addWidget(self.beamshift_attempts, 15, 1, 1, 1)
        self.checkBox_supervise_landing = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_supervise_landing.setEnabled(True)
        self.checkBox_supervise_landing.setObjectName("checkBox_supervise_landing")
        self.gridLayout_4.addWidget(self.checkBox_supervise_landing, 22, 0, 1, 1)
        self.beamShiftAttemptsLabel = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.beamShiftAttemptsLabel.setObjectName("beamShiftAttemptsLabel")
        self.gridLayout_4.addWidget(self.beamShiftAttemptsLabel, 15, 0, 1, 1)
        self.label_protocol_undercut_tilt_angle = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_protocol_undercut_tilt_angle.setObjectName("label_protocol_undercut_tilt_angle")
        self.gridLayout_4.addWidget(self.label_protocol_undercut_tilt_angle, 6, 0, 1, 1)
        self.checkBox_supervise_liftout = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_supervise_liftout.setEnabled(True)
        self.checkBox_supervise_liftout.setObjectName("checkBox_supervise_liftout")
        self.gridLayout_4.addWidget(self.checkBox_supervise_liftout, 21, 0, 1, 1)
        self.comboBox_options_trench_start_position = QtWidgets.QComboBox(self.scrollAreaWidgetContents)
        self.comboBox_options_trench_start_position.setObjectName("comboBox_options_trench_start_position")
        self.gridLayout_4.addWidget(self.comboBox_options_trench_start_position, 7, 1, 1, 1)
        self.label_supervise_header = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_supervise_header.setFont(font)
        self.label_supervise_header.setObjectName("label_supervise_header")
        self.gridLayout_4.addWidget(self.label_supervise_header, 18, 0, 1, 1)
        self.checkBox_use_microexpansion = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_use_microexpansion.setObjectName("checkBox_use_microexpansion")
        self.gridLayout_4.addWidget(self.checkBox_use_microexpansion, 11, 0, 1, 1)
        self.label_options_landing_start_position = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_options_landing_start_position.setObjectName("label_options_landing_start_position")
        self.gridLayout_4.addWidget(self.label_options_landing_start_position, 9, 0, 1, 1)
        self.label_protocol_method = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_protocol_method.setObjectName("label_protocol_method")
        self.gridLayout_4.addWidget(self.label_protocol_method, 1, 0, 1, 1)
        self.label_options_trench_start_position = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_options_trench_start_position.setObjectName("label_options_trench_start_position")
        self.gridLayout_4.addWidget(self.label_options_trench_start_position, 7, 0, 1, 1)
        self.checkBox_align_use_fiducial = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_align_use_fiducial.setObjectName("checkBox_align_use_fiducial")
        self.gridLayout_4.addWidget(self.checkBox_align_use_fiducial, 14, 0, 1, 1)
        self.checkBox_take_final_high_quality_reference = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_take_final_high_quality_reference.setObjectName("checkBox_take_final_high_quality_reference")
        self.gridLayout_4.addWidget(self.checkBox_take_final_high_quality_reference, 3, 1, 1, 1)
        self.comboBox_ml_checkpoint = QtWidgets.QComboBox(self.scrollAreaWidgetContents)
        self.comboBox_ml_checkpoint.setObjectName("comboBox_ml_checkpoint")
        self.gridLayout_4.addWidget(self.comboBox_ml_checkpoint, 17, 1, 1, 1)
        self.checkBox_undercut = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_undercut.setObjectName("checkBox_undercut")
        self.gridLayout_4.addWidget(self.checkBox_undercut, 20, 0, 1, 1)
        self.label_ml_checkpoint = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_ml_checkpoint.setObjectName("label_ml_checkpoint")
        self.gridLayout_4.addWidget(self.label_ml_checkpoint, 17, 0, 1, 1)
        self.checkBox_supervise_mill_polishing = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_supervise_mill_polishing.setObjectName("checkBox_supervise_mill_polishing")
        self.gridLayout_4.addWidget(self.checkBox_supervise_mill_polishing, 21, 1, 1, 1)
        self.label_options_header = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_options_header.setFont(font)
        self.label_options_header.setObjectName("label_options_header")
        self.gridLayout_4.addWidget(self.label_options_header, 2, 0, 1, 1)
        self.checkBox_trench = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_trench.setObjectName("checkBox_trench")
        self.gridLayout_4.addWidget(self.checkBox_trench, 19, 0, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_4.addItem(spacerItem1, 23, 0, 1, 2)
        self.comboBox_options_landing_start_position = QtWidgets.QComboBox(self.scrollAreaWidgetContents)
        self.comboBox_options_landing_start_position.setObjectName("comboBox_options_landing_start_position")
        self.gridLayout_4.addWidget(self.comboBox_options_landing_start_position, 9, 1, 1, 1)
        self.label_ml_header = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_ml_header.setFont(font)
        self.label_ml_header.setObjectName("label_ml_header")
        self.gridLayout_4.addWidget(self.label_ml_header, 16, 0, 1, 1)
        self.comboBox_options_liftout_joining_method = QtWidgets.QComboBox(self.scrollAreaWidgetContents)
        self.comboBox_options_liftout_joining_method.setObjectName("comboBox_options_liftout_joining_method")
        self.gridLayout_4.addWidget(self.comboBox_options_liftout_joining_method, 8, 1, 1, 1)
        self.checkBox_take_final_reference_images = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_take_final_reference_images.setObjectName("checkBox_take_final_reference_images")
        self.gridLayout_4.addWidget(self.checkBox_take_final_reference_images, 3, 0, 1, 1)
        self.label_lamella_tilt_angle = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_lamella_tilt_angle.setObjectName("label_lamella_tilt_angle")
        self.gridLayout_4.addWidget(self.label_lamella_tilt_angle, 12, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label.setFont(font)
        self.label.setObjectName("label")
        self.gridLayout_4.addWidget(self.label, 5, 0, 1, 2)
        self.doubleSpinBox_lamella_tilt_angle = QtWidgets.QDoubleSpinBox(self.scrollAreaWidgetContents)
        self.doubleSpinBox_lamella_tilt_angle.setMinimum(-180.0)
        self.doubleSpinBox_lamella_tilt_angle.setMaximum(180.0)
        self.doubleSpinBox_lamella_tilt_angle.setObjectName("doubleSpinBox_lamella_tilt_angle")
        self.gridLayout_4.addWidget(self.doubleSpinBox_lamella_tilt_angle, 12, 1, 1, 1)
        self.label_protocol_name_2 = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_protocol_name_2.setObjectName("label_protocol_name_2")
        self.gridLayout_4.addWidget(self.label_protocol_name_2, 0, 0, 1, 1)
        self.checkBox_supervise_mill_rough = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_supervise_mill_rough.setObjectName("checkBox_supervise_mill_rough")
        self.gridLayout_4.addWidget(self.checkBox_supervise_mill_rough, 20, 1, 1, 1)
        self.checkBox_align_at_milling_current = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_align_at_milling_current.setObjectName("checkBox_align_at_milling_current")
        self.gridLayout_4.addWidget(self.checkBox_align_at_milling_current, 14, 1, 1, 1)
        self.comboBox_options_landing_joining_method = QtWidgets.QComboBox(self.scrollAreaWidgetContents)
        self.comboBox_options_landing_joining_method.setObjectName("comboBox_options_landing_joining_method")
        self.gridLayout_4.addWidget(self.comboBox_options_landing_joining_method, 10, 1, 1, 1)
        self.label_options_liftout_joining_method = QtWidgets.QLabel(self.scrollAreaWidgetContents)
        self.label_options_liftout_joining_method.setObjectName("label_options_liftout_joining_method")
        self.gridLayout_4.addWidget(self.label_options_liftout_joining_method, 8, 0, 1, 1)
        self.doubleSpinBox_undercut_tilt = QtWidgets.QDoubleSpinBox(self.scrollAreaWidgetContents)
        self.doubleSpinBox_undercut_tilt.setMinimum(-180.0)
        self.doubleSpinBox_undercut_tilt.setMaximum(180.0)
        self.doubleSpinBox_undercut_tilt.setObjectName("doubleSpinBox_undercut_tilt")
        self.gridLayout_4.addWidget(self.doubleSpinBox_undercut_tilt, 6, 1, 1, 1)
        self.checkBox_use_notch = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_use_notch.setObjectName("checkBox_use_notch")
        self.gridLayout_4.addWidget(self.checkBox_use_notch, 11, 1, 1, 1)
        self.checkBox_setup = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_setup.setObjectName("checkBox_setup")
        self.gridLayout_4.addWidget(self.checkBox_setup, 19, 1, 1, 1)
        self.checkBox_turn_beams_off = QtWidgets.QCheckBox(self.scrollAreaWidgetContents)
        self.checkBox_turn_beams_off.setObjectName("checkBox_turn_beams_off")
        self.gridLayout_4.addWidget(self.checkBox_turn_beams_off, 4, 0, 1, 1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.gridLayout_2.addWidget(self.scrollArea, 0, 0, 1, 2)
        self.tabWidget.addTab(self.tab_2, "")
        self.gridLayout.addWidget(self.tabWidget, 1, 0, 1, 2)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem2, 2, 0, 1, 2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 788, 20))
        self.menubar.setObjectName("menubar")
        self.menuAutoLamella = QtWidgets.QMenu(self.menubar)
        self.menuAutoLamella.setObjectName("menuAutoLamella")
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        self.menuHelp = QtWidgets.QMenu(self.menubar)
        self.menuHelp.setObjectName("menuHelp")
        self.menuDevelopment = QtWidgets.QMenu(self.menubar)
        self.menuDevelopment.setObjectName("menuDevelopment")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.actionNew_Experiment = QtWidgets.QAction(MainWindow)
        self.actionNew_Experiment.setObjectName("actionNew_Experiment")
        self.actionLoad_Experiment = QtWidgets.QAction(MainWindow)
        self.actionLoad_Experiment.setObjectName("actionLoad_Experiment")
        self.actionCryo_Deposition = QtWidgets.QAction(MainWindow)
        self.actionCryo_Deposition.setObjectName("actionCryo_Deposition")
        self.actionLoad_Protocol = QtWidgets.QAction(MainWindow)
        self.actionLoad_Protocol.setObjectName("actionLoad_Protocol")
        self.actionLoad_Positions = QtWidgets.QAction(MainWindow)
        self.actionLoad_Positions.setObjectName("actionLoad_Positions")
        self.actionOpen_Minimap = QtWidgets.QAction(MainWindow)
        self.actionOpen_Minimap.setObjectName("actionOpen_Minimap")
        self.actionSave_Protocol = QtWidgets.QAction(MainWindow)
        self.actionSave_Protocol.setObjectName("actionSave_Protocol")
        self.actionLoad_Minimap_Image = QtWidgets.QAction(MainWindow)
        self.actionLoad_Minimap_Image.setObjectName("actionLoad_Minimap_Image")
        self.actionStop_Workflow = QtWidgets.QAction(MainWindow)
        self.actionStop_Workflow.setObjectName("actionStop_Workflow")
        self.actionLoad_Milling_Stage = QtWidgets.QAction(MainWindow)
        self.actionLoad_Milling_Stage.setObjectName("actionLoad_Milling_Stage")
        self.actionLoad_Milling_Pattern = QtWidgets.QAction(MainWindow)
        self.actionLoad_Milling_Pattern.setObjectName("actionLoad_Milling_Pattern")
        self.actionSave_Milling_Pattern = QtWidgets.QAction(MainWindow)
        self.actionSave_Milling_Pattern.setObjectName("actionSave_Milling_Pattern")
        self.actionInformation = QtWidgets.QAction(MainWindow)
        self.actionInformation.setObjectName("actionInformation")
        self.actionGenerate_Report = QtWidgets.QAction(MainWindow)
        self.actionGenerate_Report.setObjectName("actionGenerate_Report")
        self.actionGenerate_Overview_Plot = QtWidgets.QAction(MainWindow)
        self.actionGenerate_Overview_Plot.setObjectName("actionGenerate_Overview_Plot")
        self.actionSpot_Burn = QtWidgets.QAction(MainWindow)
        self.actionSpot_Burn.setObjectName("actionSpot_Burn")
        self.actionAdd_Lamella_from_Odemis = QtWidgets.QAction(MainWindow)
        self.actionAdd_Lamella_from_Odemis.setObjectName("actionAdd_Lamella_from_Odemis")
        self.actionUpdateMilling_Protocol = QtWidgets.QAction(MainWindow)
        self.actionUpdateMilling_Protocol.setObjectName("actionUpdateMilling_Protocol")
        self.actionRun_Spot_Burn_Workflow = QtWidgets.QAction(MainWindow)
        self.actionRun_Spot_Burn_Workflow.setObjectName("actionRun_Spot_Burn_Workflow")
        self.menuAutoLamella.addAction(self.actionNew_Experiment)
        self.menuAutoLamella.addAction(self.actionLoad_Experiment)
        self.menuAutoLamella.addSeparator()
        self.menuAutoLamella.addAction(self.actionLoad_Protocol)
        self.menuAutoLamella.addAction(self.actionSave_Protocol)
        self.menuAutoLamella.addAction(self.actionUpdateMilling_Protocol)
        self.menuTools.addAction(self.actionCryo_Deposition)
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.actionOpen_Minimap)
        self.menuTools.addAction(self.actionGenerate_Report)
        self.menuTools.addAction(self.actionGenerate_Overview_Plot)
        self.menuTools.addSeparator()
        self.menuHelp.addAction(self.actionInformation)
        self.menuDevelopment.addAction(self.actionAdd_Lamella_from_Odemis)
        self.menuDevelopment.addAction(self.actionSpot_Burn)
        self.menuDevelopment.addAction(self.actionRun_Spot_Burn_Workflow)
        self.menubar.addAction(self.menuAutoLamella.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())
        self.menubar.addAction(self.menuDevelopment.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_instructions.setText(_translate("MainWindow", "Instructions"))
        self.label_title.setText(_translate("MainWindow", "AutoLamella"))
        self.label_workflow_information.setText(_translate("MainWindow", "Workflow Information"))
        self.pushButton_no.setText(_translate("MainWindow", "No"))
        self.pushButton_yes.setText(_translate("MainWindow", "Yes"))
        self.pushButton_run_serial_liftout_landing.setText(_translate("MainWindow", "Run Landing Workflow"))
        self.label_experiment_name.setText(_translate("MainWindow", "Experiment:"))
        self.pushButton_stop_workflow.setText(_translate("MainWindow", "Stop Workflow"))
        self.pushButton_run_setup_autolamella.setText(_translate("MainWindow", "Run AutoLamella"))
        self.groupBox_setup.setTitle(_translate("MainWindow", "Setup"))
        self.pushButton_add_lamella.setText(_translate("MainWindow", "Add Lamella"))
        self.pushButton_remove_lamella.setText(_translate("MainWindow", "Remove Lamella"))
        self.pushButton_setup_autoliftout.setText(_translate("MainWindow", "Run Setup Liftout"))
        self.label_protocol_name.setText(_translate("MainWindow", "Protocol:"))
        self.pushButton_run_autoliftout.setText(_translate("MainWindow", "Run Liftout Workflow"))
        self.groupBox_selected_lamella.setTitle(_translate("MainWindow", "Selected Lamella"))
        self.pushButton_lamella_landing_selected.setText(_translate("MainWindow", "Landing Position Selected"))
        self.pushButton_save_position.setText(_translate("MainWindow", "Save Position"))
        self.pushButton_go_to_lamella.setText(_translate("MainWindow", "Go to Position"))
        self.pushButton_fail_lamella.setText(_translate("MainWindow", "Mark Lamella As Failed"))
        self.pushButton_revert_stage.setText(_translate("MainWindow", "Time Travel To"))
        self.pushButton_run_waffle_trench.setText(_translate("MainWindow", "Run Trench Milling"))
        self.pushButton_run_waffle_undercut.setText(_translate("MainWindow", "Run Undercut Milling"))
        self.label_run_autolamella_info.setText(_translate("MainWindow", "Run AutoLamella will run all workflows stages."))
        self.groupBox_lamella.setTitle(_translate("MainWindow", "Lamella"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Experiment"))
        self.pushButton_update_protocol.setText(_translate("MainWindow", "Update Protocol"))
        self.label_options_landing_joining_method.setText(_translate("MainWindow", "Landing Joining Method"))
        self.label_alignment_header.setText(_translate("MainWindow", "Alignment"))
        self.checkBox_supervise_landing.setText(_translate("MainWindow", "Land Lamella"))
        self.beamShiftAttemptsLabel.setText(_translate("MainWindow", "Alignment Attempts"))
        self.label_protocol_undercut_tilt_angle.setText(_translate("MainWindow", "Undercut Tilt Angle Per Step (deg)"))
        self.checkBox_supervise_liftout.setText(_translate("MainWindow", "Liftout Lamella"))
        self.label_supervise_header.setText(_translate("MainWindow", "Supervision"))
        self.checkBox_use_microexpansion.setText(_translate("MainWindow", "Use Microexpansion"))
        self.label_options_landing_start_position.setText(_translate("MainWindow", "Landing Start Position"))
        self.label_protocol_method.setText(_translate("MainWindow", "Method"))
        self.label_options_trench_start_position.setText(_translate("MainWindow", "Trench Start Position"))
        self.checkBox_align_use_fiducial.setText(_translate("MainWindow", "Use Fiducial"))
        self.checkBox_take_final_high_quality_reference.setText(_translate("MainWindow", "Acquire Final High Quality Image"))
        self.checkBox_undercut.setText(_translate("MainWindow", "Undercut Stage"))
        self.label_ml_checkpoint.setText(_translate("MainWindow", "Checkpoint"))
        self.checkBox_supervise_mill_polishing.setText(_translate("MainWindow", "Mill Polishing Stage"))
        self.label_options_header.setText(_translate("MainWindow", "Options"))
        self.checkBox_trench.setText(_translate("MainWindow", "Trench Stage"))
        self.label_ml_header.setText(_translate("MainWindow", "Machine Learning"))
        self.checkBox_take_final_reference_images.setText(_translate("MainWindow", "Acquire Final Reference Images"))
        self.label_lamella_tilt_angle.setText(_translate("MainWindow", "Lamella Tilt Angle (deg)"))
        self.label.setText(_translate("MainWindow", "Workflow"))
        self.label_protocol_name_2.setText(_translate("MainWindow", "Name"))
        self.checkBox_supervise_mill_rough.setText(_translate("MainWindow", "Mill Rough Stage"))
        self.checkBox_align_at_milling_current.setText(_translate("MainWindow", "Align at Milling Current"))
        self.label_options_liftout_joining_method.setText(_translate("MainWindow", "Liftout Joining Method"))
        self.checkBox_use_notch.setText(_translate("MainWindow", "Use Notch"))
        self.checkBox_setup.setText(_translate("MainWindow", "Setup Stage"))
        self.checkBox_turn_beams_off.setText(_translate("MainWindow", "Turn off beams when finished"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Protocol"))
        self.menuAutoLamella.setTitle(_translate("MainWindow", "File"))
        self.menuTools.setTitle(_translate("MainWindow", "Tools"))
        self.menuHelp.setTitle(_translate("MainWindow", "Help"))
        self.menuDevelopment.setTitle(_translate("MainWindow", "Development"))
        self.actionNew_Experiment.setText(_translate("MainWindow", "Create Experiment"))
        self.actionLoad_Experiment.setText(_translate("MainWindow", "Load Experiment"))
        self.actionCryo_Deposition.setText(_translate("MainWindow", "Cryo Deposition"))
        self.actionLoad_Protocol.setText(_translate("MainWindow", "Load Protocol"))
        self.actionLoad_Positions.setText(_translate("MainWindow", "Load Positions"))
        self.actionOpen_Minimap.setText(_translate("MainWindow", "Open Minimap"))
        self.actionSave_Protocol.setText(_translate("MainWindow", "Export Protocol"))
        self.actionLoad_Minimap_Image.setText(_translate("MainWindow", "Load Minimap Image"))
        self.actionStop_Workflow.setText(_translate("MainWindow", "Stop Workflow"))
        self.actionLoad_Milling_Stage.setText(_translate("MainWindow", "Load Milling Stage"))
        self.actionLoad_Milling_Pattern.setText(_translate("MainWindow", "Load Milling Pattern"))
        self.actionSave_Milling_Pattern.setText(_translate("MainWindow", "Save Milling Pattern"))
        self.actionInformation.setText(_translate("MainWindow", "Information"))
        self.actionGenerate_Report.setText(_translate("MainWindow", "Generate Report"))
        self.actionGenerate_Overview_Plot.setText(_translate("MainWindow", "Generate Overview Plot"))
        self.actionSpot_Burn.setText(_translate("MainWindow", "Spot Burn"))
        self.actionAdd_Lamella_from_Odemis.setText(_translate("MainWindow", "Add Lamella from Odemis"))
        self.actionUpdateMilling_Protocol.setText(_translate("MainWindow", "Update Milling Protocol"))
        self.actionRun_Spot_Burn_Workflow.setText(_translate("MainWindow", "Run Spot Burn Workflow"))
