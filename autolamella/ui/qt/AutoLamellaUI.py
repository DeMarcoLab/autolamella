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
        MainWindow.resize(563, 1002)
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
        self.gridLayout.addWidget(self.label_instructions, 3, 0, 1, 1)
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.gridLayout_3 = QtWidgets.QGridLayout(self.tab)
        self.gridLayout_3.setObjectName("gridLayout_3")
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_3.addItem(spacerItem, 16, 0, 1, 2)
        self.pushButton_revert_stage = QtWidgets.QPushButton(self.tab)
        self.pushButton_revert_stage.setObjectName("pushButton_revert_stage")
        self.gridLayout_3.addWidget(self.pushButton_revert_stage, 12, 1, 1, 1)
        self.comboBox_current_lamella = QtWidgets.QComboBox(self.tab)
        self.comboBox_current_lamella.setObjectName("comboBox_current_lamella")
        self.gridLayout_3.addWidget(self.comboBox_current_lamella, 8, 1, 1, 1)
        self.comboBox_lamella_history = QtWidgets.QComboBox(self.tab)
        self.comboBox_lamella_history.setObjectName("comboBox_lamella_history")
        self.gridLayout_3.addWidget(self.comboBox_lamella_history, 12, 0, 1, 1)
        self.pushButton_save_position = QtWidgets.QPushButton(self.tab)
        self.pushButton_save_position.setObjectName("pushButton_save_position")
        self.gridLayout_3.addWidget(self.pushButton_save_position, 10, 0, 1, 1)
        self.label_current_lamella_header = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_current_lamella_header.setFont(font)
        self.label_current_lamella_header.setObjectName("label_current_lamella_header")
        self.gridLayout_3.addWidget(self.label_current_lamella_header, 8, 0, 1, 1)
        self.pushButton_add_lamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_add_lamella.setObjectName("pushButton_add_lamella")
        self.gridLayout_3.addWidget(self.pushButton_add_lamella, 7, 0, 1, 1)
        self.pushButton_go_to_lamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_go_to_lamella.setObjectName("pushButton_go_to_lamella")
        self.gridLayout_3.addWidget(self.pushButton_go_to_lamella, 10, 1, 1, 1)
        self.pushButton_run_setup_autolamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_setup_autolamella.setObjectName("pushButton_run_setup_autolamella")
        self.gridLayout_3.addWidget(self.pushButton_run_setup_autolamella, 19, 0, 1, 2)
        self.label_setup_header = QtWidgets.QLabel(self.tab)
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(75)
        self.label_setup_header.setFont(font)
        self.label_setup_header.setObjectName("label_setup_header")
        self.gridLayout_3.addWidget(self.label_setup_header, 3, 0, 1, 1)
        self.pushButton_run_autolamella = QtWidgets.QPushButton(self.tab)
        palette = QtGui.QPalette()
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(170, 170, 170))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Active, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(170, 170, 170))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Inactive, QtGui.QPalette.PlaceholderText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.WindowText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Button, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Light, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Midlight, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Dark, brush)
        brush = QtGui.QBrush(QtGui.QColor(170, 170, 170))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Mid, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Text, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.BrightText, brush)
        brush = QtGui.QBrush(QtGui.QColor(127, 127, 127))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Base, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 100, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Window, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.Shadow, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 255))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.AlternateBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(255, 255, 220))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipBase, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.ToolTipText, brush)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0, 128))
        brush.setStyle(QtCore.Qt.SolidPattern)
        palette.setBrush(QtGui.QPalette.Disabled, QtGui.QPalette.PlaceholderText, brush)
        self.pushButton_run_autolamella.setPalette(palette)
        font = QtGui.QFont()
        font.setBold(False)
        font.setWeight(50)
        self.pushButton_run_autolamella.setFont(font)
        self.pushButton_run_autolamella.setStyleSheet("background-color: darkGreen")
        self.pushButton_run_autolamella.setAutoDefault(False)
        self.pushButton_run_autolamella.setDefault(False)
        self.pushButton_run_autolamella.setFlat(False)
        self.pushButton_run_autolamella.setObjectName("pushButton_run_autolamella")
        self.gridLayout_3.addWidget(self.pushButton_run_autolamella, 21, 0, 1, 2)
        self.pushButton_fail_lamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_fail_lamella.setObjectName("pushButton_fail_lamella")
        self.gridLayout_3.addWidget(self.pushButton_fail_lamella, 11, 1, 1, 1)
        self.label_experiment_name = QtWidgets.QLabel(self.tab)
        self.label_experiment_name.setObjectName("label_experiment_name")
        self.gridLayout_3.addWidget(self.label_experiment_name, 1, 0, 1, 2)
        self.pushButton_run_waffle_undercut = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_waffle_undercut.setObjectName("pushButton_run_waffle_undercut")
        self.gridLayout_3.addWidget(self.pushButton_run_waffle_undercut, 18, 0, 1, 2)
        self.pushButton_remove_lamella = QtWidgets.QPushButton(self.tab)
        self.pushButton_remove_lamella.setStyleSheet("")
        self.pushButton_remove_lamella.setObjectName("pushButton_remove_lamella")
        self.gridLayout_3.addWidget(self.pushButton_remove_lamella, 7, 1, 1, 1)
        self.label_info = QtWidgets.QLabel(self.tab)
        self.label_info.setObjectName("label_info")
        self.gridLayout_3.addWidget(self.label_info, 14, 0, 1, 2)
        self.label_protocol_name = QtWidgets.QLabel(self.tab)
        self.label_protocol_name.setObjectName("label_protocol_name")
        self.gridLayout_3.addWidget(self.label_protocol_name, 2, 0, 1, 2)
        self.pushButton_run_waffle_trench = QtWidgets.QPushButton(self.tab)
        self.pushButton_run_waffle_trench.setDefault(False)
        self.pushButton_run_waffle_trench.setFlat(False)
        self.pushButton_run_waffle_trench.setObjectName("pushButton_run_waffle_trench")
        self.gridLayout_3.addWidget(self.pushButton_run_waffle_trench, 17, 0, 1, 2)
        self.checkBox_show_lamella_in_view = QtWidgets.QCheckBox(self.tab)
        self.checkBox_show_lamella_in_view.setObjectName("checkBox_show_lamella_in_view")
        self.gridLayout_3.addWidget(self.checkBox_show_lamella_in_view, 13, 0, 1, 1)
        self.tabWidget.addTab(self.tab, "")
        self.tab_2 = QtWidgets.QWidget()
        self.tab_2.setObjectName("tab_2")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.tab_2)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.label_options_lamella_start_position = QtWidgets.QLabel(self.tab_2)
        self.label_options_lamella_start_position.setObjectName("label_options_lamella_start_position")
        self.gridLayout_2.addWidget(self.label_options_lamella_start_position, 7, 0, 1, 1)
        self.checkBox_supervise_liftout = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_supervise_liftout.setEnabled(True)
        self.checkBox_supervise_liftout.setObjectName("checkBox_supervise_liftout")
        self.gridLayout_2.addWidget(self.checkBox_supervise_liftout, 21, 0, 1, 1)
        self.checkBox_take_final_reference_images = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_take_final_reference_images.setObjectName("checkBox_take_final_reference_images")
        self.gridLayout_2.addWidget(self.checkBox_take_final_reference_images, 4, 0, 1, 1)
        self.label_options_landing_joining_method = QtWidgets.QLabel(self.tab_2)
        self.label_options_landing_joining_method.setObjectName("label_options_landing_joining_method")
        self.gridLayout_2.addWidget(self.label_options_landing_joining_method, 10, 0, 1, 1)
        self.checkBox_trench = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_trench.setObjectName("checkBox_trench")
        self.gridLayout_2.addWidget(self.checkBox_trench, 19, 0, 1, 1)
        self.label_options_liftout_joining_method = QtWidgets.QLabel(self.tab_2)
        self.label_options_liftout_joining_method.setObjectName("label_options_liftout_joining_method")
        self.gridLayout_2.addWidget(self.label_options_liftout_joining_method, 8, 0, 1, 1)
        self.label_protocol_undercut_tilt_angle = QtWidgets.QLabel(self.tab_2)
        self.label_protocol_undercut_tilt_angle.setObjectName("label_protocol_undercut_tilt_angle")
        self.gridLayout_2.addWidget(self.label_protocol_undercut_tilt_angle, 5, 0, 1, 1)
        self.doubleSpinBox_undercut_tilt = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.doubleSpinBox_undercut_tilt.setMinimum(-180.0)
        self.doubleSpinBox_undercut_tilt.setMaximum(180.0)
        self.doubleSpinBox_undercut_tilt.setObjectName("doubleSpinBox_undercut_tilt")
        self.gridLayout_2.addWidget(self.doubleSpinBox_undercut_tilt, 5, 1, 1, 1)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout_2.addItem(spacerItem1, 24, 0, 1, 2)
        self.comboBox_options_landing_joining_method = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_options_landing_joining_method.setObjectName("comboBox_options_landing_joining_method")
        self.gridLayout_2.addWidget(self.comboBox_options_landing_joining_method, 10, 1, 1, 1)
        self.checkBox_supervise_mill_polishing = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_supervise_mill_polishing.setObjectName("checkBox_supervise_mill_polishing")
        self.gridLayout_2.addWidget(self.checkBox_supervise_mill_polishing, 21, 1, 1, 1)
        self.label_protocol_undercut_tilt_step = QtWidgets.QLabel(self.tab_2)
        self.label_protocol_undercut_tilt_step.setObjectName("label_protocol_undercut_tilt_step")
        self.gridLayout_2.addWidget(self.label_protocol_undercut_tilt_step, 6, 0, 1, 1)
        self.beamShiftAttemptsLabel = QtWidgets.QLabel(self.tab_2)
        self.beamShiftAttemptsLabel.setObjectName("beamShiftAttemptsLabel")
        self.gridLayout_2.addWidget(self.beamShiftAttemptsLabel, 15, 0, 1, 1)
        self.label_options_landing_start_position = QtWidgets.QLabel(self.tab_2)
        self.label_options_landing_start_position.setObjectName("label_options_landing_start_position")
        self.gridLayout_2.addWidget(self.label_options_landing_start_position, 9, 0, 1, 1)
        self.checkBox_undercut = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_undercut.setObjectName("checkBox_undercut")
        self.gridLayout_2.addWidget(self.checkBox_undercut, 20, 0, 1, 1)
        self.lineEdit_name = QtWidgets.QLineEdit(self.tab_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_name.sizePolicy().hasHeightForWidth())
        self.lineEdit_name.setSizePolicy(sizePolicy)
        self.lineEdit_name.setObjectName("lineEdit_name")
        self.gridLayout_2.addWidget(self.lineEdit_name, 0, 1, 1, 1)
        self.pushButton_update_protocol = QtWidgets.QPushButton(self.tab_2)
        self.pushButton_update_protocol.setObjectName("pushButton_update_protocol")
        self.gridLayout_2.addWidget(self.pushButton_update_protocol, 23, 0, 1, 2)
        self.checkBox_setup = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_setup.setObjectName("checkBox_setup")
        self.gridLayout_2.addWidget(self.checkBox_setup, 19, 1, 1, 1)
        self.label_ml_header = QtWidgets.QLabel(self.tab_2)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_ml_header.setFont(font)
        self.label_ml_header.setObjectName("label_ml_header")
        self.gridLayout_2.addWidget(self.label_ml_header, 16, 0, 1, 1)
        self.checkBox_supervise_mill_rough = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_supervise_mill_rough.setObjectName("checkBox_supervise_mill_rough")
        self.gridLayout_2.addWidget(self.checkBox_supervise_mill_rough, 20, 1, 1, 1)
        self.label_supervise_header = QtWidgets.QLabel(self.tab_2)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_supervise_header.setFont(font)
        self.label_supervise_header.setObjectName("label_supervise_header")
        self.gridLayout_2.addWidget(self.label_supervise_header, 18, 0, 1, 1)
        self.doubleSpinBox_undercut_step = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.doubleSpinBox_undercut_step.setMinimum(-180.0)
        self.doubleSpinBox_undercut_step.setMaximum(180.0)
        self.doubleSpinBox_undercut_step.setObjectName("doubleSpinBox_undercut_step")
        self.gridLayout_2.addWidget(self.doubleSpinBox_undercut_step, 6, 1, 1, 1)
        self.comboBox_options_landing_start_position = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_options_landing_start_position.setObjectName("comboBox_options_landing_start_position")
        self.gridLayout_2.addWidget(self.comboBox_options_landing_start_position, 9, 1, 1, 1)
        self.label_protocol_name_2 = QtWidgets.QLabel(self.tab_2)
        self.label_protocol_name_2.setObjectName("label_protocol_name_2")
        self.gridLayout_2.addWidget(self.label_protocol_name_2, 0, 0, 1, 1)
        self.beamshift_attempts = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.beamshift_attempts.setMinimum(-180.0)
        self.beamshift_attempts.setMaximum(180.0)
        self.beamshift_attempts.setObjectName("beamshift_attempts")
        self.gridLayout_2.addWidget(self.beamshift_attempts, 15, 1, 1, 1)
        self.doubleSpinBox_lamella_tilt_angle = QtWidgets.QDoubleSpinBox(self.tab_2)
        self.doubleSpinBox_lamella_tilt_angle.setObjectName("doubleSpinBox_lamella_tilt_angle")
        self.gridLayout_2.addWidget(self.doubleSpinBox_lamella_tilt_angle, 12, 1, 1, 1)
        self.comboBox_options_lamella_start_position = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_options_lamella_start_position.setObjectName("comboBox_options_lamella_start_position")
        self.gridLayout_2.addWidget(self.comboBox_options_lamella_start_position, 7, 1, 1, 1)
        self.checkBox_take_final_high_quality_reference = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_take_final_high_quality_reference.setObjectName("checkBox_take_final_high_quality_reference")
        self.gridLayout_2.addWidget(self.checkBox_take_final_high_quality_reference, 4, 1, 1, 1)
        self.checkBox_align_at_milling_current = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_align_at_milling_current.setObjectName("checkBox_align_at_milling_current")
        self.gridLayout_2.addWidget(self.checkBox_align_at_milling_current, 14, 1, 1, 1)
        self.label_ml_checkpoint = QtWidgets.QLabel(self.tab_2)
        self.label_ml_checkpoint.setObjectName("label_ml_checkpoint")
        self.gridLayout_2.addWidget(self.label_ml_checkpoint, 17, 0, 1, 1)
        self.label_lamella_tilt_angle = QtWidgets.QLabel(self.tab_2)
        self.label_lamella_tilt_angle.setObjectName("label_lamella_tilt_angle")
        self.gridLayout_2.addWidget(self.label_lamella_tilt_angle, 12, 0, 1, 1)
        self.label_protocol_method = QtWidgets.QLabel(self.tab_2)
        self.label_protocol_method.setObjectName("label_protocol_method")
        self.gridLayout_2.addWidget(self.label_protocol_method, 1, 0, 1, 1)
        self.label_alignment_header = QtWidgets.QLabel(self.tab_2)
        font = QtGui.QFont()
        font.setBold(True)
        font.setUnderline(False)
        font.setWeight(75)
        self.label_alignment_header.setFont(font)
        self.label_alignment_header.setObjectName("label_alignment_header")
        self.gridLayout_2.addWidget(self.label_alignment_header, 13, 0, 1, 2)
        self.comboBox_ml_checkpoint = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_ml_checkpoint.setObjectName("comboBox_ml_checkpoint")
        self.gridLayout_2.addWidget(self.comboBox_ml_checkpoint, 17, 1, 1, 1)
        self.comboBox_options_liftout_joining_method = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_options_liftout_joining_method.setObjectName("comboBox_options_liftout_joining_method")
        self.gridLayout_2.addWidget(self.comboBox_options_liftout_joining_method, 8, 1, 1, 1)
        self.label_options_header = QtWidgets.QLabel(self.tab_2)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_options_header.setFont(font)
        self.label_options_header.setObjectName("label_options_header")
        self.gridLayout_2.addWidget(self.label_options_header, 2, 0, 1, 1)
        self.comboBox_method = QtWidgets.QComboBox(self.tab_2)
        self.comboBox_method.setObjectName("comboBox_method")
        self.gridLayout_2.addWidget(self.comboBox_method, 1, 1, 1, 1)
        self.checkBox_options_confirm_next_stage = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_options_confirm_next_stage.setObjectName("checkBox_options_confirm_next_stage")
        self.gridLayout_2.addWidget(self.checkBox_options_confirm_next_stage, 3, 0, 1, 1)
        self.checkBox_supervise_landing = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_supervise_landing.setEnabled(True)
        self.checkBox_supervise_landing.setObjectName("checkBox_supervise_landing")
        self.gridLayout_2.addWidget(self.checkBox_supervise_landing, 22, 0, 1, 1)
        self.checkBox_use_microexpansion = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_use_microexpansion.setObjectName("checkBox_use_microexpansion")
        self.gridLayout_2.addWidget(self.checkBox_use_microexpansion, 11, 0, 1, 1)
        self.checkBox_use_notch = QtWidgets.QCheckBox(self.tab_2)
        self.checkBox_use_notch.setObjectName("checkBox_use_notch")
        self.gridLayout_2.addWidget(self.checkBox_use_notch, 11, 1, 1, 1)
        self.tabWidget.addTab(self.tab_2, "")
        self.gridLayout.addWidget(self.tabWidget, 1, 0, 1, 2)
        self.pushButton_yes = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_yes.setObjectName("pushButton_yes")
        self.gridLayout.addWidget(self.pushButton_yes, 4, 0, 1, 1)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem2, 2, 0, 1, 2)
        self.label_title = QtWidgets.QLabel(self.centralwidget)
        font = QtGui.QFont()
        font.setPointSize(16)
        font.setBold(True)
        font.setWeight(75)
        self.label_title.setFont(font)
        self.label_title.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.label_title.setObjectName("label_title")
        self.gridLayout.addWidget(self.label_title, 0, 0, 1, 2)
        self.pushButton_no = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_no.setObjectName("pushButton_no")
        self.gridLayout.addWidget(self.pushButton_no, 4, 1, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 563, 22))
        self.menubar.setObjectName("menubar")
        self.menuAutoLamella = QtWidgets.QMenu(self.menubar)
        self.menuAutoLamella.setObjectName("menuAutoLamella")
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menuTools.setObjectName("menuTools")
        self.menuWorkflow = QtWidgets.QMenu(self.menubar)
        self.menuWorkflow.setObjectName("menuWorkflow")
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
        self.menuAutoLamella.addAction(self.actionNew_Experiment)
        self.menuAutoLamella.addAction(self.actionLoad_Experiment)
        self.menuAutoLamella.addSeparator()
        self.menuAutoLamella.addAction(self.actionLoad_Protocol)
        self.menuAutoLamella.addAction(self.actionSave_Protocol)
        self.menuTools.addAction(self.actionCryo_Deposition)
        self.menuTools.addSeparator()
        self.menuTools.addAction(self.actionLoad_Positions)
        self.menuTools.addAction(self.actionOpen_Minimap)
        self.menuTools.addAction(self.actionLoad_Minimap_Image)
        self.menuWorkflow.addAction(self.actionStop_Workflow)
        self.menubar.addAction(self.menuAutoLamella.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menuWorkflow.menuAction())

        self.retranslateUi(MainWindow)
        self.tabWidget.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.label_instructions.setText(_translate("MainWindow", "Instructions"))
        self.pushButton_revert_stage.setText(_translate("MainWindow", "Time Travel To"))
        self.pushButton_save_position.setText(_translate("MainWindow", "Save Position"))
        self.label_current_lamella_header.setText(_translate("MainWindow", "Current Lamella"))
        self.pushButton_add_lamella.setText(_translate("MainWindow", "Add Lamella"))
        self.pushButton_go_to_lamella.setText(_translate("MainWindow", "Go to position"))
        self.pushButton_run_setup_autolamella.setText(_translate("MainWindow", "Run Setup AutoLamella"))
        self.label_setup_header.setText(_translate("MainWindow", "Setup"))
        self.pushButton_run_autolamella.setText(_translate("MainWindow", "Run AutoLamella"))
        self.pushButton_fail_lamella.setText(_translate("MainWindow", "Mark Lamella As Failed"))
        self.label_experiment_name.setText(_translate("MainWindow", "Experiment:"))
        self.pushButton_run_waffle_undercut.setText(_translate("MainWindow", "Run Waffle Undercut Milling"))
        self.pushButton_remove_lamella.setText(_translate("MainWindow", "Remove Lamella"))
        self.label_info.setText(_translate("MainWindow", "No Lamella Selected"))
        self.label_protocol_name.setText(_translate("MainWindow", "Protocol:"))
        self.pushButton_run_waffle_trench.setText(_translate("MainWindow", "Run Waffle Trench Milling"))
        self.checkBox_show_lamella_in_view.setText(_translate("MainWindow", "Show Lamellas In View"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("MainWindow", "Experiment"))
        self.label_options_lamella_start_position.setText(_translate("MainWindow", "Lamella Start Position"))
        self.checkBox_supervise_liftout.setText(_translate("MainWindow", "Liftout Lamella"))
        self.checkBox_take_final_reference_images.setText(_translate("MainWindow", "Take Final Reference Images"))
        self.label_options_landing_joining_method.setText(_translate("MainWindow", "Landing Joining Method"))
        self.checkBox_trench.setText(_translate("MainWindow", "Trench Stage"))
        self.label_options_liftout_joining_method.setText(_translate("MainWindow", "Liftout Joining Method"))
        self.label_protocol_undercut_tilt_angle.setText(_translate("MainWindow", "Undercut Tilt Angle"))
        self.checkBox_supervise_mill_polishing.setText(_translate("MainWindow", "Mill Polishing Stage"))
        self.label_protocol_undercut_tilt_step.setText(_translate("MainWindow", "Undercut Tilt Steps"))
        self.beamShiftAttemptsLabel.setText(_translate("MainWindow", "Alignment Attempts"))
        self.label_options_landing_start_position.setText(_translate("MainWindow", "Landing Start Position"))
        self.checkBox_undercut.setText(_translate("MainWindow", "Undercut Stage"))
        self.pushButton_update_protocol.setText(_translate("MainWindow", "Update Protocol"))
        self.checkBox_setup.setText(_translate("MainWindow", "Setup Stage"))
        self.label_ml_header.setText(_translate("MainWindow", "Machine Learning"))
        self.checkBox_supervise_mill_rough.setText(_translate("MainWindow", "Mill Rough Stage"))
        self.label_supervise_header.setText(_translate("MainWindow", "Supervision"))
        self.label_protocol_name_2.setText(_translate("MainWindow", "Name"))
        self.checkBox_take_final_high_quality_reference.setText(_translate("MainWindow", "Take Final High Quality Reference Image"))
        self.checkBox_align_at_milling_current.setText(_translate("MainWindow", "Align at Milling Current"))
        self.label_ml_checkpoint.setText(_translate("MainWindow", "Checkpoint"))
        self.label_lamella_tilt_angle.setText(_translate("MainWindow", "Lamella Tilt Angle (deg)"))
        self.label_protocol_method.setText(_translate("MainWindow", "Method"))
        self.label_alignment_header.setText(_translate("MainWindow", "Alignment"))
        self.label_options_header.setText(_translate("MainWindow", "Options"))
        self.checkBox_options_confirm_next_stage.setText(_translate("MainWindow", "Confirm Next Stage"))
        self.checkBox_supervise_landing.setText(_translate("MainWindow", "Land Lamella"))
        self.checkBox_use_microexpansion.setText(_translate("MainWindow", "Use Microexpansion"))
        self.checkBox_use_notch.setText(_translate("MainWindow", "Use Notch"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_2), _translate("MainWindow", "Protocol"))
        self.pushButton_yes.setText(_translate("MainWindow", "Yes"))
        self.label_title.setText(_translate("MainWindow", "AutoLamella"))
        self.pushButton_no.setText(_translate("MainWindow", "No"))
        self.menuAutoLamella.setTitle(_translate("MainWindow", "File"))
        self.menuTools.setTitle(_translate("MainWindow", "Tools"))
        self.menuWorkflow.setTitle(_translate("MainWindow", "Workflow"))
        self.actionNew_Experiment.setText(_translate("MainWindow", "Create Experiment"))
        self.actionLoad_Experiment.setText(_translate("MainWindow", "Load Experiment"))
        self.actionCryo_Deposition.setText(_translate("MainWindow", "Cryo Deposition"))
        self.actionLoad_Protocol.setText(_translate("MainWindow", "Load Protocol"))
        self.actionLoad_Positions.setText(_translate("MainWindow", "Load Positions"))
        self.actionOpen_Minimap.setText(_translate("MainWindow", "Open Minimap Tool"))
        self.actionSave_Protocol.setText(_translate("MainWindow", "Save Protocol"))
        self.actionLoad_Minimap_Image.setText(_translate("MainWindow", "Load Minimap Image"))
        self.actionStop_Workflow.setText(_translate("MainWindow", "Stop Workflow"))
