#!/usr/bin/env python
# coding: utf-8
#
# PyRMD Studio: A Unified Suite for Next-Generation, AI-Powered Virtual Screening
# Copyright (C) 2021-2026 Benito Natale, Muhammad Waqas, Michele Roggia, Salvatore Di Maro, Sandro Cosconati
# PyRMD Authors: Dr. Giorgio Amendola, Prof. Sandro Cosconati
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# If you use PyRMD Studio in your work, please cite the following articles:
# PyRMD Studio:
# <XXXX>
#
# PyRMD:
# <https://pubs.acs.org/doi/full/10.1021/acs.jcim.1c00653>
#
# PyRMD2Dock:
# <https://pubs.acs.org/doi/10.1021/acs.jcim.3c00647>
#
# Please check our GitHub page for more information:
# <https://github.com/cosconatilab/PyRMD_Studio>
#------------------------------------------------------------------------------
"""
Unified GUI Application - EXACT Integration of Screening.py and rmd_analysis.py
This application combines both GUIs into a single tab-based interface WITHOUT modifying the original classes.

IMPORTANT: All original GUI layouts and functionalities are preserved exactly as they were.
Only a minimal tab-based wrapper has been added.
"""

# ============================================================================
# COMPLETE ORIGINAL SCREENING.PY CODE (UNMODIFIED)
# ============================================================================

# -*- coding: utf-8 -*-

import subprocess
import multiprocessing
import json
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QCheckBox, QButtonGroup, QRadioButton, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QLineEdit, QWidget, QComboBox, QSpinBox
import configparser
import os
import time

class CPUCoreSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CPU Core Selection")
        self.resize(400, 200)
        
        self.layout = QVBoxLayout(self)
        
        # Get total CPU cores
        self.total_cores = multiprocessing.cpu_count()
        
        # Display total cores
        self.label_total = QLabel(f"Total CPU cores available: {self.total_cores}")
        self.layout.addWidget(self.label_total)
        
        # Option selection
        self.radio_all_cores = QRadioButton("Use all cores")
        self.radio_all_cores.setChecked(True)
        self.layout.addWidget(self.radio_all_cores)
        
        self.radio_specify_cores = QRadioButton("Specify number of cores:")
        self.layout.addWidget(self.radio_specify_cores)
        
        # Core count spinner
        core_layout = QHBoxLayout()
        self.spinBox_cores = QSpinBox()
        self.spinBox_cores.setMinimum(1)
        self.spinBox_cores.setMaximum(self.total_cores)
        self.spinBox_cores.setValue(self.total_cores)
        self.spinBox_cores.setEnabled(False)
        core_layout.addWidget(QLabel("Number of cores:"))
        core_layout.addWidget(self.spinBox_cores)
        core_layout.addStretch()
        
        core_widget = QWidget()
        core_widget.setLayout(core_layout)
        self.layout.addWidget(core_widget)
        
        # Connect radio buttons
        self.radio_all_cores.toggled.connect(self._toggle_core_selection)
        self.radio_specify_cores.toggled.connect(self._toggle_core_selection)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.pushButton_run = QPushButton("Run Now")
        self.pushButton_run.clicked.connect(self.accept)
        self.pushButton_cancel = QPushButton("Cancel")
        self.pushButton_cancel.clicked.connect(self.reject)
        
        button_layout.addWidget(self.pushButton_run)
        button_layout.addWidget(self.pushButton_cancel)
        
        button_widget = QWidget()
        button_widget.setLayout(button_layout)
        self.layout.addWidget(button_widget)
    
    def _toggle_core_selection(self):
        """Toggle core count spinner based on radio button selection"""
        self.spinBox_cores.setEnabled(self.radio_specify_cores.isChecked())
    
    def get_core_count(self):
        """Get the selected number of cores"""
        if self.radio_all_cores.isChecked():
            return self.total_cores
        else:
            return self.spinBox_cores.value()

class EpsilonSelectionDialog(QDialog):
    def __init__(self, parent=None, title="Epsilon Values", values=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(400, 300)
        
        self.layout = QVBoxLayout(self)
        
        # Display the selected values
        self.label = QLabel("Selected epsilon values:")
        self.layout.addWidget(self.label)
        
        # Text area to show and edit values
        self.valuesEdit = QtWidgets.QTextEdit()
        if values:
            self.valuesEdit.setText(", ".join(map(str, values)))
        self.layout.addWidget(self.valuesEdit)
        
        # Buttons
        self.buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)
    
    def get_values(self):
        text = self.valuesEdit.toPlainText()
        return [float(x.strip()) for x in text.split(",") if x.strip()]

class Ui_Screening(object):
    def setupUi(self, Screening, selected_module="PyRMD"):
        Screening.setObjectName("Screening")
        self.selected_module = selected_module
        Screening.setWindowTitle(f"Screening - {self.selected_module}")
        
        # ...inside Ui_Screening.setupUi...
        self.default_values = {
            'butina_cutoff': '0.7'
        }
        
        # Initialize file paths and epsilon values
        self.browse_smi_file_screen = ""
        self.file_path_chembl = ""
        self.actives_file_path = ""
        self.inactives_file_path = ""
        self.decoys_file_path = ""
        self.screening_output_directory = ""
        self.active_epsilon_values = []
        self.inactive_epsilon_values = []
        # Initialize filter settings
        self.use_filter = False
        self.filter_defaults = {
            "Molecular Weight Min:": "200",
            "Molecular Weight Max:": "600",
            "LogP Min:": "-5",
            "LogP Max:": "5",
            "H-Bond Donors Min:": "0",
            "H-Bond Donors Max:": "6",
            "H-Bond Acceptors Min:": "0",
            "H-Bond Acceptors Max:": "11",
            "Rotatable Bonds Min:": "0",
            "Rotatable Bonds Max:": "9",
            "Heavy Atoms Min:": "15",
            "Heavy Atoms Max:": "51",
        }
        Screening.resize(800, 1000)
        
        # Set up central widget
        self.centralwidget = QtWidgets.QWidget(Screening)
        self.centralwidget.setObjectName("centralwidget")
        Screening.setCentralWidget(self.centralwidget)
        
        # Main layout
        self.mainLayout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.mainLayout.setContentsMargins(20, 20, 20, 20)
        self.mainLayout.setSpacing(15)
        
        # Expert Mode Checkbox
        self.expertModeCheckbox = QCheckBox("Expert Mode")
        self.expertModeCheckbox.setChecked(False)
        self.expertModeCheckbox.setToolTip("Go for expert mode to see advanced parameters.")
        self.expertModeCheckbox.stateChanged.connect(self._update_parameter_visibility)
        self.mainLayout.addWidget(self.expertModeCheckbox)
        
        # Scroll Area
        self.scrollArea = QtWidgets.QScrollArea(self.centralwidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.formLayout = QtWidgets.QFormLayout(self.scrollAreaWidgetContents)
        self.formLayout.setSpacing(10)
        
        self.all_parameter_widgets = []  # Store (widget, visibility_mode)
        
        current_row = 0
        
        # MODE Section
        self.label_mode_header = QtWidgets.QLabel("MODE")
        self.label_mode_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_mode_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_mode_header, "always"))
        
        self.label_program_mode = QtWidgets.QLabel("Program Mode:")
        self.lineEdit_program_mode = QLineEdit()
        self.lineEdit_program_mode.setText("Ligand-Based Virtual Screening (LBVS), Screening")
        self.lineEdit_program_mode.setReadOnly(True)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_program_mode)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_program_mode)
        current_row += 1
        self.all_parameter_widgets.append((self.label_program_mode, "always"))
        self.all_parameter_widgets.append((self.lineEdit_program_mode, "always"))
        
        # Database to Screen
        self.label_db_to_screen = QtWidgets.QLabel("Database to Screen:")
        self.label_db_to_screen.setToolTip("Select the database file to screen.")
        db_layout = QHBoxLayout()
        self.lineEdit_db_to_screen = QLineEdit()
        self.pushButton_db_to_screen = QPushButton("Browse")
        self.pushButton_db_to_screen.clicked.connect(lambda: self.browse_file("browse_smi_file_screen", self.lineEdit_db_to_screen, "Select Database File"))
        db_layout.addWidget(self.lineEdit_db_to_screen)
        db_layout.addWidget(self.pushButton_db_to_screen)
        db_container = QWidget()
        db_container.setLayout(db_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_db_to_screen)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, db_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_db_to_screen, "beginner"))
        self.all_parameter_widgets.append((db_container, "beginner"))
        
        # Output Directory
        self.label_output_dir = QtWidgets.QLabel("Output Directory:")
        output_dir_layout = QHBoxLayout()
        self.lineEdit_output_dir = QLineEdit()
        self.pushButton_output_dir = QPushButton("Browse")
        self.pushButton_output_dir.clicked.connect(self.browse_output_directory)
        output_dir_layout.addWidget(self.lineEdit_output_dir)
        output_dir_layout.addWidget(self.pushButton_output_dir)
        output_dir_container = QWidget()
        output_dir_container.setLayout(output_dir_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_output_dir)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, output_dir_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_output_dir, "beginner"))
        self.all_parameter_widgets.append((output_dir_container, "beginner"))
        
        # Output File Name (Beginner Mode)
        self.label_output_file = QtWidgets.QLabel("Output File Name:")
        self.lineEdit_output_file = QLineEdit()
        self.lineEdit_output_file.setText("PyRMD_database_predictions.csv")
        self.lineEdit_output_file.setToolTip("Enter the name of the output file where results will be saved.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_output_file)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_output_file)
        current_row += 1
        self.all_parameter_widgets.append((self.label_output_file, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_output_file, "beginner"))
        
        # SDF Results (Expert Mode)
        self.label_sdf_results = QtWidgets.QLabel("Save SDF Results:")
        self.checkBox_sdf_results = QCheckBox("Save SDF Results")
        self.checkBox_sdf_results.setToolTip("Check this box to save the results in SDF format.")
        self.checkBox_sdf_results.setChecked(False)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_sdf_results)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.checkBox_sdf_results)
        current_row += 1
        self.all_parameter_widgets.append((self.label_sdf_results, "expert"))
        self.all_parameter_widgets.append((self.checkBox_sdf_results, "expert"))
        
        # TRAINING DATASETS Section
        self.label_training_header = QtWidgets.QLabel("TRAINING DATASETS")
        self.label_training_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_training_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_training_header, "always"))
        
        self.checkBox_use_chembl = QCheckBox("Use ChEMBL Dataset")
        self.checkBox_use_chembl.setChecked(True)
        self.checkBox_use_chembl.stateChanged.connect(self._toggle_training_uploads)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_use_chembl)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_use_chembl, "beginner"))
        
        # ChEMBL File
        self.label_chembl_file = QtWidgets.QLabel("ChEMBL File:")
        chembl_layout = QHBoxLayout()
        self.lineEdit_chembl_file = QLineEdit()
        self.pushButton_chembl_file = QPushButton("Browse")
        self.pushButton_chembl_file.clicked.connect(lambda: self.browse_file("file_path_chembl", self.lineEdit_chembl_file, "Select ChEMBL File"))
        chembl_layout.addWidget(self.lineEdit_chembl_file)
        chembl_layout.addWidget(self.pushButton_chembl_file)
        chembl_container = QWidget()
        chembl_container.setLayout(chembl_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_chembl_file)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, chembl_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_chembl_file, "beginner"))
        self.all_parameter_widgets.append((chembl_container, "beginner"))
        
        # Actives File
        self.label_actives_file = QtWidgets.QLabel("Active Compounds File:")
        actives_layout = QHBoxLayout()
        self.lineEdit_actives_file = QLineEdit()
        self.pushButton_actives_file = QPushButton("Browse")
        self.pushButton_actives_file.clicked.connect(lambda: self.browse_file("actives_file_path", self.lineEdit_actives_file, "Select Active Compounds File"))
        actives_layout.addWidget(self.lineEdit_actives_file)
        actives_layout.addWidget(self.pushButton_actives_file)
        actives_container = QWidget()
        actives_container.setLayout(actives_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_actives_file)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, actives_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_actives_file, "beginner"))
        self.all_parameter_widgets.append((actives_container, "beginner"))
        
        # Inactives File
        self.label_inactives_file = QtWidgets.QLabel("Inactive Compounds File:")
        inactives_layout = QHBoxLayout()
        self.lineEdit_inactives_file = QLineEdit()
        self.pushButton_inactives_file = QPushButton("Browse")
        self.pushButton_inactives_file.clicked.connect(lambda: self.browse_file("inactives_file_path", self.lineEdit_inactives_file, "Select Inactive Compounds File"))
        inactives_layout.addWidget(self.lineEdit_inactives_file)
        inactives_layout.addWidget(self.pushButton_inactives_file)
        inactives_container = QWidget()
        inactives_container.setLayout(inactives_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_inactives_file)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, inactives_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_inactives_file, "beginner"))
        self.all_parameter_widgets.append((inactives_container, "beginner"))
        
        # FINGERPRINTS Section
        self.label_fingerprints_header = QtWidgets.QLabel("FINGERPRINTS")
        self.label_fingerprints_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_fingerprints_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fingerprints_header, "always"))
        
        # Fingerprint Type Selection (Fast, Balanced, Accurate)
        self.label_fingerprint_type = QtWidgets.QLabel("Fingerprint Type:")
        fingerprint_layout = QHBoxLayout()
        
        self.radio_fp_fast = QRadioButton("Fast")
        self.radio_fp_fast.setToolTip("Select this for a quick fingerprint generation with lower accuracy (1024 bits).")
        self.radio_fp_balanced = QRadioButton("Balanced")
        self.radio_fp_balanced.setToolTip("Select this for a balanced approach with moderate accuracy (2048 bits).")
        self.radio_fp_accurate = QRadioButton("Accurate")
        self.radio_fp_accurate.setToolTip("Select this for the most accurate fingerprint generation (4096 bits).")
        self.radio_fp_accurate.setChecked(True)  # Default for screening
        
        self.fingerprint_group = QButtonGroup()
        self.fingerprint_group.addButton(self.radio_fp_fast, 0)
        self.fingerprint_group.addButton(self.radio_fp_balanced, 1)
        self.fingerprint_group.addButton(self.radio_fp_accurate, 2)
        
        fingerprint_layout.addWidget(self.radio_fp_fast)
        fingerprint_layout.addWidget(self.radio_fp_balanced)
        fingerprint_layout.addWidget(self.radio_fp_accurate)
        
        fingerprint_container = QWidget()
        fingerprint_container.setLayout(fingerprint_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_fingerprint_type)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, fingerprint_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fingerprint_type, "beginner"))
        self.all_parameter_widgets.append((fingerprint_container, "beginner"))
        
        # Expert fingerprint parameters
        self.label_fp_type = QtWidgets.QLabel("Fingerprint Algorithm:")
        self.comboBox_fp_type = QComboBox()
        self.comboBox_fp_type.addItems(["mhfp", "rdkit", "tt", "avalon", "ecfp"])
        self.comboBox_fp_type.setToolTip("Select the fingerprint algorithm to use.")
        self.comboBox_fp_type.setCurrentText("mhfp")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_fp_type)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.comboBox_fp_type)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fp_type, "expert"))
        self.all_parameter_widgets.append((self.comboBox_fp_type, "expert"))
        
        self.label_fp_size = QtWidgets.QLabel("Fingerprint Size:")
        self.lineEdit_fp_size = QLineEdit()
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_fp_size)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_fp_size)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fp_size, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_fp_size, "expert"))
        
        self.label_fp_radius = QtWidgets.QLabel("Fingerprint Radius/Iterations:")
        self.lineEdit_fp_radius = QLineEdit()
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_fp_radius)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_fp_radius)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fp_radius, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_fp_radius, "expert"))
        
        # Explicit Hydrogens (Expert)
        self.checkBox_explicit_H = QCheckBox("Explicit Hydrogens")
        self.checkBox_explicit_H.setChecked(True)  # Default: True
        self.checkBox_explicit_H.setToolTip("Include explicit hydrogens in the fingerprint.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_explicit_H)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_explicit_H, "expert"))

        # Chirality (Expert)
        self.checkBox_chirality = QCheckBox("Include Chirality")
        self.checkBox_chirality.setChecked(False) # Default: False
        self.checkBox_chirality.setToolTip("Include chirality in ECFP/MHFP fingerprints.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_chirality)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_chirality, "expert"))

        # Redundancy (Expert - ECFP specific)
        self.checkBox_redundancy = QCheckBox("Redundancy (ECFP)")
        self.checkBox_redundancy.setChecked(True) # Default: True
        self.checkBox_redundancy.setToolTip("Include redundancy for ECFP fingerprints.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_redundancy)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_redundancy, "expert"))

        # Features (Expert - ECFP specific)
        self.checkBox_features = QCheckBox("Features (ECFP)")
        self.checkBox_features.setChecked(False) # Default: False
        self.checkBox_features.setToolTip("Use features for ECFP fingerprints.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_features)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_features, "expert"))

        # ------------------------------------------------------------------
        # DECOYS Section (Expert Mode)
        self.label_decoys_header = QtWidgets.QLabel("DECOYS")
        self.label_decoys_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_decoys_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_decoys_header, "beginner"))
        
        self.label_decoys_file = QtWidgets.QLabel("Decoys File (optional):")
        decoys_layout = QHBoxLayout()
        self.lineEdit_decoys_file = QLineEdit()
        self.lineEdit_decoys_file.setToolTip("Select the decoys file to use in the screening.")
        self.pushButton_decoys_file = QPushButton("Browse")
        self.pushButton_decoys_file.setToolTip("Select the decoys file to use in the screening.")
        self.pushButton_decoys_file.clicked.connect(lambda: self.browse_file("decoys_file_path", self.lineEdit_decoys_file, "Select Decoys File"))
        decoys_layout.addWidget(self.lineEdit_decoys_file)
        decoys_layout.addWidget(self.pushButton_decoys_file)
        decoys_container = QWidget()
        decoys_container.setLayout(decoys_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_decoys_file)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, decoys_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_decoys_file, "beginner"))
        self.all_parameter_widgets.append((decoys_container, "beginner"))
        
        # EPSILON CUTOFF VALUES Section
        self.label_epsilon_header = QtWidgets.QLabel("EPSILON CUTOFF VALUES")
        self.label_epsilon_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_epsilon_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_epsilon_header, "always"))
        
        # Active Epsilon Cutoff
        self.label_active_epsilon = QtWidgets.QLabel("Active Epsilon Cutoff:")
        self.label_active_epsilon.setStyleSheet("font-weight: bold; color: #27ae60;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_active_epsilon)
        current_row += 1
        self.all_parameter_widgets.append((self.label_active_epsilon, "beginner"))
        
        # Active epsilon selection type
        active_epsilon_type_layout = QHBoxLayout()
        self.radio_active_single = QRadioButton("Single")
        self.radio_active_single.setToolTip("Enter a single epsilon value for active compounds.")
        self.radio_active_range = QRadioButton("Range")
        self.radio_active_range.setToolTip("Enter a range of epsilon values for active compounds (Min, Max, Step).")
        self.radio_active_manual = QRadioButton("Manual")
        self.radio_active_manual.setToolTip("Enter manual epsilon values for active compounds (e.g., 0.1,0.5,0.8 or 0.1-0.5).")
        self.radio_active_single.setChecked(True)
        
        self.active_epsilon_group = QButtonGroup()
        self.active_epsilon_group.addButton(self.radio_active_single, 0)
        self.active_epsilon_group.addButton(self.radio_active_range, 1)
        self.active_epsilon_group.addButton(self.radio_active_manual, 2)
        
        active_epsilon_type_layout.addWidget(self.radio_active_single)
        active_epsilon_type_layout.addWidget(self.radio_active_range)
        active_epsilon_type_layout.addWidget(self.radio_active_manual)
        
        active_epsilon_type_container = QWidget()
        active_epsilon_type_container.setLayout(active_epsilon_type_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, active_epsilon_type_container)
        current_row += 1
        self.all_parameter_widgets.append((active_epsilon_type_container, "beginner"))
        
        # Active epsilon single value
        self.label_active_single = QtWidgets.QLabel("Single Value:")
        self.lineEdit_active_single = QLineEdit()
        self.lineEdit_active_single.setText("0.95")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_active_single)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_active_single)
        current_row += 1
        self.all_parameter_widgets.append((self.label_active_single, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_active_single, "beginner"))
        
        # Active epsilon range
        self.label_active_range = QtWidgets.QLabel("Range (Min, Max, Step):")
        active_range_layout = QHBoxLayout()
        self.lineEdit_active_min = QLineEdit()
        self.lineEdit_active_min.setPlaceholderText("Min")
        self.lineEdit_active_max = QLineEdit()
        self.lineEdit_active_max.setPlaceholderText("Max")
        self.lineEdit_active_step = QLineEdit()
        self.lineEdit_active_step.setPlaceholderText("Step")
        active_range_layout.addWidget(self.lineEdit_active_min)
        active_range_layout.addWidget(self.lineEdit_active_max)
        active_range_layout.addWidget(self.lineEdit_active_step)
        active_range_container = QWidget()
        active_range_container.setLayout(active_range_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_active_range)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, active_range_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_active_range, "beginner"))
        self.all_parameter_widgets.append((active_range_container, "beginner"))
        
        # Active epsilon manual
        self.label_active_manual = QtWidgets.QLabel("Manual Values:")
        self.lineEdit_active_manual = QLineEdit()
        self.lineEdit_active_manual.setPlaceholderText("e.g., 0.1,0.5,0.8 or 0.1-0.5")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_active_manual)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_active_manual)
        current_row += 1
        self.all_parameter_widgets.append((self.label_active_manual, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_active_manual, "beginner"))
        
        # Preview Active Epsilon button
        self.pushButton_preview_active = QPushButton("Preview Active Epsilon Values")
        self.pushButton_preview_active.clicked.connect(self._preview_active_epsilon_values)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.pushButton_preview_active)
        current_row += 1
        self.all_parameter_widgets.append((self.pushButton_preview_active, "beginner"))
        
        # Inactive Epsilon Cutoff
        self.label_inactive_epsilon = QtWidgets.QLabel("Inactive Epsilon Cutoff:")
        self.label_inactive_epsilon.setStyleSheet("font-weight: bold; color: #e74c3c;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_inactive_epsilon)
        current_row += 1
        self.all_parameter_widgets.append((self.label_inactive_epsilon, "beginner"))
        
        # Inactive epsilon selection type
        inactive_epsilon_type_layout = QHBoxLayout()
        self.radio_inactive_single = QRadioButton("Single")
        self.radio_inactive_single.setToolTip("Enter a single epsilon value for inactive compounds.")
        self.radio_inactive_range = QRadioButton("Range")
        self.radio_inactive_range.setToolTip("Enter a range of epsilon values for inactive compounds (Min, Max, Step).")
        self.radio_inactive_manual = QRadioButton("Manual")
        self.radio_inactive_manual.setToolTip("Enter manual epsilon values for inactive compounds (e.g., 0.1,0.5,0.8 or 0.1-0.5).")
        self.radio_inactive_single.setChecked(True)
        
        self.inactive_epsilon_group = QButtonGroup()
        self.inactive_epsilon_group.addButton(self.radio_inactive_single, 0)
        self.inactive_epsilon_group.addButton(self.radio_inactive_range, 1)
        self.inactive_epsilon_group.addButton(self.radio_inactive_manual, 2)
        
        inactive_epsilon_type_layout.addWidget(self.radio_inactive_single)
        inactive_epsilon_type_layout.addWidget(self.radio_inactive_range)
        inactive_epsilon_type_layout.addWidget(self.radio_inactive_manual)
        
        inactive_epsilon_type_container = QWidget()
        inactive_epsilon_type_container.setLayout(inactive_epsilon_type_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, inactive_epsilon_type_container)
        current_row += 1
        self.all_parameter_widgets.append((inactive_epsilon_type_container, "beginner"))
        
        # Inactive epsilon single value
        self.label_inactive_single = QtWidgets.QLabel("Single Value:")
        self.lineEdit_inactive_single = QLineEdit()
        self.lineEdit_inactive_single.setText("0.95")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_inactive_single)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_inactive_single)
        current_row += 1
        self.all_parameter_widgets.append((self.label_inactive_single, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_inactive_single, "beginner"))
        
        # Inactive epsilon range
        self.label_inactive_range = QtWidgets.QLabel("Range (Min, Max, Step):")
        inactive_range_layout = QHBoxLayout()
        self.lineEdit_inactive_min = QLineEdit()
        self.lineEdit_inactive_min.setPlaceholderText("Min")
        self.lineEdit_inactive_max = QLineEdit()
        self.lineEdit_inactive_max.setPlaceholderText("Max")
        self.lineEdit_inactive_step = QLineEdit()
        self.lineEdit_inactive_step.setPlaceholderText("Step")
        inactive_range_layout.addWidget(self.lineEdit_inactive_min)
        inactive_range_layout.addWidget(self.lineEdit_inactive_max)
        inactive_range_layout.addWidget(self.lineEdit_inactive_step)
        inactive_range_container = QWidget()
        inactive_range_container.setLayout(inactive_range_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_inactive_range)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, inactive_range_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_inactive_range, "beginner"))
        self.all_parameter_widgets.append((inactive_range_container, "beginner"))
        
        # Inactive epsilon manual
        self.label_inactive_manual = QtWidgets.QLabel("Manual Values:")
        self.lineEdit_inactive_manual = QLineEdit()
        self.lineEdit_inactive_manual.setPlaceholderText("e.g., 0.1,0.5,0.8 or 0.1-0.5")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_inactive_manual)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_inactive_manual)
        current_row += 1
        self.all_parameter_widgets.append((self.label_inactive_manual, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_inactive_manual, "beginner"))
        
        # Preview Inactive Epsilon button
        self.pushButton_preview_inactive = QPushButton("Preview Inactive Epsilon Values")
        self.pushButton_preview_inactive.clicked.connect(self._preview_inactive_epsilon_values)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.pushButton_preview_inactive)
        current_row += 1
        self.all_parameter_widgets.append((self.pushButton_preview_inactive, "beginner"))
        
        # Butina Clustering Section (Expert Mode)
        self.label_butina_header = QtWidgets.QLabel("BUTINA CLUSTERING THRESHOLD")
        self.label_butina_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_butina_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_butina_header, "expert"))
        
        self.label_bu = QtWidgets.QLabel("Threshold (Similarity):")
        self.lineEdit_bu = QLineEdit()
        self.lineEdit_bu.setText(self.default_values['butina_cutoff'])
        self.lineEdit_bu.setToolTip("Enter the clustering threshold for Butina algorithm.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_bu)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_bu)
        current_row += 1
        self.all_parameter_widgets.append((self.label_bu, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_bu, "expert"))
        
        # STAT PARAMETERS Section (Expert Mode)
        self.label_stat_header = QtWidgets.QLabel("STAT PARAMETERS")
        self.label_stat_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_stat_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_stat_header, "expert"))
        
        self.label_beta = QtWidgets.QLabel("Beta:")
        self.lineEdit_beta = QLineEdit()
        self.lineEdit_beta.setText("1")
        self.lineEdit_beta.setToolTip("Enter the beta value for statistical calculations.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_beta)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_beta)
        current_row += 1
        self.all_parameter_widgets.append((self.label_beta, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_beta, "expert"))
        
        self.label_alpha = QtWidgets.QLabel("Alpha:")
        self.lineEdit_alpha = QLineEdit()
        self.lineEdit_alpha.setText("20")
        self.lineEdit_alpha.setToolTip("Enter the alpha value for statistical calculations.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_alpha)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_alpha)
        current_row += 1
        self.all_parameter_widgets.append((self.label_alpha, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_alpha, "expert"))
        
        # KFOLD PARAMETERS Section (Expert Mode)
        self.label_kfold_header = QtWidgets.QLabel("KFOLD PARAMETERS")
        self.label_kfold_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_kfold_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_kfold_header, "expert"))
        
        self.label_n_splits = QtWidgets.QLabel("N Splits:")
        self.lineEdit_n_splits = QLineEdit()
        self.lineEdit_n_splits.setText("5")
        self.lineEdit_n_splits.setToolTip("Enter the number of splits for K-Fold cross-validation.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_n_splits)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_n_splits)
        current_row += 1
        self.all_parameter_widgets.append((self.label_n_splits, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_n_splits, "expert"))
        
        self.label_n_repeats = QtWidgets.QLabel("N Repeats:")
        self.lineEdit_n_repeats = QLineEdit()
        self.lineEdit_n_repeats.setText("3")
        self.lineEdit_n_repeats.setToolTip("Enter the number of repeats for K-Fold cross-validation.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_n_repeats)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_n_repeats)
        current_row += 1
        self.all_parameter_widgets.append((self.label_n_repeats, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_n_repeats, "expert"))
        
        # CHEMBL THRESHOLDS Section (Expert Mode)
        self.label_chembl_thresholds_header = QtWidgets.QLabel("CHEMBL THRESHOLDS")
        self.label_chembl_thresholds_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_chembl_thresholds_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_chembl_thresholds_header, "beginner"))
        
        self.label_activity_threshold = QtWidgets.QLabel("Activity Threshold (nM):")
        self.lineEdit_activity_threshold = QLineEdit()
        self.lineEdit_activity_threshold.setText("1001")
        self.lineEdit_activity_threshold.setToolTip("Enter the activity threshold for ChEMBL screening.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_activity_threshold)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_activity_threshold)
        current_row += 1
        self.all_parameter_widgets.append((self.label_activity_threshold, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_activity_threshold, "beginner"))
        # # After self.lineEdit_activity_threshold
        # self.label_actives_count = QLabel("Actives below threshold: 0")
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_actives_count)
        # current_row += 1
        
        self.label_inactivity_threshold = QtWidgets.QLabel("Inactivity Threshold (nM):")
        self.lineEdit_inactivity_threshold = QLineEdit()
        self.lineEdit_inactivity_threshold.setText("39999")
        self.lineEdit_inactivity_threshold.setToolTip("Enter the inactivity threshold for ChEMBL screening.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_inactivity_threshold)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_inactivity_threshold)
        current_row += 1
        self.all_parameter_widgets.append((self.label_inactivity_threshold, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_inactivity_threshold, "beginner"))
        # # After self.lineEdit_inactivity_threshold
        # self.label_inactives_count = QLabel("Inactives above threshold: 0")
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_inactives_count)
        # current_row += 1
        
        
        # self.lineEdit_chembl_file.textChanged.connect(self._update_actives_inactives_count)
        # self.lineEdit_activity_threshold.textChanged.connect(self._update_actives_inactives_count)
        # self.lineEdit_inactivity_threshold.textChanged.connect(self._update_actives_inactives_count)
        
        # Inhibition Thresholds Section
        self.label_inhibition_header = QtWidgets.QLabel("INHIBITION THRESHOLDS")
        self.label_inhibition_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_inhibition_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_inhibition_header, "always"))

        self.checkBox_use_inhibition = QCheckBox("Use Inhibition Thresholds")
        self.checkBox_use_inhibition.setChecked(False)
        self.checkBox_use_inhibition.stateChanged.connect(self._toggle_inhibition_thresholds)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_use_inhibition)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_use_inhibition, "always"))

        # --- MODIFIED LAYOUT STARTS HERE ---
        inhibition_layout = QHBoxLayout()
        self.lineEdit_inhibition_inactive = QLineEdit()
        self.lineEdit_inhibition_inactive.setText("11")
        self.lineEdit_inhibition_inactive.setToolTip("Inactive if inhibition < this value (%)")
        
        # Removed the active lineEdit and labels
        
        inhibition_layout.addWidget(QLabel("Inactive <"))
        inhibition_layout.addWidget(self.lineEdit_inhibition_inactive)
        inhibition_layout.addWidget(QLabel("%"))
        inhibition_layout.addStretch() # Adds space to the right
        # --- MODIFIED LAYOUT ENDS HERE ---

        inhibition_container = QWidget()
        inhibition_container.setLayout(inhibition_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, inhibition_container)
        current_row += 1

        self.all_parameter_widgets.append((inhibition_container, "inhibition"))
                
        # FILTER Section
        self.label_filter_header = QtWidgets.QLabel("FILTER PROPERTIES")
        self.label_filter_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_filter_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_filter_header, "always"))

        self.checkBox_use_filter = QCheckBox("Enable Filtering")
        self.checkBox_use_filter.setChecked(False)  # default unchecked
        self.checkBox_use_filter.stateChanged.connect(self._toggle_filter_properties)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_use_filter)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_use_filter, "always"))

        # Create filter fields dictionary for easy access
        self.filter_fields = {}

        # Example filter properties
        filter_props = [
            ("Molecular Weight Min:", "200"),
            ("Molecular Weight Max:", "600"),
            ("LogP Min:", "-5"),
            ("LogP Max:", "5"),
            ("H-Bond Donors Min:", "0"),
            ("H-Bond Donors Max:", "6"),
            ("H-Bond Acceptors Min:", "0"),
            ("H-Bond Acceptors Max:", "11"),
            ("Rotatable Bonds Min:", "0"),
            ("Rotatable Bonds Max:", "9"),
            ("Heavy Atoms Min:", "15"),
            ("Heavy Atoms Max:", "51"),
        ]

        for label_text, default_val in filter_props:
            label = QtWidgets.QLabel(label_text)
            lineEdit = QtWidgets.QLineEdit()
            lineEdit.setText(default_val)
            self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, label)
            self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, lineEdit)
            current_row += 1

            self.all_parameter_widgets.append((label, "filter"))
            self.all_parameter_widgets.append((lineEdit, "filter"))
            self.filter_fields[label_text] = lineEdit

        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        self.pushButton_update_config = QPushButton("Update Configuration")
        self.pushButton_update_config.setToolTip("Update the configuration file with the current settings.")
        self.pushButton_update_config.clicked.connect(self.update_ini_file)
        button_layout.addWidget(self.pushButton_update_config)
        
        self.pushButton_run_screening = QPushButton("Run Screening")
        self.pushButton_run_screening.setToolTip("Run the screening process with the current settings.")
        self.pushButton_run_screening.clicked.connect(self.run_screening_process)
        button_layout.addWidget(self.pushButton_run_screening)
        
        self.pushButton_reset_defaults = QPushButton("Reset to Defaults")
        self.pushButton_reset_defaults.setToolTip("Reset all parameters to their default values.")
        self.pushButton_reset_defaults.clicked.connect(self.load_default_values)
        button_layout.addWidget(self.pushButton_reset_defaults)
        
        button_container = QWidget()
        button_container.setLayout(button_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, button_container)
        current_row += 1
        self.all_parameter_widgets.append((button_container, "always"))
        
        # Set scroll area
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.mainLayout.addWidget(self.scrollArea)
        
        # Status bar
        self.statusbar = QtWidgets.QStatusBar(Screening)
        Screening.setStatusBar(self.statusbar)
        
        # Connect signals
        self.radio_fp_fast.toggled.connect(self._update_fingerprint_settings)
        self.radio_fp_balanced.toggled.connect(self._update_fingerprint_settings)
        self.radio_fp_accurate.toggled.connect(self._update_fingerprint_settings)
        self.lineEdit_output_dir.textChanged.connect(self._save_shared_output_preferences)
        self.lineEdit_output_file.textChanged.connect(self._save_shared_output_preferences)
        
        self.radio_active_single.toggled.connect(self._toggle_active_epsilon_ui)
        self.radio_active_range.toggled.connect(self._toggle_active_epsilon_ui)
        self.radio_active_manual.toggled.connect(self._toggle_active_epsilon_ui)
        
        self.radio_inactive_single.toggled.connect(self._toggle_inactive_epsilon_ui)
        self.radio_inactive_range.toggled.connect(self._toggle_inactive_epsilon_ui)
        self.radio_inactive_manual.toggled.connect(self._toggle_inactive_epsilon_ui)
        
        # Initialize UI state
        self.load_default_values()
        self._update_parameter_visibility()
        self._toggle_training_uploads()
        self._toggle_active_epsilon_ui()
        self._toggle_inactive_epsilon_ui()
        self._update_fingerprint_settings()
        self._toggle_inhibition_thresholds()
        self._toggle_filter_properties()  # hide filter fields initially


        self.retranslateUi(Screening)
        QtCore.QMetaObject.connectSlotsByName(Screening)

    def _toggle_training_uploads(self):
        """Toggle visibility of training dataset upload options"""
        use_chembl = self.checkBox_use_chembl.isChecked()
        
        # Show ChEMBL file when using ChEMBL
        self.label_chembl_file.setVisible(use_chembl)
        self.lineEdit_chembl_file.parentWidget().setVisible(use_chembl)
        
        # Show actives/inactives files when not using ChEMBL
        self.label_actives_file.setVisible(not use_chembl)
        self.lineEdit_actives_file.parentWidget().setVisible(not use_chembl)
        self.label_inactives_file.setVisible(not use_chembl)
        self.lineEdit_inactives_file.parentWidget().setVisible(not use_chembl)

    def _update_parameter_visibility(self):
        """Update parameter visibility based on expert mode"""
        expert_mode = self.expertModeCheckbox.isChecked()
        
        for widget, visibility in self.all_parameter_widgets:
            if visibility == "always":
                widget.setVisible(True)
            elif visibility == "beginner":
                widget.setVisible(True)  # Always visible
            elif visibility == "expert":
                widget.setVisible(expert_mode)
        
        # Update training uploads visibility
        self._toggle_training_uploads()

    def _update_fingerprint_settings(self):
        """Update fingerprint settings based on selected type"""
        if self.radio_fp_fast.isChecked():
            self.comboBox_fp_type.setCurrentText("mhfp")
            self.lineEdit_fp_size.setText("1024")
            self.lineEdit_fp_radius.setText("3")
        elif self.radio_fp_balanced.isChecked():
            self.comboBox_fp_type.setCurrentText("mhfp")
            self.lineEdit_fp_size.setText("2048")
            self.lineEdit_fp_radius.setText("3")
        elif self.radio_fp_accurate.isChecked():
            self.comboBox_fp_type.setCurrentText("mhfp")
            self.lineEdit_fp_size.setText("4096")
            self.lineEdit_fp_radius.setText("3")

    def _toggle_active_epsilon_ui(self):
        """Toggle active epsilon UI elements based on selection"""
        single_selected = self.radio_active_single.isChecked()
        range_selected = self.radio_active_range.isChecked()
        manual_selected = self.radio_active_manual.isChecked()
        
        self.label_active_single.setVisible(single_selected)
        self.lineEdit_active_single.setVisible(single_selected)
        
        self.label_active_range.setVisible(range_selected)
        self.lineEdit_active_min.parentWidget().setVisible(range_selected)
        
        self.label_active_manual.setVisible(manual_selected)
        self.lineEdit_active_manual.setVisible(manual_selected)

    def _toggle_inactive_epsilon_ui(self):
        """Toggle inactive epsilon UI elements based on selection"""
        single_selected = self.radio_inactive_single.isChecked()
        range_selected = self.radio_inactive_range.isChecked()
        manual_selected = self.radio_inactive_manual.isChecked()
        
        self.label_inactive_single.setVisible(single_selected)
        self.lineEdit_inactive_single.setVisible(single_selected)
        
        self.label_inactive_range.setVisible(range_selected)
        self.lineEdit_inactive_min.parentWidget().setVisible(range_selected)
        
        self.label_inactive_manual.setVisible(manual_selected)
        self.lineEdit_inactive_manual.setVisible(manual_selected)
    
    def _toggle_filter_properties(self):
        """Show or hide filter property fields based on checkbox"""
        enabled = self.checkBox_use_filter.isChecked()
        for widget, visibility in self.all_parameter_widgets:
            if visibility == "filter":
                widget.setVisible(enabled)

    def _toggle_inhibition_thresholds(self):
        """Show or hide inhibition threshold fields based on checkbox"""
        enabled = self.checkBox_use_inhibition.isChecked()
        for widget, visibility in self.all_parameter_widgets:
            if visibility == "inhibition":
                widget.setVisible(enabled)


    def _preview_active_epsilon_values(self):
        """Preview and edit active epsilon values, and save to tc_actives.txt"""
        values = []
        
        if self.radio_active_single.isChecked():
            try:
                value = float(self.lineEdit_active_single.text())
                values = [value]
            except ValueError:
                QMessageBox.warning(self.centralwidget, "Invalid Input", "Please enter a valid number for single value.")
                return
        elif self.radio_active_range.isChecked():
            try:
                min_val = float(self.lineEdit_active_min.text())
                max_val = float(self.lineEdit_active_max.text())
                step = float(self.lineEdit_active_step.text())
                
                if min_val >= max_val:
                    QMessageBox.warning(self.centralwidget, "Invalid Range", "Minimum value must be less than maximum value.")
                    return
                if step <= 0:
                    QMessageBox.warning(self.centralwidget, "Invalid Step", "Step must be greater than 0.")
                    return
                
                current = min_val
                while current <= max_val:
                    values.append(round(current, 3))
                    current += step
            except ValueError:
                QMessageBox.warning(self.centralwidget, "Invalid Input", "Please enter valid numbers for range values.")
                return
        elif self.radio_active_manual.isChecked():
            try:
                manual_text = self.lineEdit_active_manual.text()
                parts = manual_text.replace(' ', '').split(',')
                
                for part in parts:
                    if '-' in part and not part.startswith('-'):
                        # Range format like "0.1-0.5"
                        range_parts = part.split('-')
                        if len(range_parts) == 2:
                            start = float(range_parts[0])
                            end = float(range_parts[1])
                            # Generate values with 0.1 step
                            current = start
                            while current <= end:
                                values.append(round(current, 1))
                                current += 0.1
                    else:
                        # Single value
                        values.append(float(part))
            except ValueError:
                QMessageBox.warning(self.centralwidget, "Invalid Input", "Please enter valid manual values (e.g., 0.1,0.5,0.8 or 0.1-0.5).")
                return
        
        if values:
            dialog = EpsilonSelectionDialog(self.centralwidget, "Active Epsilon Values", values)
            if dialog.exec_() == QDialog.Accepted:
                self.active_epsilon_values = dialog.get_values()
                
                # Save active epsilon values to tc_actives.txt
                try:
                    with open('tc_actives.txt', 'w') as f:
                        for value in self.active_epsilon_values:
                            f.write(f"{value:.2f}\n")
                    QMessageBox.information(self.centralwidget, "Values Updated", f"Active epsilon values updated and saved to tc_actives.txt: {len(self.active_epsilon_values)} values selected.")
                except Exception as e:
                    QMessageBox.critical(self.centralwidget, "Error", f"Failed to save active epsilon values: {str(e)}")

    def _preview_inactive_epsilon_values(self):
        """Preview and edit inactive epsilon values, and save to tc_inactives.txt"""
        values = []
        
        if self.radio_inactive_single.isChecked():
            try:
                value = float(self.lineEdit_inactive_single.text())
                values = [value]
            except ValueError:
                QMessageBox.warning(self.centralwidget, "Invalid Input", "Please enter a valid number for single value.")
                return
        elif self.radio_inactive_range.isChecked():
            try:
                min_val = float(self.lineEdit_inactive_min.text())
                max_val = float(self.lineEdit_inactive_max.text())
                step = float(self.lineEdit_inactive_step.text())
                
                if min_val >= max_val:
                    QMessageBox.warning(self.centralwidget, "Invalid Range", "Minimum value must be less than maximum value.")
                    return
                if step <= 0:
                    QMessageBox.warning(self.centralwidget, "Invalid Step", "Step must be greater than 0.")
                    return
                
                current = min_val
                while current <= max_val:
                    values.append(round(current, 3))
                    current += step
            except ValueError:
                QMessageBox.warning(self.centralwidget, "Invalid Input", "Please enter valid numbers for range values.")
                return
        elif self.radio_inactive_manual.isChecked():
            try:
                manual_text = self.lineEdit_inactive_manual.text()
                parts = manual_text.replace(' ', '').split(',')
                
                for part in parts:
                    if '-' in part and not part.startswith('-'):
                        # Range format like "0.1-0.5"
                        range_parts = part.split('-')
                        if len(range_parts) == 2:
                            start = float(range_parts[0])
                            end = float(range_parts[1])
                            # Generate values with 0.1 step
                            current = start
                            while current <= end:
                                values.append(round(current, 1))
                                current += 0.1
                    else:
                        # Single value
                        values.append(float(part))
            except ValueError:
                QMessageBox.warning(self.centralwidget, "Invalid Input", "Please enter valid manual values (e.g., 0.1,0.5,0.8 or 0.1-0.5).")
                return
        
        if values:
            dialog = EpsilonSelectionDialog(self.centralwidget, "Inactive Epsilon Values", values)
            if dialog.exec_() == QDialog.Accepted:
                self.inactive_epsilon_values = dialog.get_values()
                
                # Save inactive epsilon values to tc_inactives.txt
                try:
                    with open('tc_inactives.txt', 'w') as f:
                        for value in self.inactive_epsilon_values:
                            f.write(f"{value:.2f}\n")
                    QMessageBox.information(self.centralwidget, "Values Updated", f"Inactive epsilon values updated and saved to tc_inactives.txt: {len(self.inactive_epsilon_values)} values selected.")
                except Exception as e:
                    QMessageBox.critical(self.centralwidget, "Error", f"Failed to save inactive epsilon values: {str(e)}")

    def browse_file(self, file_path_attr, line_edit, dialog_title):
        """Browse for a file and update the corresponding line edit"""
        file_path, _ = QFileDialog.getOpenFileName(self.centralwidget, dialog_title, "", "All Files (*)")
        if file_path:
            setattr(self, file_path_attr, file_path)
            line_edit.setText(file_path)

    def browse_output_directory(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(self.centralwidget, "Select Output Directory")
        if directory:
            self.screening_output_directory = directory
            self.lineEdit_output_dir.setText(directory)
    
    def load_chembl_data_file(self, file_path):
        try:
            if file_path and os.path.exists(file_path):
                # Set the ChEMBL file path
                self.file_path_chembl = file_path
                self.lineEdit_chembl_file.setText(file_path)
                
                # Enable ChEMBL dataset checkbox
                self.checkBox_use_chembl.setChecked(True)
                
                # # <<< Add this line here
                # self._update_actives_inactives_count()
                
                QMessageBox.information(
                    self.centralwidget,
                    "Success",
                    f"ChEMBL data file loaded successfully:\n{file_path}"
                )
            else:
                QMessageBox.warning(
                    self.centralwidget,
                    "File Not Found",
                    f"The specified file does not exist:\n{file_path}"
                )
        except Exception as e:
            QMessageBox.critical(
                self.centralwidget,
                "Error",
                f"Failed to load ChEMBL data file:\n{str(e)}"
            )
            
    # def _update_actives_inactives_count(self):
    #     import pandas as pd
    #     chembl_file = self.lineEdit_chembl_file.text().strip()
    #     try:
    #         if not chembl_file or not os.path.exists(chembl_file):
    #             self.label_actives_count.setText("Actives below threshold: 0")
    #             self.label_inactives_count.setText("Inactives above threshold: 0")
    #             return

    #         df = pd.read_csv(chembl_file, sep=None, engine='python')
    #         # Try to find the activity column
    #         activity_col = None
    #         for col in df.columns:
    #             if col.lower() in ["standard value", "standard_value", "activity", "activity_value"]:
    #                 activity_col = col
    #                 break
    #         if activity_col is None:
    #             self.label_actives_count.setText("No activity column found")
    #             self.label_inactives_count.setText("No activity column found")
    #             return

    #         try:
    #             activity_threshold = float(self.lineEdit_activity_threshold.text())
    #         except ValueError:
    #             activity_threshold = None
    #         try:
    #             inactivity_threshold = float(self.lineEdit_inactivity_threshold.text())
    #         except ValueError:
    #             inactivity_threshold = None

    #         if activity_threshold is not None:
    #             actives = df[df[activity_col] < activity_threshold]
    #             self.label_actives_count.setText(f"Actives below threshold: {len(actives)}")
    #         else:
    #             self.label_actives_count.setText("Actives below threshold: ?")

    #         if inactivity_threshold is not None:
    #             inactives = df[df[activity_col] > inactivity_threshold]
    #             self.label_inactives_count.setText(f"Inactives above threshold: {len(inactives)}")
    #         else:
    #             self.label_inactives_count.setText("Inactives above threshold: ?")

    #     except Exception as e:
    #         self.label_actives_count.setText("Error reading file")
    #         self.label_inactives_count.setText("Error reading file")

    def update_ini_file(self):
        """Update configuration file with current parameter values and save epsilon files"""
        try:
            # First save epsilon values to files
            self._save_epsilon_values_to_files()
            
            config = configparser.ConfigParser()
            
            # Add all sections
            config.add_section('MODE')
            config.add_section('TRAINING_DATASETS')
            config.add_section('FINGERPRINTS')
            config.add_section('DECOYS')
            config.add_section('CHEMBL_ACTIVITY_THRESHOLDS')
            config.add_section('CHEMBL_INHIBITION_THRESHOLDS')
            config.add_section('KFOLD_PARAMETERS')
            config.add_section('TRAINING_PARAMETERS')
            config.add_section('CLUSTERING')
            config.add_section('STAT_PARAMETERS')
            config.add_section('FILTER')
            
            # MODE section
            config.set('MODE', 'mode', 'screening')
            config.set('MODE', 'db_to_screen', self.lineEdit_db_to_screen.text())
            
            # Build full output path
            output_dir = self.lineEdit_output_dir.text().strip()
            output_file = self.lineEdit_output_file.text().strip()
            if output_dir and output_file:
                full_output_path = os.path.join(output_dir, output_file)
            elif output_file:
                full_output_path = output_file
            else:
                full_output_path = "PyRMD_database_predictions.csv"
            
            config.set('MODE', 'screening_output', full_output_path)
            config.set('MODE', 'sdf_results', str(self.checkBox_sdf_results.isChecked()).lower())
            config.set('MODE', 'benchmark_file', '')
            
            # TRAINING_DATASETS section
            use_chembl = self.checkBox_use_chembl.isChecked()
            config.set('TRAINING_DATASETS', 'use_chembl', str(use_chembl).lower())
            config.set('TRAINING_DATASETS', 'chembl_file', self.lineEdit_chembl_file.text())
            config.set('TRAINING_DATASETS', 'use_actives', str(not use_chembl).lower())
            config.set('TRAINING_DATASETS', 'actives_file', self.lineEdit_actives_file.text())
            config.set('TRAINING_DATASETS', 'use_inactives', str(not use_chembl).lower())
            config.set('TRAINING_DATASETS', 'inactives_file', self.lineEdit_inactives_file.text())
            
           
            # FINGERPRINTS section
            config.set('FINGERPRINTS', 'fp_type', self.comboBox_fp_type.currentText())
            config.set('FINGERPRINTS', 'nbits', self.lineEdit_fp_size.text().strip() or '1024')
            
            # Read from new checkboxes
            config.set('FINGERPRINTS', 'explicit_hydrogens', str(self.checkBox_explicit_H.isChecked()))
            config.set('FINGERPRINTS', 'iterations', self.lineEdit_fp_radius.text().strip() or '2')
            config.set('FINGERPRINTS', 'chirality', str(self.checkBox_chirality.isChecked()))
            config.set('FINGERPRINTS', 'redundancy', str(self.checkBox_redundancy.isChecked()))
            config.set('FINGERPRINTS', 'features', str(self.checkBox_features.isChecked()))
            
            # -----------------------------------------------------------
            
            # DECOYS section
            has_decoys_file = bool(self.lineEdit_decoys_file.text().strip())
            config.set('DECOYS', 'use_decoys', str(has_decoys_file).lower())
            config.set('DECOYS', 'decoys_file', self.lineEdit_decoys_file.text())
            config.set('DECOYS', 'sample_number', '1000000')
            
            # CHEMBL ACTIVITY THRESHOLDS
            config.set('CHEMBL_ACTIVITY_THRESHOLDS', 'activity_threshold', self.lineEdit_activity_threshold.text())
            config.set('CHEMBL_ACTIVITY_THRESHOLDS', 'inactivity_threshold', self.lineEdit_inactivity_threshold.text())

            # CHEMBL INHIBITION THRESHOLDS
            use_inhibition = self.checkBox_use_inhibition.isChecked()
            config.set('CHEMBL_INHIBITION_THRESHOLDS', 'chembl_inhibition_rate', str(use_inhibition).lower())

            if use_inhibition:
                config.set('CHEMBL_INHIBITION_THRESHOLDS', 'inhibition_inactivity_threshold', self.lineEdit_inhibition_inactive.text())
                # REMOVED the line for inhibition_activity_threshold
            
            # KFOLD_PARAMETERS section
            config.set('KFOLD_PARAMETERS', 'n_splits', self.lineEdit_n_splits.text())
            config.set('KFOLD_PARAMETERS', 'n_repeats', self.lineEdit_n_repeats.text())
            
            # TRAINING_PARAMETERS section
            # Note: Epsilon cutoff values are saved to tc_actives.txt and tc_inactives.txt files
            # and should NOT be included in the configuration file as per requirements
            active_val = "XXXX"  # Placeholder - actual values saved to tc_actives.txt
            inactive_val = "YYYY"  # Placeholder - actual values saved to tc_inactives.txt
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_actives', active_val)
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_inactives', inactive_val)
            
            # CLUSTERING section
            butina_cutoff_val = self.lineEdit_bu.text().strip()
            config.set('CLUSTERING', 'butina_cutoff', butina_cutoff_val)
            
            # STAT_PARAMETERS section
            config.set('STAT_PARAMETERS', 'beta', self.lineEdit_beta.text())
            config.set('STAT_PARAMETERS', 'alpha', self.lineEdit_alpha.text())
            
            # FILTER section
            use_filter = self.checkBox_use_filter.isChecked()
            config.set('FILTER', 'filter_properties', str(use_filter).lower())

            if use_filter:
                config.set('FILTER', 'molwt_min', self.filter_fields["Molecular Weight Min:"].text())
                config.set('FILTER', 'molwt_max', self.filter_fields["Molecular Weight Max:"].text())
                config.set('FILTER', 'logp_min', self.filter_fields["LogP Min:"].text())
                config.set('FILTER', 'logp_max', self.filter_fields["LogP Max:"].text())
                config.set('FILTER', 'hdonors_min', self.filter_fields["H-Bond Donors Min:"].text())
                config.set('FILTER', 'hdonors_max', self.filter_fields["H-Bond Donors Max:"].text())
                config.set('FILTER', 'haccept_min', self.filter_fields["H-Bond Acceptors Min:"].text())
                config.set('FILTER', 'haccept_max', self.filter_fields["H-Bond Acceptors Max:"].text())
                config.set('FILTER', 'rotabonds_min', self.filter_fields["Rotatable Bonds Min:"].text())
                config.set('FILTER', 'rotabonds_max', self.filter_fields["Rotatable Bonds Max:"].text())
                config.set('FILTER', 'heavat_min', self.filter_fields["Heavy Atoms Min:"].text())
                config.set('FILTER', 'heavat_max', self.filter_fields["Heavy Atoms Max:"].text())

            
            # Write config file
            with open('configuration_screening.ini', 'w') as configfile:
                config.write(configfile)
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to update configuration: {str(e)}")

    def _save_epsilon_values_to_files(self):
        """Save epsilon values to text files"""
        try:
            # Save active epsilon values
            if self.radio_active_single.isChecked():
                active_value = float(self.lineEdit_active_single.text())
                with open('tc_actives.txt', 'w') as f:
                    f.write(f"{active_value:.2f}\n")
            elif hasattr(self, 'active_epsilon_values') and self.active_epsilon_values:
                with open('tc_actives.txt', 'w') as f:
                    for value in self.active_epsilon_values:
                        f.write(f"{value:.2f}\n")
            
            # Save inactive epsilon values
            if self.radio_inactive_single.isChecked():
                inactive_value = float(self.lineEdit_inactive_single.text())
                with open('tc_inactives.txt', 'w') as f:
                    f.write(f"{inactive_value:.2f}\n")
            elif hasattr(self, 'inactive_epsilon_values') and self.inactive_epsilon_values:
                with open('tc_inactives.txt', 'w') as f:
                    for value in self.inactive_epsilon_values:
                        f.write(f"{value:.2f}\n")
                        
        except Exception as e:
            QMessageBox.warning(self.centralwidget, "Warning", f"Failed to save epsilon values: {str(e)}")

    def run_screening_process(self):
        """Run the screening process with CPU core selection and popups"""
        try:
            # Show CPU core selection dialog
            core_dialog = CPUCoreSelectionDialog(self.centralwidget)
            if core_dialog.exec_() != QDialog.Accepted:
                return  # User cancelled

            selected_cores = core_dialog.get_core_count()
            self.selected_cores = selected_cores

            # Disable the button while running
            self.pushButton_run_screening.setEnabled(False)
            self.pushButton_run_screening.setText("Running...")

            # Set environment variable for CPU cores
            os.environ['OMP_NUM_THREADS'] = str(selected_cores)
            os.environ['NUMBA_NUM_THREADS'] = str(selected_cores)

            # Inform the user that screening has started
            QMessageBox.information(
                self.centralwidget,
                "Screening Started",
                f"Screening process started using {selected_cores} CPU cores."
            )

            # Run the launch.sh synchronously (wait for it to finish)
            cmd = './launch.sh'
            result = subprocess.run(cmd, shell=True)

            # Re-enable button
            self.pushButton_run_screening.setEnabled(True)
            self.pushButton_run_screening.setText("Run Screening")

            # Show completion popup
            if result.returncode == 0:
                QMessageBox.information(
                    self.centralwidget,
                    "Screening Completed",
                    "Screening process finished successfully!"
                )
            else:
                QMessageBox.critical(
                    self.centralwidget,
                    "Screening Failed",
                    "Screening process encountered an error. Please check the logs."
                )

        except Exception as e:
            # Re-enable button in case of failure
            self.pushButton_run_screening.setEnabled(True)
            self.pushButton_run_screening.setText("Run Screening")
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to start screening: {str(e)}")

    def load_default_values(self):
        """Load default values into the form and update configuration file"""
        try:
            # Database and output settings
            self.lineEdit_db_to_screen.setText("")
            self.lineEdit_output_dir.setText("")
            self.lineEdit_output_file.setText("PyRMD_database_predictions.csv")
            self.checkBox_sdf_results.setChecked(False)
            
            # Training datasets
            self.checkBox_use_chembl.setChecked(True)
            self.lineEdit_chembl_file.setText("")
            self.lineEdit_actives_file.setText("")
            self.lineEdit_inactives_file.setText("")
            
            # Fingerprint settings - Default to balanced (mhfp)
            self.radio_fp_balanced.setChecked(True)
            self.comboBox_fp_type.setCurrentText("mhfp")
            self.lineEdit_fp_size.setText("2048")
            self.lineEdit_fp_radius.setText("3")            
            self.checkBox_explicit_H.setChecked(True)
            self.checkBox_chirality.setChecked(False)
            self.checkBox_redundancy.setChecked(True)
            self.checkBox_features.setChecked(False)
            
            # -----------------------------------------
            
            # Decoys
            self.lineEdit_decoys_file.setText("")
            
            # Epsilon values - Default to single 0.95
            self.radio_active_single.setChecked(True)
            self.radio_inactive_single.setChecked(True)
            self.lineEdit_active_single.setText("0.95")
            self.lineEdit_inactive_single.setText("0.95")
            
            # Clear range and manual fields
            self.lineEdit_active_min.setText("")
            self.lineEdit_active_max.setText("")
            self.lineEdit_active_step.setText("")
            self.lineEdit_active_manual.setText("")
            self.lineEdit_inactive_min.setText("")
            self.lineEdit_inactive_max.setText("")
            self.lineEdit_inactive_step.setText("")
            self.lineEdit_inactive_manual.setText("")
            
            # Clear epsilon value arrays
            self.active_epsilon_values = []
            self.inactive_epsilon_values = []
            
            # KFOLD parameters
            self.lineEdit_n_splits.setText("5")
            self.lineEdit_n_repeats.setText("3")
            
            # ChEMBL thresholds
            self.lineEdit_activity_threshold.setText("1001")
            self.lineEdit_inactivity_threshold.setText("39999")
            
            # --- MODIFIED INHIBITION RESET ---
            self.checkBox_use_inhibition.setChecked(False)
            self.lineEdit_inhibition_inactive.setText("11")
            
            # Clustering parameters
            self.lineEdit_bu.setText("0.7")  # Default Butina clustering cutoff
            self.lineEdit_bu.setToolTip("Enter the Butina clustering cutoff value.")
                        
            # Stat parameters
            self.lineEdit_beta.setText("1")
            self.lineEdit_alpha.setText("20")
            
            # Update fingerprint settings based on selection
            self._update_fingerprint_settings()
            
            # Update visibility based on training dataset selection
            self._toggle_training_uploads()

            # Restore shared output selection if available
            self._load_shared_output_preferences()
            
            # Update configuration file with defaults
            self.update_ini_file()
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to load default values: {str(e)}")

    def _as_bool(self, value, default=False):
        if isinstance(value, bool):
            return value
        if value is None:
            return default
        text = str(value).strip().lower()
        if text in ["1", "true", "yes", "y", "on"]:
            return True
        if text in ["0", "false", "no", "n", "off", ""]:
            return False
        return default

    def _shared_output_settings_path(self):
        return os.path.abspath("screening_output_preferences_pyrmd.json")

    def _load_shared_output_preferences(self):
        try:
            settings_path = self._shared_output_settings_path()
            if not os.path.exists(settings_path):
                return

            with open(settings_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)

            output_dir = str(data.get("output_dir", "")).strip()
            output_file = str(data.get("output_file", "")).strip()

            if output_dir:
                self.lineEdit_output_dir.setText(output_dir)
            if output_file:
                self.lineEdit_output_file.setText(output_file)
        except Exception:
            pass

    def _save_shared_output_preferences(self):
        try:
            payload = {
                "output_dir": self.lineEdit_output_dir.text().strip(),
                "output_file": self.lineEdit_output_file.text().strip(),
            }
            with open(self._shared_output_settings_path(), "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
        except Exception:
            pass

    def apply_benchmark_model_parameters(self, model_parameters):
        """Apply benchmark-row model parameters to screening UI and persist configuration."""
        if not isinstance(model_parameters, dict):
            return

        normalized = {}
        for key, value in model_parameters.items():
            normalized[str(key).strip().lower()] = "" if value is None else str(value).strip()

        def get_value(*keys):
            for key in keys:
                if key in normalized and normalized[key] != "":
                    return normalized[key]
            return ""

        fp_type = get_value("fp_type")
        if fp_type:
            self.comboBox_fp_type.setCurrentText(fp_type)

        nbits = get_value("nbits")
        nbits_int = None
        if nbits:
            try:
                nbits_int = int(float(nbits))
            except Exception:
                nbits_int = None

        if nbits_int == 1024:
            self.radio_fp_fast.setChecked(True)
            self._update_fingerprint_settings()
        elif nbits_int == 2048:
            self.radio_fp_balanced.setChecked(True)
            self._update_fingerprint_settings()
        elif nbits_int == 4096:
            self.radio_fp_accurate.setChecked(True)
            self._update_fingerprint_settings()

        if nbits:
            self.lineEdit_fp_size.setText(nbits)

        iterations = get_value("iterations")
        if iterations:
            self.lineEdit_fp_radius.setText(iterations)

        explicit_hydrogens = get_value("explicit_hydrogens")
        if explicit_hydrogens != "":
            self.checkBox_explicit_H.setChecked(self._as_bool(explicit_hydrogens))

        chirality = get_value("chirality")
        if chirality != "":
            self.checkBox_chirality.setChecked(self._as_bool(chirality))

        redundancy = get_value("redundancy")
        if redundancy != "":
            self.checkBox_redundancy.setChecked(self._as_bool(redundancy, default=True))

        features = get_value("features")
        if features != "":
            self.checkBox_features.setChecked(self._as_bool(features))

        activity_threshold = get_value("activity_threshold")
        if activity_threshold:
            self.lineEdit_activity_threshold.setText(activity_threshold)

        inactivity_threshold = get_value("inactivity_threshold")
        if inactivity_threshold:
            self.lineEdit_inactivity_threshold.setText(inactivity_threshold)

        inhibition_threshold = get_value("inhibition_threshold")
        if inhibition_threshold and inhibition_threshold not in ["0", "0.0"]:
            self.checkBox_use_inhibition.setChecked(True)
            self.lineEdit_inhibition_inactive.setText(inhibition_threshold)
        else:
            self.checkBox_use_inhibition.setChecked(False)

        epsilon_active = get_value("epsilon_cutoff_actives")
        if epsilon_active:
            self.radio_active_single.setChecked(True)
            self.lineEdit_active_single.setText(epsilon_active)

        epsilon_inactive = get_value("epsilon_cutoff_inactives")
        if epsilon_inactive:
            self.radio_inactive_single.setChecked(True)
            self.lineEdit_inactive_single.setText(epsilon_inactive)

        butina_cutoff = get_value("butina_cutoff", "cutoff")
        if butina_cutoff:
            self.lineEdit_bu.setText(butina_cutoff)

        beta_value = get_value("beta")
        if beta_value:
            self.lineEdit_beta.setText(beta_value)

        alpha_value = get_value("alpha")
        if alpha_value:
            self.lineEdit_alpha.setText(alpha_value)

        n_splits = get_value("n_splits")
        if n_splits:
            self.lineEdit_n_splits.setText(n_splits)

        n_repeats = get_value("n_repeats")
        if n_repeats:
            self.lineEdit_n_repeats.setText(n_repeats)

        use_decoys_value = get_value("use_decoys")
        decoys_file = get_value("decoys_file")
        if decoys_file:
            self.lineEdit_decoys_file.setText(decoys_file)
        elif use_decoys_value != "" and not self._as_bool(use_decoys_value):
            self.lineEdit_decoys_file.setText("")

        chembl_file = get_value("chembl_file")
        actives_file = get_value("actives_file")
        inactives_file = get_value("inactives_file")

        if chembl_file:
            self.checkBox_use_chembl.setChecked(True)
            self.lineEdit_chembl_file.setText(chembl_file)
        else:
            self.checkBox_use_chembl.setChecked(False)
            if actives_file:
                self.lineEdit_actives_file.setText(actives_file)
            if inactives_file:
                self.lineEdit_inactives_file.setText(inactives_file)

        self.active_epsilon_values = []
        self.inactive_epsilon_values = []
        self._toggle_training_uploads()
        self._save_shared_output_preferences()
        self.update_ini_file()

    def retranslateUi(self, Screening):
        _translate = QtCore.QCoreApplication.translate
        Screening.setWindowTitle(_translate("Screening", f"Screening - {self.selected_module}"))

    def set_color_palette(self, color_background, color_foreground, color_primary, color_accent, color_button_text, color_input_bg, color_input_text):
        """Set color palette for the UI with comprehensive theme support"""
        # Store colors for potential future use
        self.color_background = color_background
        self.color_foreground = color_foreground
        self.color_primary = color_primary
        self.color_accent = color_accent
        self.color_button_text = color_button_text
        self.color_input_bg = color_input_bg
        self.color_input_text = color_input_text
        
        # Apply comprehensive color scheme to the main window and all child widgets
        comprehensive_style = f"""
            QMainWindow {{
                background-color: {color_background};
                color: {color_foreground};
            }}
            QWidget {{
                background-color: {color_background};
                color: {color_foreground};
            }}
            QPushButton {{
                background-color: {color_primary};
                color: {color_button_text};
                border: 1px solid {color_accent};
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 25px;
            }}
            QPushButton:hover {{
                background-color: {color_accent};
                border: 1px solid {color_primary};
            }}
            QPushButton:pressed {{
                background-color: {color_accent};
                border: 2px solid {color_primary};
            }}
            QPushButton:disabled {{
                background-color: #CCCCCC;
                color: #666666;
                border: 1px solid #AAAAAA;
            }}
            QLineEdit, QTextEdit, QPlainTextEdit {{
                background-color: {color_input_bg};
                color: {color_input_text};
                border: 2px solid {color_accent};
                padding: 5px;
                border-radius: 4px;
                selection-background-color: {color_primary};
                selection-color: {color_button_text};
            }}
            QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {color_primary};
            }}
            QLabel {{
                color: {color_foreground};
                background-color: transparent;
            }}
            QCheckBox, QRadioButton {{
                color: {color_foreground};
                background-color: transparent;
            }}
            QCheckBox::indicator, QRadioButton::indicator {{
                background-color: {color_input_bg};
                border: 2px solid {color_accent};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
                background-color: {color_primary};
                border: 2px solid {color_primary};
            }}
            QComboBox {{
                background-color: {color_input_bg};
                color: {color_input_text};
                border: 2px solid {color_accent};
                padding: 5px;
                border-radius: 4px;
            }}
            QComboBox:focus {{
                border: 2px solid {color_primary};
            }}
            QComboBox::drop-down {{
                border: none;
                background-color: {color_primary};
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {color_button_text};
            }}
            QComboBox QAbstractItemView {{
                background-color: {color_input_bg};
                color: {color_input_text};
                border: 1px solid {color_accent};
                selection-background-color: {color_primary};
                selection-color: {color_button_text};
            }}
            QSpinBox, QDoubleSpinBox {{
                background-color: {color_input_bg};
                color: {color_input_text};
                border: 2px solid {color_accent};
                padding: 5px;
                border-radius: 4px;
            }}
            QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {color_primary};
            }}
            QScrollArea {{
                background-color: {color_background};
                border: 1px solid {color_accent};
            }}
            QScrollBar:vertical {{
                background-color: {color_background};
                width: 15px;
                border: 1px solid {color_accent};
            }}
            QScrollBar::handle:vertical {{
                background-color: {color_primary};
                border-radius: 7px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {color_accent};
            }}
            QScrollBar:horizontal {{
                background-color: {color_background};
                height: 15px;
                border: 1px solid {color_accent};
            }}
            QScrollBar::handle:horizontal {{
                background-color: {color_primary};
                border-radius: 7px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background-color: {color_accent};
            }}
            QGroupBox {{
                color: {color_foreground};
                border: 2px solid {color_accent};
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: {color_background};
            }}
            QTabWidget::pane {{
                border: 1px solid {color_accent};
                background-color: {color_background};
            }}
            QTabBar::tab {{
                background-color: {color_input_bg};
                color: {color_input_text};
                border: 1px solid {color_accent};
                padding: 8px 15px;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background-color: {color_primary};
                color: {color_button_text};
            }}
            QTabBar::tab:hover {{
                background-color: {color_accent};
            }}
            QProgressBar {{
                background-color: {color_input_bg};
                border: 2px solid {color_accent};
                border-radius: 5px;
                text-align: center;
                color: {color_foreground};
            }}
            QProgressBar::chunk {{
                background-color: {color_primary};
                border-radius: 3px;
            }}
            QStatusBar {{
                background-color: {color_background};
                color: {color_foreground};
                border-top: 1px solid {color_accent};
            }}
            QMenuBar {{
                background-color: {color_background};
                color: {color_foreground};
                border-bottom: 1px solid {color_accent};
            }}
            QMenuBar::item {{
                background-color: transparent;
                padding: 5px 10px;
            }}
            QMenuBar::item:selected {{
                background-color: {color_primary};
                color: {color_button_text};
            }}
            QMenu {{
                background-color: {color_input_bg};
                color: {color_input_text};
                border: 1px solid {color_accent};
            }}
            QMenu::item {{
                padding: 5px 20px;
            }}
            QMenu::item:selected {{
                background-color: {color_primary};
                color: {color_button_text};
            }}
            QDialog {{
                background-color: {color_background};
                color: {color_foreground};
            }}
            QMessageBox {{
                background-color: {color_background};
                color: {color_foreground};
            }}
        """
        
        # Apply to the main window if available
        if hasattr(self, 'centralwidget') and hasattr(self.centralwidget, 'parent') and self.centralwidget.parent():
            self.centralwidget.parent().setStyleSheet(comprehensive_style)
        
        # Also apply to central widget
        if hasattr(self, 'centralwidget'):
            self.centralwidget.setStyleSheet(comprehensive_style)


# Original main function from Screening.py (commented out for integration)
# if __name__ == "__main__":
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     ScreeningWindow = QtWidgets.QMainWindow()
#     ui = Ui_Screening()
#     ui.setupUi(ScreeningWindow)
#     ScreeningWindow.show()
#     sys.exit(app.exec_())



# ============================================================================
# COMPLETE ORIGINAL RMD_ANALYSIS.PY CODE (UNMODIFIED)
# ============================================================================

import sys
import os
import pandas as pd
import numpy as np
import time
import argparse
import matplotlib
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QFileDialog,
    QStatusBar,
    QGroupBox,
    QGridLayout,
    QSizePolicy,
    QFrame,
    QMessageBox,
    QSlider,
    QTextEdit,
    QComboBox,
    QLineEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QCursor, QFont
from scipy import stats


class MplCanvas(FigureCanvas):
    """Matplotlib canvas class for embedding plots in PyQt"""

    thresholdMoved = pyqtSignal(float)

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Set up figure with light theme for modern look
        plt.style.use("default")
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor("white")
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor("#f8f9fa")

        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        # Initialize variables
        self.all_data = None
        self.threshold_line = None
        self.selected_region = None
        self.threshold_annotation = None
        self.dragging_threshold = False

        # Connect events for ruler interaction
        self.mpl_connect("button_press_event", self.on_mouse_press)
        self.mpl_connect("button_release_event", self.on_mouse_release)
        self.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.mpl_connect("figure_enter_event", self.on_figure_enter)
        self.mpl_connect("figure_leave_event", self.on_figure_leave)

    def on_figure_enter(self, event):
        """Handle mouse entering the figure"""
        if self.threshold_line is not None:
            self.setCursor(Qt.CrossCursor)

    def on_figure_leave(self, event):
        """Handle mouse leaving the figure"""
        self.setCursor(Qt.ArrowCursor)

    def on_mouse_press(self, event):
        """Handle mouse press event for threshold line dragging"""
        if event.inaxes != self.axes or self.threshold_line is None:
            return

        # Check if click is near the threshold line
        threshold_x = self.threshold_line.get_xdata()[0]
        if abs(event.xdata - threshold_x) < 0.5:  # Tolerance for clicking
            self.dragging_threshold = True
            self.setCursor(Qt.SizeHorCursor)

    def on_mouse_release(self, event):
        """Handle mouse release event for threshold line dragging"""
        if self.dragging_threshold:
            self.dragging_threshold = False
            self.setCursor(Qt.ArrowCursor)
            if event.xdata is not None:
                self.thresholdMoved.emit(event.xdata)

    def on_mouse_move(self, event):
        """Handle mouse move event for threshold line dragging"""
        if self.dragging_threshold and event.xdata is not None:
            # --- NEW CODE: Constrain x to data limits ---
            min_val = float(np.min(self.all_data))
            max_val = float(np.max(self.all_data))
            
            # "Clamp" the value so it cannot go below min or above max
            new_x = max(min_val, min(event.xdata, max_val))
            # ---------------------------------------------

            # Update threshold line position using the constrained new_x
            self.threshold_line.set_xdata([new_x, new_x])
            
            # Update annotation if exists
            if self.threshold_annotation:
                self.threshold_annotation.set_text(f"Threshold: {new_x:.3f}")
                self.threshold_annotation.set_position((new_x + 0.1, self.threshold_annotation.get_position()[1]))

            # Update highlighted region in real-time
            if self.selected_region:
                # Remove old highlighted region
                self.selected_region.remove()
                
                # Calculate selected count for real-time update
                selected_count = len(self.all_data[self.all_data > new_x])
                total_count = len(self.all_data)
                percentage = (selected_count / total_count) * 100 if total_count > 0 else 0
                
                # Add new highlighted region (RIGHT side of threshold)
                self.selected_region = self.axes.axvspan(
                    new_x, max(self.all_data), alpha=0.2, color="#27ae60", 
                    label=f"Selected Range ({selected_count} compounds, {percentage:.1f}%)"
                )

            # Update legend in real-time
            self.update_legend_realtime(new_x)

            # Redraw with lower latency for smoother movement
            self.draw_idle()
            self.thresholdMoved.emit(new_x)
            
        elif self.threshold_line is not None and event.inaxes == self.axes:
            threshold_x = self.threshold_line.get_xdata()[0]
            if abs(event.xdata - threshold_x) < 0.5:
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.ArrowCursor)

    def update_legend_realtime(self, threshold):
        """Update legend during real-time threshold movement"""
        if self.all_data is None:
            return
        
        # Calculate selected count (right side of threshold)
        selected_count = len(self.all_data[self.all_data > threshold])
        total_count = len(self.all_data)
        percentage = (selected_count / total_count) * 100 if total_count > 0 else 0
        
        # Update legend labels
        legend = self.axes.get_legend()
        if legend:
            # --- CHANGED: Removed "All Compounds" from this list ---
            labels = [
                "Density Curve", 
                f"Threshold: {threshold:.3f}",
                f"Selected Range ({selected_count} compounds, {percentage:.1f}%)"
            ]
            # -------------------------------------------------------
            
            for i, text in enumerate(legend.get_texts()):
                if i < len(labels):
                    text.set_text(labels[i])

    def plot_distribution(self, data, threshold=None):
        """Plot the distribution with histogram and KDE curve"""
        self.all_data = data
        self.update_plot(threshold)

    def update_plot(self, threshold=None):
        """Update the plot with current threshold"""
        if self.all_data is None:
            return

        # Clear previous plot
        self.axes.clear()
        self.threshold_line = None
        self.selected_region = None
        self.threshold_annotation = None

        # --- CHANGED: Removed label="All Compounds" argument ---
        # Create histogram
        n, bins, patches = self.axes.hist(
            self.all_data, bins=40, alpha=0.7, color="#4a69bd" 
        )
        # -----------------------------------------------------

        # Apply gradient coloring to histogram bars
        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        col = bin_centers - min(bin_centers)
        col /= max(col)

        if hasattr(matplotlib, "colormaps"):
            cm = matplotlib.colormaps["viridis"]
        else:
            cm = plt.cm.viridis

        for c, p in zip(col, patches):
            plt.setp(p, "facecolor", cm(c))

        # Add KDE curve
        kde = stats.gaussian_kde(self.all_data)
        x_grid = np.linspace(min(self.all_data), max(self.all_data), 1000)
        kde_values = kde(x_grid)

        # Scale KDE to match histogram height
        scale_factor = max(n) / max(kde_values) * 0.8
        kde_values = kde_values * scale_factor

        self.axes.plot(x_grid, kde_values, "r-", linewidth=2, label="Density Curve")

        # Add threshold line if specified (always visible when data is loaded)
        if threshold is not None:
            y_max = max(n) * 1.1
            self.threshold_line = self.axes.axvline(
                x=threshold,
                color="#e74c3c",
                linestyle="--",
                linewidth=3,
                alpha=0.8,
                label=f"Threshold: {threshold:.3f}"
            )
            # Add annotation for the threshold line
            self.threshold_annotation = self.axes.annotate(
                f"Threshold: {threshold:.3f}",
                xy=(threshold, y_max * 0.95),
                xytext=(threshold + 0.1, y_max * 0.9),
                color="#e74c3c",
                weight="bold",
                fontsize=10,
                ha="left",
                va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#e74c3c", alpha=0.9),
            )

            # Highlight selected region (RIGHT side of threshold - higher scores)
            selected_count = len(self.all_data[self.all_data > threshold])
            total_count = len(self.all_data)
            percentage = (selected_count / total_count) * 100 if total_count > 0 else 0
            
            self.selected_region = self.axes.axvspan(
                threshold, max(self.all_data), alpha=0.2, color="#27ae60", 
                label=f"Selected Range ({selected_count} compounds, {percentage:.1f}%)"
            )

        # Set labels and title
        self.axes.set_xlabel("RMD Score", fontsize=12, weight="bold")
        self.axes.set_ylabel("Frequency", fontsize=12, weight="bold")
        self.axes.set_title("RMD Score Distribution", fontsize=14, weight="bold")

        # Add grid and legend
        self.axes.grid(True, alpha=0.3)
        self.axes.legend()

        # Redraw the canvas
        self.draw()


class StatisticsPanel(QWidget):
    """Panel for displaying statistical information with direct export"""

    thresholdChanged = pyqtSignal(float)
    exportRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.data = None
        self.initUI()

    def initUI(self):
        """Initialize the UI for statistics panel"""
        layout = QVBoxLayout(self)

        # Overall statistics group
        overall_group = QGroupBox("Overall Statistics")
        overall_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
                color: #3498db;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        overall_layout = QGridLayout(overall_group)

        # Create labels for overall statistics
        self.overall_labels = {}
        # --- CHANGED: Replaced 'Mode' with 'Variance' ---
        stats_names = ["Min", "Max", "Mean", "Median", "Variance", "Std Dev"]
        # -----------------------------------------------
        for i, stat in enumerate(stats_names):
            label = QLabel(f"{stat}:")
            value_label = QLabel("N/A")
            value_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            overall_layout.addWidget(label, i // 2, (i % 2) * 2)
            overall_layout.addWidget(value_label, i // 2, (i % 2) * 2 + 1)
            self.overall_labels[stat.lower().replace(" ", "_")] = value_label

        layout.addWidget(overall_group)

        # Threshold control and export group
        threshold_group = QGroupBox("Threshold Control & Export")
        threshold_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #27ae60;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
                color: #27ae60;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        threshold_layout = QGridLayout(threshold_group)

        # Threshold type selection
        threshold_layout.addWidget(QLabel("Threshold Type:"), 0, 0)
        self.threshold_type_combo = QComboBox()
        self.threshold_type_combo.addItems([
            "RMD Score",
            "Compound Count", 
            "Percentage"
        ])
        self.threshold_type_combo.currentTextChanged.connect(self.on_threshold_type_changed)
        threshold_layout.addWidget(self.threshold_type_combo, 0, 1)

        # Threshold value input
        threshold_layout.addWidget(QLabel("Value:"), 1, 0)
        self.threshold_input = QDoubleSpinBox()
        self.threshold_input.setRange(-1000.0, 1000.0)
        self.threshold_input.setDecimals(4)
        self.threshold_input.setValue(0.0)
        self.threshold_input.setStyleSheet("""
            QDoubleSpinBox {
                font-weight: bold; 
                color: #e74c3c;
                border: 2px solid #e74c3c;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        self.threshold_input.valueChanged.connect(self.on_threshold_input_changed)
        threshold_layout.addWidget(self.threshold_input, 1, 1)

        # Export button
        self.export_button = QPushButton("Export Selected Compounds as CSV")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #219a52;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.export_button.clicked.connect(self.on_export_clicked)
        self.export_button.setEnabled(False)
        threshold_layout.addWidget(self.export_button, 2, 0, 1, 2)

        layout.addWidget(threshold_group)

        # Selected range statistics group (now for RIGHT side)
        selected_group = QGroupBox("Selected Range Statistics (Right Side)")
        selected_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #27ae60;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
                color: #27ae60;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        selected_layout = QGridLayout(selected_group)

        # Create labels for selected range statistics
        self.selected_labels = {}
        selected_stats = ["Count", "Compounds", "Percentage"]
        for i, stat in enumerate(selected_stats):
            label = QLabel(f"{stat}:")
            value_label = QLabel("N/A")
            value_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            selected_layout.addWidget(label, i, 0)
            selected_layout.addWidget(value_label, i, 1)
            self.selected_labels[stat.lower()] = value_label

        layout.addWidget(selected_group)

        # Less than or equal threshold statistics group (now for LEFT side)
        less_group = QGroupBox("Less Than or Equal Threshold Statistics (Left Side)")
        less_group.setStyleSheet("""
            QGroupBox {
                border: 2px solid #e74c3c;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
                color: #e74c3c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }
        """)
        less_layout = QGridLayout(less_group)

        # Create labels for less than threshold statistics
        self.less_labels = {}
        # --- CHANGED: Replaced 'Mode' with 'Variance' ---
        less_stats = ["Mean", "Median", "Variance", "Std Dev"]
        # -----------------------------------------------
        for i, stat in enumerate(less_stats):
            label = QLabel(f"{stat}:")
            value_label = QLabel("N/A")
            value_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
            less_layout.addWidget(label, i // 2, (i % 2) * 2)
            less_layout.addWidget(value_label, i // 2, (i % 2) * 2 + 1)
            self.less_labels[stat.lower().replace(" ", "_")] = value_label

        layout.addWidget(less_group)

    def set_data(self, data):
        """Set the data for threshold calculations"""
        self.data = data
        self.export_button.setEnabled(True)
        
        # --- NEW CODE: Strictly limit input to data min/max ---
        if self.data is not None and len(self.data) > 0:
            min_val = float(np.min(self.data))
            max_val = float(np.max(self.data))
            # Removed the "- 1" and "+ 1" padding here
            self.threshold_input.setRange(min_val, max_val)

    def on_export_clicked(self):
        """Handle export button click"""
        self.exportRequested.emit()

    def on_threshold_type_changed(self, threshold_type):
        """Handle threshold type change"""
        if self.data is None:
            return
            
        if threshold_type == "RMD Score":
            min_val = float(np.min(self.data))
            max_val = float(np.max(self.data))
            # --- NEW CODE: Strict limits, no padding ---
            self.threshold_input.setRange(min_val, max_val)
            # -------------------------------------------
            self.threshold_input.setDecimals(4)
            self.threshold_input.setSuffix("")
            # Convert current value to RMD score if needed
            current_threshold = self.get_current_threshold_score()
            
            # Ensure the current threshold is within bounds (just in case)
            current_threshold = max(min_val, min(current_threshold, max_val))
            
            self.threshold_input.blockSignals(True)
            self.threshold_input.setValue(current_threshold)
            self.threshold_input.blockSignals(False)
            
        elif threshold_type == "Compound Count":
            # (This part remains mostly the same, naturally limited by count)
            self.threshold_input.setRange(1, len(self.data))
            self.threshold_input.setDecimals(0)
            self.threshold_input.setSuffix(" compounds")
            # ... rest of the logic is fine ...
            current_threshold = self.get_current_threshold_score()
            count = len(self.data[self.data > current_threshold])
            self.threshold_input.blockSignals(True)
            self.threshold_input.setValue(count)
            self.threshold_input.blockSignals(False)
            
        else:  # Percentage
            # (Percentages are naturally 0-100, which is safe)
            self.threshold_input.setRange(0.0, 100.0)
            self.threshold_input.setDecimals(2)
            self.threshold_input.setSuffix("%")
            # ... rest of the logic is fine ...
            current_threshold = self.get_current_threshold_score()
            count = len(self.data[self.data > current_threshold])
            percentage = (count / len(self.data)) * 100
            self.threshold_input.blockSignals(True)
            self.threshold_input.setValue(percentage)
            self.threshold_input.blockSignals(False)

    def get_current_threshold_score(self):
        """Get the current threshold as RMD score"""
        if self.data is None:
            return 0.0
        
        threshold_type = self.threshold_type_combo.currentText()
        value = self.threshold_input.value()
        
        if threshold_type == "RMD Score":
            return value
        elif threshold_type == "Compound Count":
            # Find the score that gives the specified compound count on the RIGHT side
            count = int(value)
            if count >= len(self.data):
                return np.min(self.data) - 1  # All compounds selected
            if count <= 0:
                return np.max(self.data) + 1  # No compounds selected
            # Sort in descending order to get highest scores first
            sorted_data = np.sort(self.data)[::-1]
            return sorted_data[count - 1]  # Threshold to get exactly 'count' compounds on right
        else:  # Percentage
            # Find the score that gives the specified percentage on the RIGHT side
            percentage = value / 100.0
            count = int(len(self.data) * percentage)
            if count >= len(self.data):
                return np.min(self.data) - 1  # All compounds selected
            if count <= 0:
                return np.max(self.data) + 1  # No compounds selected
            # Sort in descending order to get highest scores first
            sorted_data = np.sort(self.data)[::-1]
            return sorted_data[count - 1]  # Threshold to get exactly 'count' compounds on right

    def on_threshold_input_changed(self):
        """Handle threshold input change"""
        if self.data is None:
            return
        
        threshold_score = self.get_current_threshold_score()
        self.thresholdChanged.emit(threshold_score)

    def update_threshold_input(self, threshold_score):
        """Update threshold input without triggering signal"""
        if self.data is None:
            return
            
        threshold_type = self.threshold_type_combo.currentText()
        
        self.threshold_input.blockSignals(True)
        
        if threshold_type == "RMD Score":
            self.threshold_input.setValue(threshold_score)
        elif threshold_type == "Compound Count":
            count = len(self.data[self.data > threshold_score])  # RIGHT side count
            self.threshold_input.setValue(count)
        else:  # Percentage
            count = len(self.data[self.data > threshold_score])  # RIGHT side count
            percentage = (count / len(self.data)) * 100
            self.threshold_input.setValue(percentage)
            
        self.threshold_input.blockSignals(False)

    def update_overall_stats(self, data):
        """Update overall statistics"""
        if data is None or len(data) == 0:
            for label in self.overall_labels.values():
                label.setText("N/A")
            return

        try:
            # --- CHANGED: Calculate Variance instead of Mode ---
            stats_values = {
                "min": np.min(data),
                "max": np.max(data),
                "mean": np.mean(data),
                "median": np.median(data),
                "variance": np.var(data),  # New Variance calculation
                "std_dev": np.std(data)
            }
            # --------------------------------------------------

            # Update labels
            for stat, value in stats_values.items():
                if np.isnan(value):
                    self.overall_labels[stat].setText("N/A")
                else:
                    self.overall_labels[stat].setText(f"{value:.4f}")

        except Exception as e:
            print(f"Stats Error: {e}")
            for label in self.overall_labels.values():
                label.setText("Error")

    def update_selected_stats(self, data, total_count, threshold):
        """Update selected range statistics (RIGHT side - greater than threshold)"""
        if data is None or len(data) == 0:
            for label in self.selected_labels.values():
                label.setText("N/A")
            return

        try:
            # Calculate selected range statistics (RIGHT side)
            selected_data = data[data > threshold]
            count = len(selected_data)
            percentage = (count / total_count) * 100 if total_count > 0 else 0

            self.selected_labels["count"].setText(f"{count}")
            self.selected_labels["compounds"].setText(f"{count}")
            self.selected_labels["percentage"].setText(f"{percentage:.2f}%")

        except Exception as e:
            for label in self.selected_labels.values():
                label.setText("Error")

    def update_less_stats(self, data, threshold):
        """Update less than or equal threshold statistics (LEFT side)"""
        if data is None or len(data) == 0:
            for label in self.less_labels.values():
                label.setText("N/A")
            return

        try:
            # Calculate less than or equal threshold statistics (LEFT side)
            less_data = data[data <= threshold]
            
            if len(less_data) == 0:
                for label in self.less_labels.values():
                    label.setText("N/A")
                return

            # --- CHANGED: Calculate Variance instead of Mode ---
            stats_values = {
                "mean": np.mean(less_data),
                "median": np.median(less_data),
                "variance": np.var(less_data),  # New Variance calculation
                "std_dev": np.std(less_data)
            }
            # --------------------------------------------------

            # Update labels
            for stat, value in stats_values.items():
                if np.isnan(value):
                    self.less_labels[stat].setText("N/A")
                else:
                    self.less_labels[stat].setText(f"{value:.4f}")

        except Exception as e:
            print(f"Less Stats Error: {e}")
            for label in self.less_labels.values():
                label.setText("Error")


class StreamlinedCompoundAnalyzer(QMainWindow):
    """Streamlined Compound Analyzer with direct CSV export"""

    def __init__(self, input_file=None, output_file=None, status_file=None, modal_mode=False):
        super().__init__()

        self.data = None
        self.df = None
        self.input_file = input_file or ""
        self.score_column = None

        # Modal mode settings
        self.modal_mode = modal_mode
        self.output_file = output_file or ""
        self.status_file = status_file or ""

        # Set up UI
        self.initUI()

        # Load input file if provided
        if self.input_file and os.path.exists(self.input_file):
            self.load_data(self.input_file)

    def initUI(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Streamlined RMD Score Analyzer")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1200, 800)

        # Set light theme with enhanced styling
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: white;
                color: #333333;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #333333;
            }
            QDoubleSpinBox, QSpinBox, QComboBox {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px;
                background-color: white;
                selection-background-color: #3498db;
            }
            QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
                border: 2px solid #3498db;
            }
            QPushButton {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 6px;
                background-color: #f8f9fa;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border: 1px solid #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
            QPushButton:disabled {
                background-color: #f8f9fa;
                color: #6c757d;
                border: 1px solid #dee2e6;
            }
        """)

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left panel for controls
        left_panel = QWidget()
        left_panel.setMaximumWidth(400)
        left_layout = QVBoxLayout(left_panel)

        # File upload section
        file_group = QGroupBox("Data File")
        file_layout = QVBoxLayout(file_group)

        self.upload_button = QPushButton("Upload RMD Score File")
        self.upload_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        self.upload_button.clicked.connect(self.upload_file)
        file_layout.addWidget(self.upload_button)

        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: #666666; font-style: italic;")
        file_layout.addWidget(self.file_label)

        left_layout.addWidget(file_group)

        # Statistics panel (now includes direct export)
        self.stats_panel = StatisticsPanel()
        self.stats_panel.thresholdChanged.connect(self.on_threshold_input_changed)
        self.stats_panel.exportRequested.connect(self.export_selected_compounds)
        left_layout.addWidget(self.stats_panel)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # Right panel for plot
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Plot canvas
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.canvas.thresholdMoved.connect(self.on_graph_threshold_moved)
        right_layout.addWidget(self.canvas)

        # Plot controls
        plot_controls_layout = QHBoxLayout()
        
        save_plot_button = QPushButton("Save Plot")
        save_plot_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        save_plot_button.clicked.connect(self.save_plot)
        plot_controls_layout.addWidget(save_plot_button)
        
        plot_controls_layout.addStretch()
        right_layout.addLayout(plot_controls_layout)

        main_layout.addWidget(right_panel)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Please upload an RMD score file")

        # Initially disable controls
        self.disable_controls()

    def disable_controls(self):
        """Disable controls until data is loaded"""
        self.stats_panel.threshold_input.setEnabled(False)
        self.stats_panel.threshold_type_combo.setEnabled(False)
        self.stats_panel.export_button.setEnabled(False)

    def enable_controls(self):
        """Enable controls after data is loaded"""
        self.stats_panel.threshold_input.setEnabled(True)
        self.stats_panel.threshold_type_combo.setEnabled(True)
        self.stats_panel.export_button.setEnabled(True)

    def upload_file(self):
        """Show file upload dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open RMD Score File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self.load_data(file_path)

    def load_data(self, file_path):
        """Load data from CSV file with enhanced error handling"""
        try:
            # Validate file exists and is readable
            if not os.path.exists(file_path):
                QMessageBox.critical(self, "File Error", f"File does not exist: {file_path}")
                return
            
            if not os.access(file_path, os.R_OK):
                QMessageBox.critical(self, "File Error", f"Cannot read file: {file_path}")
                return

            # Show loading status
            self.statusBar.showMessage("Loading data...")
            QApplication.processEvents()

            # Load data with error handling
            try:
                self.df = pd.read_csv(file_path)
            except pd.errors.EmptyDataError:
                QMessageBox.critical(self, "Data Error", "The CSV file is empty.")
                return
            except pd.errors.ParserError as e:
                QMessageBox.critical(self, "Data Error", f"Error parsing CSV file: {str(e)}")
                return
            except UnicodeDecodeError:
                # Try different encodings
                try:
                    self.df = pd.read_csv(file_path, encoding='latin-1')
                except:
                    QMessageBox.critical(self, "Encoding Error", "Cannot read file with standard encodings.")
                    return

            self.input_file = file_path

            # Validate data
            if self.df.empty:
                QMessageBox.critical(self, "Data Error", "The CSV file contains no data.")
                return

            if len(self.df.columns) == 0:
                QMessageBox.critical(self, "Data Error", "The CSV file contains no columns.")
                return

            # Find score column with improved detection
            score_column = None
            possible_columns = [
                "rmd_score", "rmd", "score", "lowest_binding_energy", 
                "binding_energy", "docking_score", "affinity", "energy"
            ]

            # First, try exact matches
            for col in possible_columns:
                if col in self.df.columns:
                    score_column = col
                    break

            # If no exact match, try case-insensitive partial matches
            if score_column is None:
                for col in self.df.columns:
                    col_lower = col.lower()
                    for possible in possible_columns:
                        if possible in col_lower:
                            score_column = col
                            break
                    if score_column:
                        break

            # If still no match, look for any numeric column
            if score_column is None:
                numeric_columns = []
                for col in self.df.columns:
                    if pd.api.types.is_numeric_dtype(self.df[col]):
                        numeric_columns.append(col)
                
                if numeric_columns:
                    # If multiple numeric columns, prefer ones with 'score' or 'energy' in name
                    for col in numeric_columns:
                        if any(keyword in col.lower() for keyword in ['score', 'energy', 'affinity', 'bind']):
                            score_column = col
                            break
                    
                    # Otherwise use first numeric column
                    if score_column is None:
                        score_column = numeric_columns[0]

            if score_column is None:
                available_cols = ", ".join(self.df.columns[:10])  # Show first 10 columns
                if len(self.df.columns) > 10:
                    available_cols += "..."
                QMessageBox.critical(
                    self, "Column Error", 
                    f"Could not find a suitable RMD score column in the CSV file.\n\n"
                    f"Available columns: {available_cols}\n\n"
                    f"Please ensure your file contains a numeric column with scores."
                )
                return

            # Extract and validate score values
            try:
                self.data = pd.to_numeric(self.df[score_column], errors='coerce').values
                self.score_column = score_column
            except Exception as e:
                QMessageBox.critical(self, "Data Error", f"Error converting score column to numeric: {str(e)}")
                return

            # Check for NaN values
            nan_count = np.isnan(self.data).sum()
            if nan_count > 0:
                if nan_count == len(self.data):
                    QMessageBox.critical(self, "Data Error", f"Column '{score_column}' contains no valid numeric values.")
                    return
                else:
                    # Remove NaN values
                    valid_indices = ~np.isnan(self.data)
                    self.df = self.df[valid_indices]
                    self.data = self.data[valid_indices]
                    
                    QMessageBox.warning(
                        self, "Data Warning", 
                        f"Removed {nan_count} rows with invalid values. "
                        f"Proceeding with {len(self.data)} valid compounds."
                    )

            # Validate we have enough data
            if len(self.data) < 2:
                QMessageBox.critical(self, "Data Error", "Need at least 2 data points for analysis.")
                return

            # Sort by score (ascending order for proper indexing)
            self.df = self.df.sort_values(by=score_column)
            self.data = self.df[score_column].values

            # Set initial threshold (70% point to select top 30% on right side)
            min_val = float(np.min(self.data))
            max_val = float(np.max(self.data))
            
            # Handle edge case where all values are the same
            if min_val == max_val:
                QMessageBox.warning(
                    self, "Data Warning", 
                    "All RMD scores are identical. Limited analysis will be available."
                )
                initial_threshold = min_val
            else:
                initial_threshold = min_val + (max_val - min_val) * 0.7  # 70% threshold to select top 30%

            # Set up statistics panel with data
            self.stats_panel.set_data(self.data)
            self.stats_panel.threshold_input.setRange(min_val - 1, max_val + 1)
            self.stats_panel.threshold_input.setValue(initial_threshold)

            # Plot distribution with threshold line enabled by default
            self.canvas.plot_distribution(self.data, initial_threshold)

            # Update statistics
            self.update_all_statistics(initial_threshold)

            # Enable controls
            self.enable_controls()

            # Update file label with more info
            file_info = f"Loaded: {os.path.basename(file_path)} ({len(self.df)} compounds, column: '{score_column}')"
            self.file_label.setText(file_info)
            self.file_label.setToolTip(f"Full path: {file_path}\nScore column: {score_column}\nData range: {min_val:.3f} to {max_val:.3f}")

            # Update status with success message
            self.statusBar.showMessage(
                f"Successfully loaded {len(self.df)} compounds from {os.path.basename(file_path)} "
                f"(Score range: {min_val:.3f} to {max_val:.3f}) - Drag the threshold line to select compounds with real-time highlighting"
            )

        except Exception as e:
            error_msg = f"Unexpected error loading data: {str(e)}"
            QMessageBox.critical(self, "Error", error_msg)
            self.statusBar.showMessage("Error loading data")
            print(f"Debug - Load data error: {e}")  # For debugging

    def on_threshold_input_changed(self, threshold):
        """Handle threshold input change from statistics panel"""
        if self.data is None:
            return
        
        self.update_all_statistics(threshold)
        self.canvas.update_plot(threshold)

    def on_graph_threshold_moved(self, threshold):
        """Handle threshold moved from graph"""
        self.stats_panel.update_threshold_input(threshold)
        self.update_all_statistics(threshold)

    def update_all_statistics(self, threshold):
        """Update all statistics displays"""
        if self.data is None:
            return

        # Update statistics panels
        self.stats_panel.update_overall_stats(self.data)
        self.stats_panel.update_selected_stats(self.data, len(self.data), threshold)
        self.stats_panel.update_less_stats(self.data, threshold)

    def export_selected_compounds(self):
        """Export selected compounds based on current threshold (RIGHT side)"""
        if self.df is None or self.data is None:
            QMessageBox.warning(self, "No Data", "Please load data first.")
            return

        try:
            # Get current threshold
            threshold = self.stats_panel.get_current_threshold_score()
            threshold_type = self.stats_panel.threshold_type_combo.currentText()
            threshold_value = self.stats_panel.threshold_input.value()
            
            # Select compounds based on threshold (RIGHT side - greater than threshold)
            selected_indices = self.df[self.score_column] > threshold
            selected_df = self.df.loc[selected_indices].copy()

            if len(selected_df) == 0:
                QMessageBox.warning(self, "No Data", "No compounds match the current threshold.")
                return

            # Generate description and filename
            if threshold_type == "RMD Score":
                description = f"RMD_Score_gt_{threshold_value:.3f}"
                group_description = f"RMD Score > {threshold_value:.3f} ({len(selected_df)} compounds)"
            elif threshold_type == "Compound Count":
                description = f"Highest_{int(threshold_value)}_Compounds"
                group_description = f"Highest {int(threshold_value)} compounds"
            else:  # Percentage
                description = f"Highest_{threshold_value:.1f}pct_Compounds"
                group_description = f"Highest {threshold_value:.1f}% compounds"

            # Generate filename
            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            file_name = f"{base_name}_{description}_{timestamp}.csv"

            # Get save file path
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Selected Compounds as CSV", file_name, "CSV Files (*.csv);;All Files (*)"
            )

            if not file_path:
                return

            # Save to CSV
            selected_df.to_csv(file_path, index=False)

            self.statusBar.showMessage(
                f"Exported {len(selected_df)} compounds to {os.path.basename(file_path)}"
            )

            QMessageBox.information(
                self, "Export Successful", 
                f"Successfully exported {group_description} to {os.path.basename(file_path)}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export compounds: {str(e)}")

    def save_plot(self):
        """Save the current plot as an image"""
        if self.canvas is None:
            return

        # Get save file name
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "", "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf);;All Files (*)"
        )

        if file_name:
            try:
                self.canvas.fig.savefig(file_name, dpi=300, bbox_inches='tight')
                self.statusBar.showMessage(f"Plot saved to {file_name}")
                QMessageBox.information(self, "Save Successful", f"Plot saved to {file_name}")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save plot: {str(e)}")

    def closeEvent(self, event):
        """Handle window close event"""
        if self.modal_mode and self.status_file:
            try:
                with open(self.status_file, 'w') as f:
                    f.write("completed")
            except:
                pass
        event.accept()


def main():
    """Main function to run the application"""
    parser = argparse.ArgumentParser(description='Streamlined RMD Score Analyzer - Real-time Highlighting Fixed')
    parser.add_argument('--input', type=str, help='Input CSV file path')
    parser.add_argument('--output', type=str, help='Output file path (for modal mode)')
    parser.add_argument('--status', type=str, help='Status file path (for modal mode)')
    parser.add_argument('--modal', action='store_true', help='Run in modal mode')
    
    args = parser.parse_args()

    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Streamlined RMD Score Analyzer")
    app.setApplicationVersion("5.1")
    app.setOrganizationName("Research Lab")

    # Create and show the main window
    window = StreamlinedCompoundAnalyzer(
        input_file=args.input,
        output_file=args.output,
        status_file=args.status,
        modal_mode=args.modal
    )
    
    window.show()
    
    # Run the application
    sys.exit(app.exec_())


# Original main function from rmd_analysis.py (commented out for integration)
# if __name__ == "__main__":
#     main()


# ============================================================================
# MINIMAL TAB-BASED WRAPPER (PRESERVES ORIGINAL FUNCTIONALITY)
# ============================================================================

# Additional import needed for the tab wrapper
from PyQt5.QtWidgets import QTabWidget

class UnifiedTabApplication(QMainWindow):
    """Minimal tab-based wrapper that preserves original GUI layouts exactly"""
    
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        """Initialize the tab-based interface with original GUIs"""
        # Set window properties
        self.setWindowTitle("PyRMD Screening and Analysis")
        self.setGeometry(100, 100, 450, 180)
        self.setMinimumSize(800, 1000)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Initialize tabs with ORIGINAL classes
        self.init_screening_tab()
        self.init_result_analysis_tab()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready - Select a tab to begin")
        
        # Apply minimal styling
        self.apply_tab_styling()
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
    
    def init_screening_tab(self):
        """Initialize the Screening tab using the ORIGINAL Ui_Screening class"""
        # Create a QMainWindow container for the original screening interface
        screening_window = QMainWindow()
        
        # Use the ORIGINAL Ui_Screening class exactly as it was
        self.screening_ui = Ui_Screening()
        self.screening_ui.setupUi(screening_window)
        
        # Add the screening window's central widget to the tab
        self.tab_widget.addTab(screening_window.centralWidget(), "Screening")
    
    def init_result_analysis_tab(self):
        """Initialize the Result Analysis tab using the ORIGINAL StreamlinedCompoundAnalyzer class"""
        # Create the ORIGINAL StreamlinedCompoundAnalyzer instance
        self.analysis_widget = StreamlinedCompoundAnalyzer()
        
        # Extract the central widget from the original analyzer
        analysis_central_widget = self.analysis_widget.centralWidget()
        
        # Add to tab widget
        self.tab_widget.addTab(analysis_central_widget, "Result Analysis")
    
    def on_tab_changed(self, index):
        """Handle tab change events"""
        if index == 0:
            self.statusBar.showMessage("Screening interface active")
        elif index == 1:
            self.statusBar.showMessage("Result Analysis interface active - Please upload a CSV file to analyze")
    
    def apply_tab_styling(self):
        """Apply minimal styling to tabs only (preserves original GUI styling)"""
        style = """
            QTabWidget::pane {
                border: 2px solid #3498db;
                background-color: white;
                border-radius: 5px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #ecf0f1;
                border: 2px solid #bdc3c7;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
                min-width: 120px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom-color: white;
                color: #3498db;
            }
            QTabBar::tab:hover {
                background-color: #d5dbdb;
            }
            QStatusBar {
                background-color: #34495e;
                color: white;
                font-weight: bold;
                padding: 5px;
            }
        """
        self.setStyleSheet(style)

    def apply_benchmark_model_parameters(self, model_parameters):
        self.tab_widget.setCurrentIndex(0)
        if hasattr(self, "screening_ui") and hasattr(self.screening_ui, "apply_benchmark_model_parameters"):
            self.screening_ui.apply_benchmark_model_parameters(model_parameters)
            self.statusBar.showMessage("Screening loaded with selected benchmark model parameters")


def main_unified():
    """Main function for the unified application"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("RMD Screening and Analysis")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("Cosconati Lab")
    
    # Create and show the unified window
    window = UnifiedTabApplication()
    window.show()
    
    # Run the application
    sys.exit(app.exec_())


if __name__ == "__main__":
    # Use the unified main function instead of the original ones
    main_unified()

