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
# ============================================================================
# COMPLETE ORIGINAL BENCHMARKING DIALOG CODE FOR PyRMD v2.0 (PyRMD_Studio_Engine)
# ============================================================================
import subprocess
import multiprocessing
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QCheckBox, QButtonGroup, QRadioButton, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QLineEdit, QWidget, QComboBox, QSpinBox, QTableWidget, QTableWidgetItem, QScrollArea, QSplitter
import configparser
import os
import time
from compound_analyzer_modal import CompoundAnalyzer
class BenchmarkWorker(QtCore.QThread):
    finished = QtCore.pyqtSignal(bool, str)  # success flag, message

    def __init__(self, cores):
        super().__init__()
        self.cores = cores

    def run(self):
        try:
            env = os.environ.copy()
            env['OMP_NUM_THREADS'] = str(self.cores)
            env['NUMBA_NUM_THREADS'] = str(self.cores)

            result = subprocess.run(
                ['./launch.sh'],
                capture_output=True,
                text=True,
                cwd=os.getcwd(),
                env=env
            )

            if result.returncode == 0:
                self.finished.emit(True, "Benchmark completed successfully!")
            else:
                self.finished.emit(False, f"Benchmark failed:\n{result.stderr}")
        except Exception as e:
            self.finished.emit(False, f"Error running benchmark: {str(e)}")


# ===== NEW INTEGRATION DIALOG CLASSES =====

class PreparationQueryDialog(QDialog):
    """Dialog to ask if the file is already prepared for pyrmd2dock"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("File Preparation Check")
        self.setFixedSize(450, 200)
        self.setModal(True)
        
        # Set up layout
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Question label
        question_label = QLabel("Is this file already prepared for pyrmd2dock?")
        question_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #2c3e50;")
        question_label.setWordWrap(True)
        layout.addWidget(question_label)
        
        # Description label
        desc_label = QLabel("If your docking score file has already been processed through the dock preparation pipeline, select 'Yes'. Otherwise, select 'No (Run Dock Prep)' to prepare the file.")
        desc_label.setStyleSheet("font-size: 11px; color: #34495e;")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        # Yes button
        self.yes_button = QPushButton("Yes")
        self.yes_button.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        self.yes_button.clicked.connect(self.accept)
        
        # No button
        self.no_button = QPushButton("No (Run Dock Prep)")
        self.no_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.no_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.yes_button)
        button_layout.addWidget(self.no_button)
        layout.addLayout(button_layout)
        
        # Store the result
        self.is_prepared = False
    
    def accept(self):
        self.is_prepared = True
        super().accept()
    
    def reject(self):
        self.is_prepared = False
        super().reject()

# ===== END NEW INTEGRATION DIALOG CLASSES =====

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


class BenchmarkResultsDialog(QDialog):
    def __init__(self, file_path, selected_module="PyRMD2Dock", screening_launcher=None, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.selected_module = selected_module
        self.screening_launcher = screening_launcher
        self.setWindowTitle("Benchmark Results")
        self.resize(1200, 700)

        layout = QVBoxLayout(self)

        self.info_label = QLabel(f"Results file: {file_path}")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(self.info_label)

        self.table = QTableWidget()
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_layout.addWidget(close_button)
        layout.addLayout(close_layout)

        self._load_results_file()

    def _extract_row_parameters(self, row_index):
        header_to_column = {}
        for column_index in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(column_index)
            if header_item is not None:
                header_text = header_item.text().strip().lower()
                if header_text:
                    header_to_column[header_text] = column_index

        parameters = {}
        for header_text, column_index in header_to_column.items():
            if column_index <= 1:
                continue
            item = self.table.item(row_index, column_index)
            parameters[header_text] = "" if item is None else item.text().strip()

        return parameters

    def _open_screening_for_button(self):
        button = self.sender()
        if button is None:
            return

        cell_point = button.mapTo(self.table.viewport(), QtCore.QPoint(1, 1))
        row_index = self.table.indexAt(cell_point).row()
        if row_index < 0:
            return

        model_params = self._extract_row_parameters(row_index)
        if not model_params:
            QMessageBox.warning(self, "Model Selection", "Failed to read selected model parameters.")
            return

        if not callable(self.screening_launcher):
            QMessageBox.warning(self, "Run Screening", "Screening launcher is not available.")
            return

        launcher = self.screening_launcher
        self.accept()
        QtCore.QTimer.singleShot(0, lambda params=model_params, launch=launcher: launch(params))

    def _open_plots_for_button(self):
        button = self.sender()
        if button is None:
            return

        cell_point = button.mapTo(self.table.viewport(), QtCore.QPoint(1, 1))
        row_index = self.table.indexAt(cell_point).row()
        if row_index < 0:
            return

        plot_paths = self._find_plot_files_for_row(row_index)
        model_label = f"Model {row_index + 1}"
        dialog = PlotViewerDialog(plot_paths, model_label=model_label, parent=self)
        dialog.exec_()

    def _find_plot_files_for_row(self, row_index):
        base_dir = os.path.dirname(os.path.abspath(self.file_path))

        header_to_column = {}
        for column_index in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(column_index)
            if header_item is not None:
                header_to_column[header_item.text().strip().lower()] = column_index

        csv_plot_paths = []
        for key in ["roc_curve_file", "prc_curve_file", "roc_plot_file", "prc_plot_file"]:
            if key in header_to_column:
                table_column = header_to_column[key]
                if table_column > 1:
                    item = self.table.item(row_index, table_column)
                    if item is not None:
                        raw_path = item.text().strip()
                        if raw_path:
                            candidate = raw_path
                            if not os.path.isabs(candidate):
                                candidate = os.path.join(base_dir, candidate)
                            if os.path.exists(candidate):
                                csv_plot_paths.append(os.path.abspath(candidate))

        if csv_plot_paths:
            unique_paths = []
            for path in csv_plot_paths:
                if path not in unique_paths:
                    unique_paths.append(path)
            return unique_paths

        candidate_names = [
            "ROC_curve.png",
            "PRC_curve.png",
            f"ROC_curve_{row_index + 1}.png",
            f"PRC_curve_{row_index + 1}.png",
        ]

        existing_paths = []
        for candidate_name in candidate_names:
            path_in_results_dir = os.path.join(base_dir, candidate_name)
            if os.path.exists(path_in_results_dir) and path_in_results_dir not in existing_paths:
                existing_paths.append(path_in_results_dir)

        return existing_paths

    def _read_results_file(self):
        separators = [",", ";", "\t", "|"]
        best_data_frame = None
        best_column_count = 0

        for separator in separators:
            try:
                data_frame = pd.read_csv(self.file_path, sep=separator, engine='python')
                if not data_frame.empty and len(data_frame.columns) > best_column_count:
                    best_data_frame = data_frame
                    best_column_count = len(data_frame.columns)
            except Exception:
                continue

        if best_data_frame is None:
            best_data_frame = pd.read_csv(self.file_path, sep=None, engine='python')

        return best_data_frame

    def _load_results_file(self):
        try:
            data_frame = self._read_results_file()

            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(data_frame.index))
            self.table.setColumnCount(len(data_frame.columns) + 2)
            self.table.setHorizontalHeaderLabels(["Watch Plots", "Run Screening"] + [str(column) for column in data_frame.columns])

            for row_index, (_, row_values) in enumerate(data_frame.iterrows()):
                watch_button = QPushButton("Watch Plots")
                watch_button.clicked.connect(self._open_plots_for_button)
                self.table.setCellWidget(row_index, 0, watch_button)

                screening_button = QPushButton("Run Screening")
                screening_button.clicked.connect(self._open_screening_for_button)
                self.table.setCellWidget(row_index, 1, screening_button)

                for column_index, value in enumerate(row_values):
                    display_value = "" if pd.isna(value) else str(value)
                    self.table.setItem(row_index, column_index + 2, QTableWidgetItem(display_value))

            self.table.resizeColumnsToContents()
            self.table.setSortingEnabled(True)
            self.info_label.setText(
                f"Results file: {self.file_path}\nModels: {len(data_frame.index)} | Columns: {len(data_frame.columns)} | Click any column header to sort"
            )
        except Exception as error:
            self.info_label.setText(f"Failed to load results file: {error}")
            self.table.setRowCount(0)
            self.table.setColumnCount(0)


class ResizableImageLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = None
        self.setAlignment(QtCore.Qt.AlignCenter)

    def set_original_pixmap(self, pixmap):
        self._original_pixmap = pixmap
        self._apply_scaled_pixmap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_scaled_pixmap()

    def _apply_scaled_pixmap(self):
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        scaled = self._original_pixmap.scaled(
            max(1, self.width()),
            max(1, self.height()),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        self.setPixmap(scaled)


class PlotViewerDialog(QDialog):
    def __init__(self, plot_paths, model_label="Model", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Plots - {model_label}")
        self.resize(1100, 800)

        layout = QVBoxLayout(self)

        if not plot_paths:
            no_plots_label = QLabel(
                "No plot files found for this row.\nExpected files: ROC_curve.png and PRC_curve.png"
            )
            no_plots_label.setWordWrap(True)
            no_plots_label.setStyleSheet("font-size: 12px; color: #6c757d;")
            layout.addWidget(no_plots_label)
        else:
            splitter = QSplitter(QtCore.Qt.Horizontal)
            splitter.setChildrenCollapsible(False)

            for plot_path in plot_paths[:2]:
                panel = QWidget()
                panel_layout = QVBoxLayout(panel)

                name_label = QLabel(os.path.basename(plot_path))
                name_label.setStyleSheet("font-size: 12px; font-weight: 600;")
                panel_layout.addWidget(name_label)

                image_scroll = QScrollArea()
                image_scroll.setWidgetResizable(True)
                image_label = ResizableImageLabel()
                image_label.setMinimumSize(300, 300)

                image_pixmap = QtGui.QPixmap(plot_path)
                if image_pixmap.isNull():
                    image_label.setText(f"Failed to open image: {plot_path}")
                    image_label.setStyleSheet("color: #dc3545;")
                else:
                    image_label.set_original_pixmap(image_pixmap)

                image_scroll.setWidget(image_label)
                panel_layout.addWidget(image_scroll)
                splitter.addWidget(panel)

            if len(plot_paths) == 1:
                empty_panel = QWidget()
                empty_layout = QVBoxLayout(empty_panel)
                placeholder = QLabel("No second plot available")
                placeholder.setAlignment(QtCore.Qt.AlignCenter)
                placeholder.setStyleSheet("font-size: 12px; color: #6c757d;")
                empty_layout.addWidget(placeholder)
                splitter.addWidget(empty_panel)

            splitter.setStretchFactor(0, 1)
            splitter.setStretchFactor(1, 1)
            layout.addWidget(splitter)

        close_layout = QHBoxLayout()
        close_layout.addStretch()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        close_layout.addWidget(close_button)
        layout.addLayout(close_layout)

class Ui_Benchmark(object):
    def setupUi(self, Benchmark, selected_module="PyRMD2Dock"):
        Benchmark.setObjectName("Benchmark")
        self.selected_module = selected_module
        Benchmark.setWindowTitle(f"Benchmarking - {self.selected_module}")
        self.default_values = {
            'butina_cutoff': '0.7'
        }
        # Initialize file paths and epsilon values
        self.file_path_smi_file = ""
        self.file_path_chembl = ""
        self.decoys_file_path = ""
        self.actives_file_path = ""
        self.inactives_file_path = ""
        self.benchmark_output_directory = ""
        self.active_epsilon_values = []
        self.inactive_epsilon_values = []
        self._screening_windows = []
        self._benchmark_expected_new_rows = 0
        self._benchmark_baseline_rows = 0
        self._benchmark_target_rows = 0
        self._benchmark_results_file_path = ""
        self._benchmark_completion_message = ""
        self._benchmark_previous_size = -1
        self._benchmark_stable_hits = 0
        self._benchmark_finalize_start_time = 0
        self._benchmark_finalize_timeout_seconds = 1800
        self._benchmark_finalize_timer = QtCore.QTimer(Benchmark)
        self._benchmark_finalize_timer.setInterval(1000)
        self._benchmark_finalize_timer.timeout.connect(self._poll_benchmark_results_completion)
        
        Benchmark.resize(800, 1000)
        
        # Set up central widget
        self.centralwidget = QtWidgets.QWidget(Benchmark)
        self.centralwidget.setObjectName("centralwidget")
        Benchmark.setCentralWidget(self.centralwidget)
        
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
        self.lineEdit_program_mode.setText("Structure-Based Virtual Screening (SBVS), Benchmarking")
        self.lineEdit_program_mode.setReadOnly(True)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_program_mode)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_program_mode)
        current_row += 1
        self.all_parameter_widgets.append((self.label_program_mode, "always"))
        self.all_parameter_widgets.append((self.lineEdit_program_mode, "always"))
        
        # Output Directory
        self.label_output_dir = QtWidgets.QLabel("Output Directory:")
        self.label_output_dir.setToolTip("Select the directory where results will be saved.")
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
        self.lineEdit_output_file.setText("benchmark_results.csv")
        self.lineEdit_output_file.setToolTip("Enter the name of the output file where results will be saved.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_output_file)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_output_file)
        current_row += 1
        self.all_parameter_widgets.append((self.label_output_file, "beginner"))
        self.all_parameter_widgets.append((self.lineEdit_output_file, "beginner"))
        
        # TRAINING DATASETS Section
        self.label_training_header = QtWidgets.QLabel("TRAINING DATASETS")
        self.label_training_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_training_header)
        current_row += 1
        self.all_parameter_widgets.append((self.label_training_header, "always"))
        
        self.checkBox_use_chembl = QCheckBox("Use Single Docking Score File")
        self.checkBox_use_chembl.setChecked(True)
        self.checkBox_use_chembl.setToolTip("Check this box to use the single dataset for training.")
        self.checkBox_use_chembl.stateChanged.connect(self._toggle_training_uploads)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_use_chembl)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_use_chembl, "beginner"))
        
        # ChEMBL File
        self.label_chembl_file = QtWidgets.QLabel("Docking Score File:")
        chembl_layout = QHBoxLayout()
        self.lineEdit_chembl_file = QLineEdit()
        self.pushButton_chembl_file = QPushButton("Browse")
        self.pushButton_chembl_file.clicked.connect(lambda: self.browse_file("file_path_chembl", self.lineEdit_chembl_file, "Select Docking Score File"))
        # Add Analyze button
        self.pushButton_analyze_chembl = QPushButton("Analyze")
        self.pushButton_analyze_chembl.setToolTip("Click to analyze the selected ΔG binding scoring file.")
        self.pushButton_analyze_chembl.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-weight: bold;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        self.pushButton_analyze_chembl.clicked.connect(self.open_compound_analyzer)
        chembl_layout.addWidget(self.lineEdit_chembl_file)
        chembl_layout.addWidget(self.pushButton_chembl_file)
        chembl_layout.addWidget(self.pushButton_analyze_chembl)
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
        
        # Fingerprint Type Selection
        self.label_fingerprint_type = QtWidgets.QLabel("Fingerprint Type:")
        fingerprint_layout = QHBoxLayout()
        
        self.radio_fp_fast = QRadioButton("Fast")
        self.radio_fp_fast.setToolTip("Select this for a quick fingerprint generation with lower accuracy (1024 bits).")
        self.radio_fp_balanced = QRadioButton("Balanced")
        self.radio_fp_balanced.setToolTip("Select this for a balanced approach with moderate accuracy (2048 bits).")
        self.radio_fp_accurate = QRadioButton("Accurate")
        self.radio_fp_accurate.setToolTip("Select this for the most accurate fingerprint generation (4096 bits).")
        self.radio_fp_balanced.setChecked(True)  # Default
        
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
        
        self.label_decoys_file = QtWidgets.QLabel("Decoys File (Optional):")
        decoys_layout = QHBoxLayout()
        self.lineEdit_decoys_file = QLineEdit()
        self.lineEdit_decoys_file.setToolTip("Select a file containing decoy compounds.")
        self.pushButton_decoys_file = QPushButton("Browse")
        self.pushButton_decoys_file.setToolTip("Click to browse and select a decoys file.")
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
        
        self.label_bu = QtWidgets.QLabel("Threshold:")
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
        self.lineEdit_n_splits.setToolTip("Enter the number of splits for k-fold cross-validation.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_n_splits)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_n_splits)
        current_row += 1
        self.all_parameter_widgets.append((self.label_n_splits, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_n_splits, "expert"))
        
        self.label_n_repeats = QtWidgets.QLabel("N Repeats:")
        self.lineEdit_n_repeats = QLineEdit()
        self.lineEdit_n_repeats.setText("3")
        self.lineEdit_n_repeats.setToolTip("Enter the number of repeats for k-fold cross-validation.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_n_repeats)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_n_repeats)
        current_row += 1
        self.all_parameter_widgets.append((self.label_n_repeats, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_n_repeats, "expert"))
        
        # # CHEMBL THRESHOLDS Section (Expert Mode)
        # self.label_chembl_thresholds_header = QtWidgets.QLabel("CHEMBL THRESHOLDS")
        # self.label_chembl_thresholds_header.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50; margin-top: 10px;")
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_chembl_thresholds_header)
        # current_row += 1
        # self.all_parameter_widgets.append((self.label_chembl_thresholds_header, "beginner"))
        
        # self.label_activity_threshold = QtWidgets.QLabel("Activity Threshold (nM):")
        # self.lineEdit_activity_threshold = QLineEdit()
        # self.lineEdit_activity_threshold.setText(self.default_values['activity_threshold'])
        # self.lineEdit_activity_threshold.setToolTip("Enter the activity threshold for ChEMBL compounds.")
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_activity_threshold)
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_activity_threshold)
        # current_row += 1
        # self.all_parameter_widgets.append((self.label_activity_threshold, "beginner"))
        # self.all_parameter_widgets.append((self.lineEdit_activity_threshold, "beginner"))
        # # After self.lineEdit_activity_threshold
        # self.label_actives_count = QLabel("Actives below threshold: 0")
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_actives_count)
        # current_row += 1
        
        # self.label_inactivity_threshold = QtWidgets.QLabel("Inactivity Threshold (nM):")
        # self.lineEdit_inactivity_threshold = QLineEdit()
        # self.lineEdit_inactivity_threshold.setText(self.default_values['inactivity_threshold'])
        # self.lineEdit_inactivity_threshold.setToolTip("Enter the inactivity threshold for ChEMBL compounds.")
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_inactivity_threshold)
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_inactivity_threshold)
        # current_row += 1
        # self.all_parameter_widgets.append((self.label_inactivity_threshold, "beginner"))
        # self.all_parameter_widgets.append((self.lineEdit_inactivity_threshold, "beginner"))
        # # After self.lineEdit_inactivity_threshold
        # self.label_inactives_count = QLabel("Inactives above threshold: 0")
        # self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.label_inactives_count)
        # current_row += 1
        
        # self.lineEdit_chembl_file.textChanged.connect(self._update_actives_inactives_count)
        # self.lineEdit_activity_threshold.textChanged.connect(self._update_actives_inactives_count)
        # self.lineEdit_inactivity_threshold.textChanged.connect(self._update_actives_inactives_count)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        self.pushButton_update_config = QPushButton("Update Configuration")
        self.pushButton_update_config = QPushButton("Update Configuration")
        self.pushButton_update_config.setToolTip("Update the configuration file with the current settings.")
        self.pushButton_update_config.clicked.connect(self.update_ini_file)
        button_layout.addWidget(self.pushButton_update_config)
        
        self.pushButton_run_benchmark = QPushButton("Run Benchmark")
        self.pushButton_run_benchmark.setToolTip("Run the benchmark process with the current settings.")
        self.pushButton_run_benchmark.clicked.connect(self.run_benchmark_process)
        button_layout.addWidget(self.pushButton_run_benchmark)

        self.pushButton_view_results = QPushButton("Open Results CSV")
        self.pushButton_view_results.setToolTip("Open an existing benchmark results CSV and inspect/sort models.")
        self.pushButton_view_results.clicked.connect(self.open_precalculated_results_file)
        button_layout.addWidget(self.pushButton_view_results)
        
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
        self.statusbar = QtWidgets.QStatusBar(Benchmark)
        Benchmark.setStatusBar(self.statusbar)
        
        # Connect signals
        self.radio_fp_fast.toggled.connect(self._update_fingerprint_settings)
        self.radio_fp_balanced.toggled.connect(self._update_fingerprint_settings)
        self.radio_fp_accurate.toggled.connect(self._update_fingerprint_settings)
        
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
        
        self.retranslateUi(Benchmark)
        QtCore.QMetaObject.connectSlotsByName(Benchmark)

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

    def _sanitize_file_path_text(self, path_text):
        if path_text is None:
            return ""

        cleaned = str(path_text).strip()
        if cleaned.lower().endswith("(prepared)"):
            cleaned = cleaned[: -len("(prepared)")].strip()

        return cleaned

    def browse_file(self, file_path_attr, line_edit, dialog_title):
        """Browse for a file and update the corresponding line edit with integrated preparation workflow"""
        
        # Check if this is the ChEMBL file (docking score file) to trigger preparation workflow
        if file_path_attr == "file_path_chembl":
            # Show preparation query dialog BEFORE file selection
            prep_dialog = PreparationQueryDialog(self.centralwidget)
            result = prep_dialog.exec_()
            
            if result == QDialog.Accepted and prep_dialog.is_prepared:
                # User selected "Yes" - file is already prepared, proceed with normal file selection
                file_path, _ = QFileDialog.getOpenFileName(self.centralwidget, dialog_title, "", "All Files (*)")
                if file_path:
                    setattr(self, file_path_attr, file_path)
                    line_edit.setText(file_path)
                    QMessageBox.information(self.centralwidget, "File Ready", 
                                          "File is ready for analysis. You can now proceed with the benchmarking process.")
            elif result == QDialog.Rejected:
                # User selected "No (Run Dock Prep)" - launch actual dock_prep interface
                self.launch_dock_prep_interface(file_path_attr, line_edit)
            # If dialog was cancelled (neither accepted nor rejected), do nothing
        else:
            # For non-ChEMBL files, use original behavior
            file_path, _ = QFileDialog.getOpenFileName(self.centralwidget, dialog_title, "", "All Files (*)")
            if file_path:
                setattr(self, file_path_attr, file_path)
                line_edit.setText(file_path)
    
    def launch_dock_prep_interface(self, file_path_attr, line_edit):
        """Launch the actual dock_prep interface and handle the result"""
        try:
            # Import the dock_prep GUI class
            from dock_prep import FinalPerfectCSVMergerGUI
            
            # Create and show the dock_prep interface
            self.dock_prep_window = FinalPerfectCSVMergerGUI()
            
            # Connect to the dock_prep window's close event to check for saved files
            self.dock_prep_window.closeEvent = lambda event: self.on_dock_prep_closed(event, file_path_attr, line_edit)
            
            # Show the dock_prep interface
            self.dock_prep_window.show()
            
            QMessageBox.information(self.centralwidget, "Dock Prep Launched", 
                                  "The dock preparation interface has been opened. After you save your prepared file, it will automatically be loaded into the docking score file field.")
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", 
                               f"Failed to launch dock preparation interface: {str(e)}")
    
    def on_dock_prep_closed(self, event, file_path_attr, line_edit):
        """Handle dock_prep window closing and check for saved files"""
        try:
            # Check if dock_prep has an output file path set
            if hasattr(self.dock_prep_window, 'output_file_path') and self.dock_prep_window.output_file_path:
                output_file = self.dock_prep_window.output_file_path
                
                # Check if the file actually exists
                if os.path.exists(output_file):
                    # Auto-load the prepared file
                    setattr(self, file_path_attr, output_file)
                    line_edit.setText(output_file)
                    line_edit.setToolTip("Prepared file loaded")
                    
                    QMessageBox.information(self.centralwidget, "File Auto-Loaded", 
                                          f"The prepared file has been automatically loaded:\n{os.path.basename(output_file)}\n\nYou can now proceed with the benchmarking process.")
                else:
                    # File was specified but doesn't exist, ask user to select manually
                    reply = QMessageBox.question(self.centralwidget, "File Not Found", 
                                               "The prepared file was not found at the expected location. Would you like to browse for your prepared file?",
                                               QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        file_path, _ = QFileDialog.getOpenFileName(self.centralwidget, "Select Prepared File", "", "CSV Files (*.csv);;All Files (*)")
                        if file_path:
                            setattr(self, file_path_attr, file_path)
                            line_edit.setText(file_path)
                            line_edit.setToolTip("Prepared file loaded")
            else:
                # No output file was set, ask user if they want to select a file
                reply = QMessageBox.question(self.centralwidget, "Select Prepared File", 
                                           "Would you like to select your prepared file now?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    file_path, _ = QFileDialog.getOpenFileName(self.centralwidget, "Select Prepared File", "", "CSV Files (*.csv);;All Files (*)")
                    if file_path:
                        setattr(self, file_path_attr, file_path)
                        line_edit.setText(file_path)
                        line_edit.setToolTip("Prepared file loaded")
        except Exception as e:
            QMessageBox.warning(self.centralwidget, "Warning", 
                              f"Could not auto-load prepared file: {str(e)}")
        
        # Allow the window to close normally
        event.accept()

    def browse_output_directory(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(self.centralwidget, "Select Output Directory")
        if directory:
            self.benchmark_output_directory = directory
            self.lineEdit_output_dir.setText(directory)
    def load_chembl_data_file(self, file_path):
        try:
            if file_path and os.path.exists(file_path):
                # Set the ChEMBL file path
                self.file_path_chembl = file_path
                self.lineEdit_chembl_file.setText(file_path)
                
                # Enable ChEMBL dataset checkbox
                self.checkBox_use_chembl.setChecked(True)
                
                # <<< Add this line here
                self._update_actives_inactives_count()
                
                QMessageBox.information(
                    self.centralwidget,
                    "Success",
                    f"INPUT data file loaded successfully:\n{file_path}"
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
                f"Failed to load input data file:\n{str(e)}"
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
        """Update configuration file with current parameter values"""
        try:
            # Save epsilon values to text files first
            self._save_epsilon_values_to_files()
            
            # Create single config file
            self._create_single_config()
            
            # Don't show popup message as per requirements
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to update configuration: {str(e)}")

    def _save_epsilon_values_to_files(self):
        """Save current epsilon values to tc_actives.txt and tc_inactives.txt"""
        # Get current active epsilon values
        active_values = []
        if self.radio_active_single.isChecked():
            try:
                value = float(self.lineEdit_active_single.text())
                active_values = [value]
            except ValueError:
                active_values = [0.95]  # Default value
        elif hasattr(self, 'active_epsilon_values') and self.active_epsilon_values:
            active_values = self.active_epsilon_values
        else:
            active_values = [0.95]  # Default value
        
        # Get current inactive epsilon values
        inactive_values = []
        if self.radio_inactive_single.isChecked():
            try:
                value = float(self.lineEdit_inactive_single.text())
                inactive_values = [value]
            except ValueError:
                inactive_values = [0.95]  # Default value
        elif hasattr(self, 'inactive_epsilon_values') and self.inactive_epsilon_values:
            inactive_values = self.inactive_epsilon_values
        else:
            inactive_values = [0.95]  # Default value
        
        # Save active epsilon values to tc_actives.txt
        with open('tc_actives.txt', 'w') as f:
            for value in active_values:
                f.write(f"{value:.2f}\n")
        
        # Save inactive epsilon values to tc_inactives.txt
        with open('tc_inactives.txt', 'w') as f:
            for value in inactive_values:
                f.write(f"{value:.2f}\n")

    def _create_single_config(self):
        """Create a single configuration file"""
        config = configparser.ConfigParser()
        
        # Add all sections
        config.add_section('MODE')
        config.add_section('TRAINING_DATASETS')
        config.add_section('FINGERPRINTS')
        config.add_section('DECOYS')
        config.add_section('CHEMBL_THRESHOLDS')
        config.add_section('KFOLD_PARAMETERS')
        config.add_section('TRAINING_PARAMETERS')
        config.add_section('CLUSTERING')
        config.add_section('STAT_PARAMETERS')
        config.add_section('FILTER')
        
        # MODE section
        config.set('MODE', 'mode', 'benchmark')
        config.set('MODE', 'db_to_screen', '')
        config.set('MODE', 'screening_output', 'database_predictions.csv')
        config.set('MODE', 'sdf_results', 'False')
        
        # Update benchmark_file with output directory and filename
        output_dir = self.lineEdit_output_dir.text().strip()
        output_file = self.lineEdit_output_file.text().strip()
        if output_dir and output_file:
            benchmark_file_path = os.path.join(output_dir, output_file)
        elif output_file:
            benchmark_file_path = f"./{output_file}"
        else:
            benchmark_file_path = "./benchmark_results.csv"
        config.set('MODE', 'benchmark_file', benchmark_file_path)
        
        # TRAINING_DATASETS section
        use_chembl = self.checkBox_use_chembl.isChecked()
        chembl_file_path = self._sanitize_file_path_text(self.lineEdit_chembl_file.text())
        config.set('TRAINING_DATASETS', 'use_chembl', str(use_chembl))
        config.set('TRAINING_DATASETS', 'chembl_file', chembl_file_path)
        config.set('TRAINING_DATASETS', 'use_actives', str(not use_chembl))
        config.set('TRAINING_DATASETS', 'actives_file', self.lineEdit_actives_file.text().strip())
        config.set('TRAINING_DATASETS', 'use_inactives', str(not use_chembl))
        config.set('TRAINING_DATASETS', 'inactives_file', self.lineEdit_inactives_file.text().strip())
        
        # --- REPLACE THE EXISTING FINGERPRINTS SECTION WITH THIS ---
        
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
        decoys_file = self.lineEdit_decoys_file.text().strip()
        config.set('DECOYS', 'use_decoys', str(bool(decoys_file)))
        config.set('DECOYS', 'decoys_file', decoys_file)
        config.set('DECOYS', 'sample_number', '1000000')
        
        # # CHEMBL_THRESHOLDS section
        # config.set('CHEMBL_THRESHOLDS', 'activity_threshold', self.lineEdit_activity_threshold.text().strip() or '1001')
        # config.set('CHEMBL_THRESHOLDS', 'inactivity_threshold', self.lineEdit_inactivity_threshold.text().strip() or '39999')
        # config.set('CHEMBL_THRESHOLDS', 'inhibition_threshold', '11')
        
        # KFOLD_PARAMETERS section
        config.set('KFOLD_PARAMETERS', 'n_splits', self.lineEdit_n_splits.text().strip() or '5')
        config.set('KFOLD_PARAMETERS', 'n_repeats', self.lineEdit_n_repeats.text().strip() or '3')
        
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
        config.set('STAT_PARAMETERS', 'beta', self.lineEdit_beta.text().strip() or '1')
        config.set('STAT_PARAMETERS', 'alpha', self.lineEdit_alpha.text().strip() or '20')
        
        # FILTER section (keep original values from template)
        config.set('FILTER', 'filter_properties', 'False')
        config.set('FILTER', 'molwt_min', '200')
        config.set('FILTER', 'logp_min', '-5')
        config.set('FILTER', 'hdonors_min', '0')
        config.set('FILTER', 'haccept_min', '0')
        config.set('FILTER', 'rotabonds_min', '0')
        config.set('FILTER', 'heavat_min', '15')
        config.set('FILTER', 'molwt_max', '600')
        config.set('FILTER', 'logp_max', '5')
        config.set('FILTER', 'hdonors_max', '6')
        config.set('FILTER', 'haccept_max', '11')
        config.set('FILTER', 'rotabonds_max', '9')
        config.set('FILTER', 'heavat_max', '51')
        
        # Write config file
        with open('configuration_benchmark.ini', 'w') as configfile:
            config.write(configfile)
    
        #QMessageBox.information(self.centralwidget, "Success", "Configuration file updated successfully!")

    def _create_combination_configs(self):
        """Create multiple configuration files for epsilon combinations"""
        combinations = []
        for active_val in self.active_epsilon_values:
            for inactive_val in self.inactive_epsilon_values:
                combinations.append((active_val, inactive_val))
        
        for active_val, inactive_val in combinations:
            config = configparser.ConfigParser()
            
            # Add all sections
            config.add_section('MODE')
            config.add_section('TRAINING_DATASETS')
            config.add_section('FINGERPRINTS')
            config.add_section('DECOYS')
            config.add_section('CHEMBL_THRESHOLDS')
            config.add_section('KFOLD_PARAMETERS')
            config.add_section('TRAINING_PARAMETERS')
            config.add_section('CLUSTERING')
            config.add_section('STAT_PARAMETERS')
            config.add_section('FILTER')
            
            # MODE section
            config.set('MODE', 'mode', 'benchmark')
            config.set('MODE', 'db_to_screen', '')
            config.set('MODE', 'screening_output', os.path.join(self.lineEdit_output_dir.text(), 'database_predictions.csv'))
            config.set('MODE', 'sdf_results', 'False')
            config.set('MODE', 'benchmark_file', os.path.join(self.lineEdit_output_dir.text(), f'{active_val}_{inactive_val}.csv'))
            
            # TRAINING_DATASETS section
            config.set('TRAINING_DATASETS', 'use_chembl', str(self.checkBox_use_chembl.isChecked()))
            config.set('TRAINING_DATASETS', 'chembl_file', self._sanitize_file_path_text(self.lineEdit_chembl_file.text()))
            config.set('TRAINING_DATASETS', 'use_actives', str(not self.checkBox_use_chembl.isChecked()))
            config.set('TRAINING_DATASETS', 'actives_file', self.lineEdit_actives_file.text())
            config.set('TRAINING_DATASETS', 'use_inactives', str(not self.checkBox_use_chembl.isChecked()))
            config.set('TRAINING_DATASETS', 'inactives_file', self.lineEdit_inactives_file.text())
            
            # FINGERPRINTS section
            config.set('FINGERPRINTS', 'fp_type', self.comboBox_fp_type.currentText())
            config.set('FINGERPRINTS', 'nbits', self.lineEdit_fp_size.text())
            config.set('FINGERPRINTS', 'explicit_hydrogens', 'True')
            config.set('FINGERPRINTS', 'iterations', self.lineEdit_fp_radius.text())
            config.set('FINGERPRINTS', 'chirality', 'False')
            config.set('FINGERPRINTS', 'redundancy', 'True')
            config.set('FINGERPRINTS', 'features', 'False')
            
            # DECOYS section
            config.set('DECOYS', 'use_decoys', 'False')
            config.set('DECOYS', 'decoys_file', self.lineEdit_decoys_file.text())
            config.set('DECOYS', 'sample_number', '1000000')
            
            # # CHEMBL_THRESHOLDS section
            # config.set('CHEMBL_THRESHOLDS', 'activity_threshold', self.lineEdit_activity_threshold.text())
            # config.set('CHEMBL_THRESHOLDS', 'inactivity_threshold', self.lineEdit_inactivity_threshold.text())
            # config.set('CHEMBL_THRESHOLDS', 'inhibition_threshold', '11')
            
            # KFOLD_PARAMETERS section
            config.set('KFOLD_PARAMETERS', 'n_splits', self.lineEdit_n_splits.text())
            config.set('KFOLD_PARAMETERS', 'n_repeats', self.lineEdit_n_repeats.text())
            
            # TRAINING_PARAMETERS section (specific epsilon values)
            # Note: Epsilon cutoff values are saved to tc_actives.txt and tc_inactives.txt files
            # and should NOT be included in the configuration file as per requirements
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_actives', 'XXXX')
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_inactives', 'YYYY')
            
            # CLUSTERING section
            butina_cutoff_val = self.lineEdit_bu.text().strip()
            config.set('CLUSTERING', 'butina_cutoff', butina_cutoff_val)

            # STAT_PARAMETERS section
            config.set('STAT_PARAMETERS', 'beta', self.lineEdit_beta.text())
            config.set('STAT_PARAMETERS', 'alpha', self.lineEdit_alpha.text())
            
            # FILTER section (disabled as requested)
            config.set('FILTER', 'filter_properties', 'False')
            config.set('FILTER', 'molwt_min', '100')
            config.set('FILTER', 'logp_min', '-5')
            config.set('FILTER', 'hdonors_min', '0')
            config.set('FILTER', 'haccept_min', '0')
            config.set('FILTER', 'rotabonds_min', '0')
            config.set('FILTER', 'heavat_min', '15')
            config.set('FILTER', 'molwt_max', '500')
            config.set('FILTER', 'logp_max', '5')
            config.set('FILTER', 'hdonors_max', '6')
            config.set('FILTER', 'haccept_max', '11')
            config.set('FILTER', 'rotabonds_max', '9')
            config.set('FILTER', 'heavat_max', '51')
            
            # Write config file with combination name
            filename = f'configuration_benchmark_{active_val}_{inactive_val}.ini'
            with open(filename, 'w') as configfile:
                config.write(configfile)

    def run_benchmark_process(self):
        """Run the benchmark process with CPU core selection and popups"""
        try:
            self.update_ini_file()

            # Show CPU core selection dialog
            core_dialog = CPUCoreSelectionDialog(self.centralwidget)
            if core_dialog.exec_() != QDialog.Accepted:
                return  # User cancelled

            selected_cores = core_dialog.get_core_count()
            self.selected_cores = selected_cores

            self._benchmark_results_file_path = self._get_benchmark_results_path()
            self._benchmark_baseline_rows = self._get_results_row_count(self._benchmark_results_file_path)
            self._benchmark_expected_new_rows = self._get_expected_benchmark_combinations()
            self._benchmark_target_rows = self._benchmark_baseline_rows + self._benchmark_expected_new_rows
            self._benchmark_completion_message = ""
            self._benchmark_previous_size = -1
            self._benchmark_stable_hits = 0
            self._benchmark_finalize_start_time = 0

            if self._benchmark_finalize_timer.isActive():
                self._benchmark_finalize_timer.stop()

            # Disable the button and update text
            self.pushButton_run_benchmark.setEnabled(False)
            self.pushButton_run_benchmark.setText("Running...")

            # Start the benchmark worker thread
            self.benchmark_worker = BenchmarkWorker(selected_cores)
            self.benchmark_worker.finished.connect(self._on_benchmark_finished)
            self.benchmark_worker.start()

            # Popup: started
            QMessageBox.information(
                self.centralwidget,
                "Benchmark Started",
                f"Benchmark started using {selected_cores} CPU cores."
            )

        except Exception as e:
            self.pushButton_run_benchmark.setEnabled(True)
            self.pushButton_run_benchmark.setText("Run Benchmark")
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to start benchmark: {str(e)}")

    def _on_benchmark_finished(self, success, message):
        if success:
            target_rows = self._benchmark_target_rows
            if target_rows <= 0:
                expected_combinations = self._get_expected_benchmark_combinations()
                baseline_rows = self._get_results_row_count(self._get_benchmark_results_path())
                target_rows = baseline_rows + expected_combinations
                self._benchmark_baseline_rows = baseline_rows
                self._benchmark_target_rows = target_rows

            self._benchmark_completion_message = message
            self._benchmark_finalize_start_time = time.time()
            self._benchmark_previous_size = -1
            self._benchmark_stable_hits = 0

            self.pushButton_run_benchmark.setEnabled(False)
            self.pushButton_run_benchmark.setText("Finalizing...")
            self._benchmark_finalize_timer.start()
        else:
            self.pushButton_run_benchmark.setEnabled(True)
            self.pushButton_run_benchmark.setText("Run Benchmark")
            QMessageBox.critical(self.centralwidget, "Benchmark Failed", message)
            self._reset_benchmark_completion_state()

        if hasattr(self, 'benchmark_worker') and self.benchmark_worker:
            self.benchmark_worker.deleteLater()
            self.benchmark_worker = None

    def _get_benchmark_results_path(self):
        output_dir = self.lineEdit_output_dir.text().strip() or '.'
        output_file = self.lineEdit_output_file.text().strip() or 'benchmark_results.csv'
        return os.path.abspath(os.path.join(output_dir, output_file))

    def _count_non_empty_lines(self, file_path):
        try:
            if not os.path.exists(file_path):
                return 0
            count = 0
            with open(file_path, 'r') as handle:
                for line in handle:
                    if line.strip():
                        count += 1
            return count
        except Exception:
            return 0

    def _get_expected_benchmark_combinations(self):
        active_file_count = self._count_non_empty_lines('tc_actives.txt')
        inactive_file_count = self._count_non_empty_lines('tc_inactives.txt')

        if active_file_count > 0:
            active_count = active_file_count
        else:
            active_count = max(1, len(self.active_epsilon_values)) if self.active_epsilon_values else 1

        if inactive_file_count > 0:
            inactive_count = inactive_file_count
        else:
            inactive_count = max(1, len(self.inactive_epsilon_values)) if self.inactive_epsilon_values else 1

        return active_count * inactive_count

    def _read_results_dataframe(self, file_path):
        separators = [",", ";", "\t", "|"]
        best_data_frame = None
        best_column_count = 0

        for separator in separators:
            try:
                data_frame = pd.read_csv(file_path, sep=separator, engine='python')
                if len(data_frame.columns) > best_column_count:
                    best_data_frame = data_frame
                    best_column_count = len(data_frame.columns)
            except Exception:
                continue

        if best_data_frame is None:
            best_data_frame = pd.read_csv(file_path, sep=None, engine='python')

        return best_data_frame

    def _get_results_row_count(self, file_path):
        try:
            if not os.path.exists(file_path):
                return 0
            data_frame = self._read_results_dataframe(file_path)
            return len(data_frame.index)
        except Exception:
            return 0

    def _check_results_ready_once(self, target_rows):
        results_file_path = self._benchmark_results_file_path or self._get_benchmark_results_path()
        rows_found = 0

        if not os.path.exists(results_file_path):
            return False, results_file_path, rows_found

        try:
            current_size = os.path.getsize(results_file_path)
            if current_size <= 0:
                self._benchmark_stable_hits = 0
                self._benchmark_previous_size = current_size
                return False, results_file_path, rows_found

            data_frame = self._read_results_dataframe(results_file_path)
            rows_found = len(data_frame.index)

            if rows_found >= target_rows:
                if current_size == self._benchmark_previous_size:
                    self._benchmark_stable_hits += 1
                else:
                    self._benchmark_stable_hits = 0

                self._benchmark_previous_size = current_size

                if self._benchmark_stable_hits >= 1:
                    return True, results_file_path, rows_found
            else:
                self._benchmark_stable_hits = 0
                self._benchmark_previous_size = current_size
        except Exception:
            self._benchmark_stable_hits = 0

        return False, results_file_path, rows_found

    def _poll_benchmark_results_completion(self):
        target_rows = self._benchmark_target_rows
        if target_rows <= 0:
            target_rows = self._get_results_row_count(self._benchmark_results_file_path or self._get_benchmark_results_path())

        results_ready, results_file_path, rows_found = self._check_results_ready_once(target_rows)
        if results_ready:
            if self._benchmark_finalize_timer.isActive():
                self._benchmark_finalize_timer.stop()

            new_rows = max(0, rows_found - self._benchmark_baseline_rows)
            QMessageBox.information(
                self.centralwidget,
                "Benchmark Completed",
                f"{self._benchmark_completion_message}\n\nResults saved to:\n{results_file_path}\nNew rows added: {new_rows}"
            )
            self._show_benchmark_results_window(results_file_path)
            self.pushButton_run_benchmark.setEnabled(True)
            self.pushButton_run_benchmark.setText("Run Benchmark")
            self._reset_benchmark_completion_state()
            return

        if self._benchmark_finalize_start_time > 0:
            elapsed = time.time() - self._benchmark_finalize_start_time
            if elapsed >= self._benchmark_finalize_timeout_seconds:
                if self._benchmark_finalize_timer.isActive():
                    self._benchmark_finalize_timer.stop()
                self.pushButton_run_benchmark.setEnabled(True)
                self.pushButton_run_benchmark.setText("Run Benchmark")
                QMessageBox.warning(
                    self.centralwidget,
                    "Benchmark Still Finalizing",
                    "All result combinations are not ready yet.\n"
                    "Please wait and open with 'Open Results CSV'."
                )
                self._reset_benchmark_completion_state()

    def _reset_benchmark_completion_state(self):
        if self._benchmark_finalize_timer.isActive():
            self._benchmark_finalize_timer.stop()

        self._benchmark_expected_new_rows = 0
        self._benchmark_baseline_rows = 0
        self._benchmark_target_rows = 0
        self._benchmark_results_file_path = ""
        self._benchmark_completion_message = ""
        self._benchmark_previous_size = -1
        self._benchmark_stable_hits = 0
        self._benchmark_finalize_start_time = 0

    def _show_benchmark_results_window(self, results_file_path=None):
        if not results_file_path:
            results_file_path = self._get_benchmark_results_path()

        if not os.path.exists(results_file_path):
            QMessageBox.warning(
                self.centralwidget,
                "Results File Not Found",
                f"Benchmark finished, but results file was not found at:\n{results_file_path}"
            )
            return

        dialog = BenchmarkResultsDialog(
            results_file_path,
            selected_module=self.selected_module,
            screening_launcher=self._launch_screening_from_model_parameters,
            parent=self.centralwidget
        )
        dialog.exec_()

    def open_precalculated_results_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.centralwidget,
            "Open Benchmark Results File",
            self.lineEdit_output_dir.text().strip() or os.getcwd(),
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self._show_benchmark_results_window(file_path)

    def _launch_screening_from_model_parameters(self, model_params):
        try:
            from Screening_2 import UnifiedTabApplication as ScreeningModule

            screening_window = ScreeningModule()
            if hasattr(screening_window, "apply_benchmark_model_parameters"):
                screening_window.apply_benchmark_model_parameters(model_params)

            screening_window.show()
            screening_window.raise_()
            screening_window.activateWindow()

            self._screening_windows.append(screening_window)
            self._screening_windows = [w for w in self._screening_windows if w is not None and not w.isHidden()]
        except Exception as error:
            QMessageBox.critical(
                self.centralwidget,
                "Open Screening Failed",
                f"Could not open screening window:\n{error}"
            )


    def load_default_values(self):
        """Load default values into the form and update configuration file"""
        try:
            # Reset all GUI elements to default values
            
            # Output settings
            self.lineEdit_output_dir.setText("")
            self.lineEdit_output_file.setText("PyRMD2Dock_results.csv")
            
            # Training datasets
            self.checkBox_use_chembl.setChecked(True)
            self.lineEdit_chembl_file.setText("")
            self.lineEdit_actives_file.setText("")
            self.lineEdit_inactives_file.setText("")
            
            # Fingerprint settings
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
            
            # Epsilon cutoff values
            self.radio_active_single.setChecked(True)
            self.lineEdit_active_single.setText("0.95")
            self.lineEdit_active_min.setText("")
            self.lineEdit_active_max.setText("")
            self.lineEdit_active_step.setText("")
            self.lineEdit_active_manual.setText("")
            
            self.radio_inactive_single.setChecked(True)
            self.lineEdit_inactive_single.setText("0.95")
            self.lineEdit_inactive_min.setText("")
            self.lineEdit_inactive_max.setText("")
            self.lineEdit_inactive_step.setText("")
            self.lineEdit_inactive_manual.setText("")
            
            # Clear epsilon values arrays
            self.active_epsilon_values = []
            self.inactive_epsilon_values = []
            
            # KFOLD parameters
            self.lineEdit_n_splits.setText("5")
            self.lineEdit_n_repeats.setText("3")
            
            # # ChEMBL thresholds
            # self.lineEdit_activity_threshold.setText("1001")
            # self.lineEdit_inactivity_threshold.setText("39999")
            
            # Stat parameters
            self.lineEdit_beta.setText("1")
            self.lineEdit_alpha.setText("20")
            
            # Update fingerprint settings based on selection
            self._update_fingerprint_settings()
            
            # Update UI visibility
            self._update_parameter_visibility()
            self._toggle_training_uploads()
            self._toggle_active_epsilon_ui()
            self._toggle_inactive_epsilon_ui()
            
            # Update configuration file with default values
            self._create_single_config()
            
            # Don't show popup message as per requirements
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to reset to defaults: {str(e)}")

    def retranslateUi(self, Benchmark):
        _translate = QtCore.QCoreApplication.translate
        Benchmark.setWindowTitle(_translate("Benchmark", f"Benchmarking - {self.selected_module}"))

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

    def open_compound_analyzer(self):
        """Open the compound analyzer window"""
        chembl_file_path = self._sanitize_file_path_text(self.lineEdit_chembl_file.text())
        
        if not chembl_file_path:
            QMessageBox.warning(self.centralwidget, "No File Selected", 
                            "Please select a Docking Score file before opening the analyzer.")
            return
        
        if not os.path.exists(chembl_file_path):
            QMessageBox.warning(self.centralwidget, "File Not Found", 
                            f"The selected Docking File file does not exist:\n{chembl_file_path}")
            return
        
        try:
            # Open as a new window (QMainWindow)
            self.analyzer_window = CompoundAnalyzer(input_file=chembl_file_path)
            self.analyzer_window.show()
            self.analyzer_window.raise_()
            self.analyzer_window.activateWindow()
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", 
                            f"Failed to open compound analyzer: {str(e)}")


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    BenchmarkWindow = QtWidgets.QMainWindow()
    ui = Ui_Benchmark()
    ui.setupUi(BenchmarkWindow)
    BenchmarkWindow.show()
    sys.exit(app.exec_())



# ===== COMPOUND ANALYZER INTEGRATION =====
# The following code is integrated from compound_analyzer_modal.py

import sys
import os
from tokenize import group
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
from matplotlib.widgets import SpanSelector, Slider
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
    QTabWidget,
    QScrollArea,
    QLineEdit,
    QCheckBox,
)
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QColor, QCursor
from scipy import stats


class ThresholdRuler:
    """Class to represent a threshold ruler with its properties"""

    def __init__(self, value, color, is_active=True, label=None, group_id=0):
        self.value = value
        self.color = color
        self.is_active = is_active
        self.group_id = group_id
        self.is_visible = True  # <--- This controls visibility
        self.line = None
        self.annotation = None
        self.label = label or (
            f"Active: {value:.2f}" if is_active else f"Inactive: {value:.2f}"
        )


class MplCanvas(FigureCanvas):
    """Matplotlib canvas class for embedding plots in PyQt"""

    rulerMoved = pyqtSignal(int, float, bool, int)  # ruler_id, value, is_active, group_id

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Set up figure with light theme for modern look
        plt.style.use("default")
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.fig.patch.set_facecolor("white")  # White background
        self.axes = self.fig.add_subplot(111)
        self.axes.set_facecolor("#f8f9fa")  # Light background

        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

        # Set up the canvas to be able to resize with the main window
        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        # Initialize variables for ruler dragging
        self.dragging_ruler_id = None
        self.rulers = []  # List of ThresholdRuler objects
        self.shaded_spans = []  # <--- NEW: Track shaded regions
        self.all_data = None
        self.selected_active_data = {}  # Dict of {group_id: data}
        self.selected_inactive_data = {}  # Dict of {group_id: data}
        self.count_annotations = {}  # Dict of {group_id: annotation}
        self.kde_curve = None
        self.cache_x_grid = None
        self.cache_kde_values = None

        # Connect events for ruler interaction
        self.mpl_connect("button_press_event", self.on_mouse_press)
        self.mpl_connect("button_release_event", self.on_mouse_release)
        self.mpl_connect("motion_notify_event", self.on_mouse_move)
        self.mpl_connect("figure_enter_event", self.on_figure_enter)
        self.mpl_connect("figure_leave_event", self.on_figure_leave)
    
    def redraw_shaded_regions(self):
        """Redraws the colored shaded regions based on current ruler positions"""
        # 1. Remove old spans
        for span in self.shaded_spans:
            try:
                span.remove()
            except ValueError:
                pass 
        self.shaded_spans = []

        if self.all_data is None:
            return

        # 2. Group rulers
        active_rulers_by_group = {}
        inactive_rulers_by_group = {}

        for ruler in self.rulers:
            if not getattr(ruler, "is_visible", True):
                continue  # Skip invisible rulers
            if ruler.is_active:
                if ruler.group_id not in active_rulers_by_group:
                    active_rulers_by_group[ruler.group_id] = []
                active_rulers_by_group[ruler.group_id].append(ruler)
            else:
                if ruler.group_id not in inactive_rulers_by_group:
                    inactive_rulers_by_group[ruler.group_id] = []
                inactive_rulers_by_group[ruler.group_id].append(ruler)

        # 3. Draw Active Regions (Green)
        x_min = min(self.all_data) if len(self.all_data) > 0 else 0
        for group_id, rulers in active_rulers_by_group.items():
            if not rulers: continue
            threshold = max(ruler.value for ruler in rulers)
            
            span = self.axes.axvspan(
                x_min, threshold, alpha=0.2, color="#27ae60", label=f"Active Group {group_id} Selection", zorder=0
            )
            self.shaded_spans.append(span)

        # 4. Draw Inactive Regions (Red)
        x_max = max(self.all_data) if len(self.all_data) > 0 else 0
        for group_id, rulers in inactive_rulers_by_group.items():
            if not rulers: continue
            threshold = min(ruler.value for ruler in rulers)
            
            span = self.axes.axvspan(
                threshold, x_max, alpha=0.2, color="#c0392b", label=f"Inactive Group {group_id} Selection", zorder=0
            )
            self.shaded_spans.append(span)
            
    def on_figure_enter(self, event):
        """Handle mouse entering the figure"""
        if len(self.rulers) > 0:
            self.setCursor(Qt.CrossCursor)

    def on_figure_leave(self, event):
        """Handle mouse leaving the figure"""
        self.setCursor(Qt.ArrowCursor)

    def on_mouse_press(self, event):
        """Handle mouse press event for ruler dragging"""
        if event.inaxes != self.axes or event.xdata is None:
            return

        for i, ruler in enumerate(self.rulers):
            if getattr(ruler, 'is_visible', True) and ruler.line is not None:
                ruler_x = ruler.line.get_xdata()[0]
                
                # Use strictly screen pixels (15 pixel radius) so it works on any data scale!
                ruler_pixel_x = self.axes.transData.transform((ruler_x, 0))[0]
                if abs(event.x - ruler_pixel_x) < 15:  
                    self.dragging_ruler_id = i
                    self.setCursor(QCursor(Qt.SizeHorCursor)) # Horizontal Drag Arrow
                    return

    def on_mouse_release(self, event):
        """Handle mouse release event for ruler dragging"""
        if self.dragging_ruler_id is not None:
            ruler = self.rulers[self.dragging_ruler_id]
            self.dragging_ruler_id = None
            self.setCursor(QCursor(Qt.ArrowCursor)) # Reset to normal mouse

    def on_mouse_move(self, event):
        """Handle mouse move event for ruler dragging"""
        if event.xdata is None and self.dragging_ruler_id is not None:
            return

        # 1. Update cursor when hovering near a visible ruler
        if self.dragging_ruler_id is None and event.inaxes == self.axes and event.x is not None:
            near_ruler = False
            for ruler in self.rulers:
                if getattr(ruler, 'is_visible', True) and ruler.line is not None:
                    ruler_x = ruler.line.get_xdata()[0]
                    # Check in screen pixels (15 pixel radius)
                    ruler_pixel_x = self.axes.transData.transform((ruler_x, 0))[0]
                    
                    if abs(event.x - ruler_pixel_x) < 15:
                        self.setCursor(QCursor(Qt.SizeHorCursor)) # Horizontal Drag Arrow
                        near_ruler = True
                        break
            if not near_ruler:
                self.setCursor(QCursor(Qt.ArrowCursor))

        # 2. Actually drag the ruler and update colors in real-time
        if self.dragging_ruler_id is not None and event.xdata is not None:
            ruler = self.rulers[self.dragging_ruler_id]

            min_val = float(np.min(self.all_data)) if self.all_data is not None else -1000
            max_val = float(np.max(self.all_data)) if self.all_data is not None else 1000
            new_x = max(min_val, min(event.xdata, max_val))

            ruler.value = new_x
            
            # Because the KDE math is cached now, we can update the plot instantly!
            self.update_plot()
            
            self.rulerMoved.emit(
                self.dragging_ruler_id, ruler.value, ruler.is_active, ruler.group_id
            )

    def add_ruler(self, value, color, is_active=True, group_id=0):
        """Add a new threshold ruler"""
        ruler = ThresholdRuler(value, color, is_active, group_id=group_id)
        self.rulers.append(ruler)
        self.update_plot()
        return len(self.rulers) - 1  # Return the ruler ID

    def update_ruler(self, ruler_id, value):
        """Update an existing ruler's value"""
        if 0 <= ruler_id < len(self.rulers):
            self.rulers[ruler_id].value = value
            self.update_plot()
            
    def set_ruler_visibility(self, ruler_id, is_visible):
        """Toggle visibility of a specific ruler and its shading"""
        if 0 <= ruler_id < len(self.rulers):
            self.rulers[ruler_id].is_visible = is_visible
            self.update_plot()

    def remove_ruler(self, ruler_id):
        """Remove a ruler by ID"""
        if 0 <= ruler_id < len(self.rulers):
            # Remove the ruler line and annotation from the plot if they exist
            if self.rulers[ruler_id].line:
                self.rulers[ruler_id].line.remove()
            if self.rulers[ruler_id].annotation:
                self.rulers[ruler_id].annotation.remove()
            del self.rulers[ruler_id]
            self.update_plot()

    def update_selection(self):
        """Update the selected data based on current rulers"""
        if self.all_data is None:
            return

        # Clear previous selections
        self.selected_active_data = {}
        self.selected_inactive_data = {}

        # Initialize ruler grouping dictionaries
        active_rulers_by_group = {}
        inactive_rulers_by_group = {}

        # Group rulers by group_id and type (active/inactive)
        for ruler in self.rulers:
            if not getattr(ruler, 'is_visible', True):  # <--- SKIP HIDDEN ONES
                continue
                
            if ruler.is_active:
                if ruler.group_id not in active_rulers_by_group:
                    active_rulers_by_group[ruler.group_id] = []
                active_rulers_by_group[ruler.group_id].append(ruler)
            else:
                if ruler.group_id not in inactive_rulers_by_group:
                    inactive_rulers_by_group[ruler.group_id] = []
                inactive_rulers_by_group[ruler.group_id].append(ruler)

        # Process active selections
        for group_id, rulers in active_rulers_by_group.items():
            if not rulers:
                continue

            # For active compounds, select those with score <= threshold
            # (lower scores are better for active compounds)
            threshold = max(ruler.value for ruler in rulers)
            selected_indices = self.all_data <= threshold
            self.selected_active_data[group_id] = self.all_data[selected_indices]

        # Process inactive selections
        for group_id, rulers in inactive_rulers_by_group.items():
            if not rulers:
                continue

            # For inactive compounds, select those with score >= threshold
            # (higher scores are worse, thus inactive)
            threshold = min(ruler.value for ruler in rulers)
            selected_indices = self.all_data >= threshold
            self.selected_inactive_data[group_id] = self.all_data[selected_indices]

        # Update count annotations
        self.update_count_annotations()

    def update_count_annotations(self):
        """Update count annotations for all groups"""
        # Remove previous annotations safely
        for annotation in self.count_annotations.values():
            if annotation is not None:
                try:
                    annotation.remove()
                except (NotImplementedError, ValueError):
                    # The annotation was likely already destroyed by self.axes.clear()
                    pass
                    
        self.count_annotations = {}

        # Find center of the plot for annotation
        x_min, x_max = self.axes.get_xlim()
        y_max = self.axes.get_ylim()[1]

        # Add annotations for active groups
        y_offset = 0
        for group_id, data in self.selected_active_data.items():
            if len(data) > 0:
                mid_point = (x_min + x_max) / 2
                y_pos = y_max * (0.8 - 0.1 * y_offset)

                self.count_annotations[f"active_{group_id}"] = self.axes.annotate(
                    f"Group {group_id}: {len(data)} active compounds",
                    xy=(mid_point, y_pos),
                    xytext=(mid_point, y_pos),
                    color="black",
                    weight="bold",
                    fontsize=10,
                    ha="center",
                    va="center",
                    bbox=dict(
                        boxstyle="round,pad=0.5", fc="#abebc6", ec="#27ae60", alpha=0.9
                    ),
                )
                y_offset += 1

        # Add annotations for inactive groups
        for group_id, data in self.selected_inactive_data.items():
            if len(data) > 0:
                mid_point = (x_min + x_max) / 2
                y_pos = y_max * (0.8 - 0.1 * y_offset)

                self.count_annotations[f"inactive_{group_id}"] = self.axes.annotate(
                    f"Group {group_id}: {len(data)} inactive compounds",
                    xy=(mid_point, y_pos),
                    xytext=(mid_point, y_pos),
                    color="black",
                    weight="bold",
                    fontsize=10,
                    ha="center",
                    va="center",
                    bbox=dict(
                        boxstyle="round,pad=0.5", fc="#f5b7b1", ec="#c0392b", alpha=0.9
                    ),
                )
                y_offset += 1

    def plot_distribution(self, data):
        """Plot the distribution and cache the heavy KDE calculation"""
        self.all_data = data
        
        # --- NEW: Compute KDE only ONCE when data is loaded ---
        if len(self.all_data) > 1:
            try:
                kde = stats.gaussian_kde(self.all_data)
                self.cached_x_grid = np.linspace(min(self.all_data), max(self.all_data), 1000)
                self.cached_kde_values = kde(self.cached_x_grid)
            except Exception:
                self.cached_x_grid = None
                self.cached_kde_values = None
                
        self.update_plot()

    def update_plot(self):
        """Update the plot with current rulers and data"""
        if self.all_data is None:
            return

        # Clear previous plot
        self.axes.clear()
        self.shaded_spans = []

        # Create histogram with gradient colors
        n, bins, patches = self.axes.hist(
            self.all_data, bins=40, alpha=0.7, color="#4a69bd", label="All Compounds"
        )

        bin_centers = 0.5 * (bins[:-1] + bins[1:])
        col = bin_centers - min(bin_centers)
        col /= max(col)

        if hasattr(matplotlib, "colormaps"):
            cm = matplotlib.colormaps["viridis"]
        else:
            cm = plt.cm.viridis

        for c, p in zip(col, patches):
            plt.setp(p, "facecolor", cm(c))

        # --- NEW: Draw KDE curve using CACHED values (Instant rendering!) ---
        if self.cached_x_grid is not None and self.cached_kde_values is not None:
            scale_factor = max(n) / max(self.cached_kde_values) * 0.8
            scaled_kde = self.cached_kde_values * scale_factor
            self.kde_curve = self.axes.plot(
                self.cached_x_grid, scaled_kde, "r-", linewidth=2, label="Density Curve"
            )

        y_max = max(n) * 1.1

        # Update selection based on current rulers
        self.update_selection()

        # Plot selected histograms (Active/Inactive subsets)
        active_colors = ["#27ae60", "#2ecc71", "#58d68d", "#82e0aa"]
        inactive_colors = ["#c0392b", "#e74c3c", "#ec7063", "#f1948a"]

        for i, (group_id, data) in enumerate(self.selected_active_data.items()):
            if len(data) > 0:
                color_idx = i % len(active_colors)
                self.axes.hist(
                    data, bins=40, alpha=0.6, color=active_colors[color_idx],
                    label=f"Active Group {group_id}: {len(data)} compounds",
                )

        for i, (group_id, data) in enumerate(self.selected_inactive_data.items()):
            if len(data) > 0:
                color_idx = i % len(inactive_colors)
                self.axes.hist(
                    data, bins=40, alpha=0.6, color=inactive_colors[color_idx],
                    label=f"Inactive Group {group_id}: {len(data)} compounds",
                )

        self.redraw_shaded_regions()

        # Draw all visible rulers
        for i, ruler in enumerate(self.rulers):
            if not getattr(ruler, 'is_visible', True):
                continue
                
            color = ruler.color
            ruler.line = self.axes.axvline(
                x=ruler.value, color=color, linestyle="-", linewidth=2,
                alpha=0.9, label=ruler.label,
            )

            y_pos = y_max * (0.95 - 0.05 * (i % 5))
            x_offset = -0.2 if ruler.is_active else 0.2
            ha = "right" if ruler.is_active else "left"

            ruler.annotation = self.axes.annotate(
                f"{'Active' if ruler.is_active else 'Inactive'} G{ruler.group_id}: {ruler.value:.2f}",
                xy=(ruler.value, y_pos),
                xytext=(ruler.value + x_offset, y_pos),
                color=color, weight="bold", fontsize=10, ha=ha, va="center",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.9),
            )

        self.axes.set_xlabel("Score", fontsize=12, weight="bold")
        self.axes.set_ylabel("Frequency", fontsize=12, weight="bold")
        self.axes.set_title("Compound Score Distribution", fontsize=14, weight="bold")
        self.axes.grid(True, alpha=0.3)
        self.draw()


class GroupPanel(QWidget):
    """Panel for controlling a single group of compounds"""

    thresholdChanged = pyqtSignal(int, float, bool)  # group_id, value, is_active
    quantityChanged = pyqtSignal(int, int, bool)  # group_id, value, is_active
    saveRequested = pyqtSignal(int, bool)  # group_id, is_active
    deleteRequested = pyqtSignal(int, bool)  # group_id, is_active
    visibilityChanged = pyqtSignal(int, bool, bool) # group_id, is_visible, is_active

    def __init__(self, group_id, is_active=True):
        super().__init__()
        self.group_id = group_id
        self.is_active = is_active
        self.is_saved = False  # Track if this group has been saved

        self.initUI()

    def initUI(self):
        """Initialize the UI for this group panel"""
        layout = QVBoxLayout(self)

        # Group box
        group_box = QGroupBox(f"{'Active' if self.is_active else 'Inactive'} Group {self.group_id}")
        group_box.setStyleSheet(
            f"""
            QGroupBox {{
                border: 2px solid {'#27ae60' if self.is_active else '#c0392b'};
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
                color: {'#27ae60' if self.is_active else '#c0392b'};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
            }}
        """
        )

        group_layout = QGridLayout(group_box)

        # Threshold input
        group_layout.addWidget(QLabel("Threshold:"), 0, 0)
        self.threshold_input = QDoubleSpinBox()
        self.threshold_input.setRange(-1000.0, 1000.0)
        self.threshold_input.setDecimals(3)
        self.threshold_input.setSingleStep(0.1)
        self.threshold_input.valueChanged.connect(self.onThresholdChanged)
        group_layout.addWidget(self.threshold_input, 0, 1)

        # Quantity input
        group_layout.addWidget(QLabel("Number of Compounds:"), 1, 0)
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 2147483647)
        self.quantity_input.valueChanged.connect(self.onQuantityChanged)
        group_layout.addWidget(self.quantity_input, 1, 1)

        # Visibility Checkbox
        self.visibility_checkbox = QCheckBox("Show on Plot")
        self.visibility_checkbox.setChecked(True)
        self.visibility_checkbox.toggled.connect(self.onVisibilityChanged)
        group_layout.addWidget(self.visibility_checkbox, 0, 2)

        # Delete button
        self.delete_button = QPushButton("Delete Group")
        self.delete_button.setStyleSheet(
            """
            QPushButton { background-color: #95a5a6; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #7f8c8d; }
        """
        )
        self.delete_button.clicked.connect(self.onDeleteClicked)
        group_layout.addWidget(self.delete_button, 0, 3) 

        # Save button
        self.save_button = QPushButton("Save Group")
        self.save_button.setStyleSheet(
            f"""
            QPushButton {{ background-color: {'#27ae60' if self.is_active else '#c0392b'}; color: white; font-weight: bold; padding: 8px; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {'#2ecc71' if self.is_active else '#e74c3c'}; }}
        """
        )
        self.save_button.clicked.connect(self.onSaveClicked)
        group_layout.addWidget(self.save_button, 1, 3)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")
        group_layout.addWidget(self.status_label, 2, 0, 1, 4)

        layout.addWidget(group_box)

    def onThresholdChanged(self):
        if not self.is_saved:
            self.thresholdChanged.emit(self.group_id, self.threshold_input.value(), self.is_active)

    def onQuantityChanged(self):
        if not self.is_saved:
            self.quantityChanged.emit(self.group_id, self.quantity_input.value(), self.is_active)

    def onVisibilityChanged(self, is_checked):
        self.visibilityChanged.emit(self.group_id, is_checked, self.is_active)

    def onSaveClicked(self):
        self.saveRequested.emit(self.group_id, self.is_active)

    def onDeleteClicked(self):
        self.deleteRequested.emit(self.group_id, self.is_active)

    def updateStatus(self, message):
        self.status_label.setText(message)

    def updateThreshold(self, value):
        self.threshold_input.blockSignals(True)
        self.threshold_input.setValue(value)
        self.threshold_input.blockSignals(False)

    def updateQuantity(self, value):
        self.quantity_input.blockSignals(True)
        self.quantity_input.setValue(value)
        self.quantity_input.blockSignals(False)

    def markAsSaved(self):
        self.is_saved = True
        self.setVisible(False)


class CompoundAnalyzer(QMainWindow):
    """Main application window for Compound Distribution Analyzer"""

    def __init__(self, input_file=None, output_file=None, status_file=None, modal_mode=False):
        super().__init__()

        self.data = None
        self.df = None
        self.input_file = input_file or ""

        # Modal mode settings
        self.modal_mode = modal_mode
        self.output_file = output_file or ""
        self.status_file = status_file or ""

        # Initialize threshold lists
        self.active_rulers = {}  # {group_id: ruler_id}
        self.inactive_rulers = {}  # {group_id: ruler_id}

        # Track saved compound groups
        self.saved_compound_groups = []  # List of saved DataFrames with metadata

        # Set up UI
        self.initUI()

        # Load input file if provided
        if self.input_file and os.path.exists(self.input_file):
            self.load_data(self.input_file)

    def initUI(self):
        """Initialize the user interface"""
        # Set window properties
        self.setWindowTitle("Compound Distribution Analyzer")
        self.setGeometry(100, 100, 1200, 800)

        # Set light theme for the application
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: white;
                color: #333333;
            }
            QGroupBox {
                border: 1px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 3px;
            }
            QLabel {
                color: #333333;
            }
            QDoubleSpinBox, QSpinBox {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 4px;
                background-color: white;
            }
            QPushButton {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 6px;
                background-color: #f8f9fa;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f8f9fa;
                border: 1px solid #cccccc;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
        """
        )

        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # File upload section
        file_section = QHBoxLayout()

        # Upload button
        self.upload_button = QPushButton("Upload Compound Data File")
        self.upload_button.setStyleSheet(
            """
            QPushButton {
                background-color: #007bff;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """
        )
        self.upload_button.clicked.connect(self.upload_file)
        file_section.addWidget(self.upload_button)

        # File label
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: #666666; font-style: italic;")
        file_section.addWidget(self.file_label)

        file_section.addStretch()
        main_layout.addLayout(file_section)

        # Plot section
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.canvas.rulerMoved.connect(self.update_from_ruler)
        main_layout.addWidget(self.canvas)

        # Tab widget for active and inactive controls
        self.tab_widget = QTabWidget()

        # Active compounds tab
        self.active_tab = QWidget()
        active_layout = QVBoxLayout(self.active_tab)

        # Scroll area for active groups
        active_scroll = QScrollArea()
        active_scroll.setWidgetResizable(True)
        active_scroll_content = QWidget()
        self.active_groups_layout = QVBoxLayout(active_scroll_content)
        active_scroll_content.setLayout(self.active_groups_layout) # Set layout for the content widget
        active_scroll.setWidget(active_scroll_content)
        active_layout.addWidget(active_scroll)

        # Add first active group
        self.active_groups = []
        self.add_active_group()

        # Add button for new active group
        add_active_button = QPushButton("Add Another Active Group")
        add_active_button.setStyleSheet(
            """
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """
        )
        add_active_button.clicked.connect(self.add_active_group)
        active_layout.addWidget(add_active_button)

        # Inactive compounds tab
        self.inactive_tab = QWidget()
        inactive_layout = QVBoxLayout(self.inactive_tab)

        # Scroll area for inactive groups
        inactive_scroll = QScrollArea()
        inactive_scroll.setWidgetResizable(True)
        inactive_scroll_content = QWidget()
        self.inactive_groups_layout = QVBoxLayout(inactive_scroll_content)
        inactive_scroll_content.setLayout(self.inactive_groups_layout) # Set layout for the content widget
        inactive_scroll.setWidget(inactive_scroll_content)
        inactive_layout.addWidget(inactive_scroll)

        # Add first inactive group
        self.inactive_groups = []
        self.add_inactive_group()

        # Add button for new inactive group
        add_inactive_button = QPushButton("Add Another Inactive Group")
        add_inactive_button.setStyleSheet(
            """
            QPushButton {
                background-color: #c0392b;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e74c3c;
            }
        """
        )
        add_inactive_button.clicked.connect(self.add_inactive_group)
        inactive_layout.addWidget(add_inactive_button)

        # Add tabs to tab widget
        self.tab_widget.addTab(self.active_tab, "Active Compounds")
        self.tab_widget.addTab(self.inactive_tab, "Inactive Compounds")

        main_layout.addWidget(self.tab_widget)

        # Bottom buttons section
        bottom_buttons_layout = QHBoxLayout()

        # Save plot button
        save_plot_button = QPushButton("Save Plot")
        save_plot_button.setStyleSheet(
            """
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
        """
        )
        save_plot_button.clicked.connect(self.save_plot)
        bottom_buttons_layout.addWidget(save_plot_button)

        # Save All Groups as CSV button
        self.save_all_csv_button = QPushButton("Save All Groups as CSV")
        self.save_all_csv_button.setStyleSheet(
            """
            QPushButton {
                background-color: #f39c12;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """
        )
        self.save_all_csv_button.clicked.connect(self.save_all_groups_as_csv)
        self.save_all_csv_button.setEnabled(False)  # Initially disabled
        bottom_buttons_layout.addWidget(self.save_all_csv_button)

        # Close Window button
        self.close_window_button = QPushButton("Close Window")
        self.close_window_button.setStyleSheet(
            """
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """
        )
        self.close_window_button.clicked.connect(self.close)
        self.close_window_button.setVisible(False)  # Initially hidden
        bottom_buttons_layout.addWidget(self.close_window_button)

        bottom_buttons_layout.addStretch()
        main_layout.addLayout(bottom_buttons_layout)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Disable controls until data is loaded
        self.disable_controls()

    def add_active_group(self):
        """Add a new active group panel"""
        group_id = len(self.active_groups)
        group_panel = GroupPanel(group_id, is_active=True)

       # Connect signals
        group_panel.thresholdChanged.connect(self.update_from_threshold)
        group_panel.quantityChanged.connect(self.update_from_quantity)
        group_panel.saveRequested.connect(self.save_compounds)
        group_panel.deleteRequested.connect(self.delete_group)
        group_panel.visibilityChanged.connect(self.update_group_visibility) # <--- ADD THIS LINE TO BOTH
        # Add to layout and list
        self.active_groups_layout.addWidget(group_panel)
        self.active_groups.append(group_panel)

        # If data is loaded, add ruler and update
        if self.data is not None:
            # Calculate threshold (10th percentile + some offset based on group)
            p_val = 10 + group_id * 5
            p_val = min(p_val, 40)  # Cap at 40th percentile
            threshold = np.percentile(self.data, p_val)

            # Add ruler
            ruler_id = self.canvas.add_ruler(
                threshold, "#27ae60", is_active=True, group_id=group_id
            )
            self.active_rulers[group_id] = ruler_id

            # Update panel
            group_panel.updateThreshold(threshold)
            group_panel.updateQuantity(int(len(self.data) * p_val / 100))

    def add_inactive_group(self):
        """Add a new inactive group panel"""
        group_id = len(self.inactive_groups)
        group_panel = GroupPanel(group_id, is_active=False)

       # Connect signals
        group_panel.thresholdChanged.connect(self.update_from_threshold)
        group_panel.quantityChanged.connect(self.update_from_quantity)
        group_panel.saveRequested.connect(self.save_compounds)
        group_panel.deleteRequested.connect(self.delete_group)
        group_panel.visibilityChanged.connect(self.update_group_visibility) # <--- ADD THIS LINE TO BOTH

        # Add to layout and list
        self.inactive_groups_layout.addWidget(group_panel)
        self.inactive_groups.append(group_panel)

        # If data is loaded, add ruler and update
        if self.data is not None:
            # Calculate threshold (90th percentile - some offset based on group)
            p_val = 90 - group_id * 5
            p_val = max(p_val, 60)  # Cap at 60th percentile
            threshold = np.percentile(self.data, p_val)

            # Add ruler
            ruler_id = self.canvas.add_ruler(
                threshold, "#c0392b", is_active=False, group_id=group_id
            )
            self.inactive_rulers[group_id] = ruler_id

            # Update panel
            group_panel.updateThreshold(threshold)
            group_panel.updateQuantity(int(len(self.data) * (100 - p_val) / 100))
            
    def update_group_visibility(self, group_id, is_visible, is_active):
        """Hide or show a group's lines and shading on the plot"""
        ruler_dict = self.active_rulers if is_active else self.inactive_rulers
        
        if group_id in ruler_dict:
            ruler_id = ruler_dict[group_id]
            # Update visibility flag
            if 0 <= ruler_id < len(self.canvas.rulers):
                self.canvas.rulers[ruler_id].is_visible = is_visible
                self.canvas.update_plot()
            
            status = "Visible" if is_visible else "Hidden"
            self.statusBar.showMessage(f"{'Active' if is_active else 'Inactive'} Group {group_id} is now {status} on plot.")

    def disable_controls(self):
        """Disable all controls until data is loaded"""
        self.tab_widget.setEnabled(False)

    def enable_controls(self):
        """Enable controls after data is loaded"""
        self.tab_widget.setEnabled(True)

    def upload_file(self):
        """Show file upload dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Compound Data File", "", "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self.load_data(file_path)

    def load_data(self, file_path):
        """Load data from CSV file"""
        try:
            # Load data
            self.df = pd.read_csv(file_path)
            self.input_file = file_path

            # Check if required column exists
            score_column = None
            possible_columns = [
                "score",
                "lowest_binding_energy",
                "binding_energy",
                "docking_score",
            ]

            for col in possible_columns:
                if col in self.df.columns:
                    score_column = col
                    break

            if score_column is None:
                # If no known column is found, ask the user
                score_columns = [
                    col
                    for col in self.df.columns
                    if "score" in col.lower() or "energy" in col.lower()
                ]

                if score_columns:
                    # If we found some likely candidates, use the first one
                    score_column = score_columns[0]
                elif len(self.df.columns) > 0:
                    # Otherwise use the first numerical column
                    for col in self.df.columns:
                        if pd.api.types.is_numeric_dtype(self.df[col]):
                            score_column = col
                            break

            if score_column is None:
                QMessageBox.critical(
                    self, "Error", "Could not find a suitable score column in the CSV file."
                )
                return

            # Extract score values
            self.data = self.df[score_column].values
            self.score_column = score_column

            # Sort by score (lower is better)
            self.df = self.df.sort_values(by=score_column)
            self.data = self.df[score_column].values

            # Clear existing rulers
            self.canvas.rulers = []
            self.active_rulers = {}
            self.inactive_rulers = {}

            # Set initial thresholds for all groups
            min_val = self.data.min()
            max_val = self.data.max()

            # Update active groups
            for i, group_panel in enumerate(self.active_groups):
                # Calculate threshold (10th percentile + some offset based on group)
                p_val = 10 + i * 5
                p_val = min(p_val, 40)  # Cap at 40th percentile
                threshold = np.percentile(self.data, p_val)

                # Add ruler
                ruler_id = self.canvas.add_ruler(
                    threshold, "#27ae60", is_active=True, group_id=i
                )
                self.active_rulers[i] = ruler_id

                # Update panel
                group_panel.updateThreshold(threshold)
                group_panel.updateQuantity(int(len(self.data) * p_val / 100))

            # Update inactive groups
            for i, group_panel in enumerate(self.inactive_groups):
                # Calculate threshold (90th percentile - some offset based on group)
                p_val = 90 - i * 5
                p_val = max(p_val, 60)  # Cap at 60th percentile
                threshold = np.percentile(self.data, p_val)

                # Add ruler
                ruler_id = self.canvas.add_ruler(
                    threshold, "#c0392b", is_active=False, group_id=i
                )
                self.inactive_rulers[i] = ruler_id

                # Update panel
                group_panel.updateThreshold(threshold)
                group_panel.updateQuantity(int(len(self.data) * (100 - p_val) / 100))

            # Plot distribution
            self.canvas.plot_distribution(self.data)

            # Enable controls
            self.enable_controls()
            # Enable "Save All Groups as CSV" button since we now have data
            self.save_all_csv_button.setEnabled(True)
    

            # Update file label
            self.file_label.setText(f"Loaded: {os.path.basename(file_path)}")

            # Update status
            self.statusBar.showMessage(
                f"Loaded {len(self.df)} compounds from {os.path.basename(file_path)}"
            )

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def update_from_ruler(self, ruler_id, value, is_active, group_id):
        """Update controls when a ruler is moved"""
        if is_active:
            if group_id < len(self.active_groups) and not self.active_groups[group_id].is_saved:
                self.active_groups[group_id].updateThreshold(value)

                # Update quantity based on threshold
                if self.data is not None:
                    # For active compounds, count those with score <= threshold
                    count = np.sum(self.data <= value)
                    self.active_groups[group_id].updateQuantity(count)
        else:
            if group_id < len(self.inactive_groups) and not self.inactive_groups[group_id].is_saved:
                self.inactive_groups[group_id].updateThreshold(value)

                # Update quantity based on threshold
                if self.data is not None:
                    # For inactive compounds, count those with score >= threshold
                    count = np.sum(self.data >= value)
                    self.inactive_groups[group_id].updateQuantity(count)

        # Update status bar with feedback
        self.statusBar.showMessage(
            f"{'Active' if is_active else 'Inactive'} Group {group_id} threshold set to {value:.2f}"
        )

    def update_from_threshold(self, group_id, value, is_active):
        """Update plot when threshold controls are changed"""
        if self.data is None:
            return

        # Update the ruler
        if is_active:
            if group_id in self.active_rulers:
                self.canvas.update_ruler(self.active_rulers[group_id], value)

                # Update quantity based on threshold
                if self.data is not None:
                    # For active compounds, count those with score <= threshold
                    count = np.sum(self.data <= value)
                    self.active_groups[group_id].updateQuantity(count)
        else:
            if group_id in self.inactive_rulers:
                self.canvas.update_ruler(self.inactive_rulers[group_id], value)

                # Update quantity based on threshold
                if self.data is not None:
                    # For inactive compounds, count those with score >= threshold
                    count = np.sum(self.data >= value)
                    self.inactive_groups[group_id].updateQuantity(count)

        # Update status bar
        self.statusBar.showMessage(
            f"{'Active' if is_active else 'Inactive'} Group {group_id} threshold updated to {value:.2f}"
        )

    def update_from_quantity(self, group_id, quantity, is_active):
        """Update threshold when quantity controls are changed"""
        if self.data is None:
            return

        # Calculate threshold based on quantity
        if is_active:
            # For active compounds, find threshold that gives us the desired quantity
            if quantity > 0 and quantity <= len(self.data):
                sorted_data = np.sort(self.data)
                threshold = sorted_data[quantity - 1]

                # Update ruler and threshold input
                if group_id in self.active_rulers:
                    self.canvas.update_ruler(self.active_rulers[group_id], threshold)
                if group_id < len(self.active_groups):
                    self.active_groups[group_id].updateThreshold(threshold)
        else:
            # For inactive compounds, find threshold that gives us the desired quantity
            if quantity > 0 and quantity <= len(self.data):
                sorted_data = np.sort(self.data)
                threshold = sorted_data[len(self.data) - quantity]

                # Update ruler and threshold input
                if group_id in self.inactive_rulers:
                    self.canvas.update_ruler(self.inactive_rulers[group_id], threshold)
                if group_id < len(self.inactive_groups):
                    self.inactive_groups[group_id].updateThreshold(threshold)

        # Update status bar
        self.statusBar.showMessage(
            f"{'Active' if is_active else 'Inactive'} Group {group_id} quantity set to {quantity}"
        )

    def save_compounds(self, group_id, is_active):
        """Save selected compounds to a separate CSV file and store its path"""
        if self.df is None or self.data is None:
            QMessageBox.warning(self, "No Data", "Please load data first.")
            return

        # Get threshold from the appropriate group
        threshold = None
        group_panel = None
        if is_active and group_id < len(self.active_groups):
            group_panel = self.active_groups[group_id]
            threshold = group_panel.threshold_input.value()
        elif not is_active and group_id < len(self.inactive_groups):
            group_panel = self.inactive_groups[group_id]
            threshold = group_panel.threshold_input.value()

        if threshold is None or group_panel is None:
            QMessageBox.warning(self, "Invalid Group", "Could not find the specified group.")
            return

        try:
            # Generate filename with timestamp and descriptive information
            base_name = os.path.splitext(os.path.basename(self.input_file))[0]
            timestamp = time.strftime("%Y%m%d_%H%M%S")

            # Find all compounds that match the selection criteria
            if is_active:
                # For active compounds, select those with score <= threshold
                selected_indices = self.df[self.score_column] <= threshold
                compound_type = "active"
            else:
                # For inactive compounds, select those with score >= threshold
                selected_indices = self.df[self.score_column] >= threshold
                compound_type = "inactive"

            # Get the selected compounds
            selected_df = self.df.loc[selected_indices].copy()

            # Create descriptive filename
            file_name = f"{base_name}_{compound_type}_group{group_id}_{len(selected_df)}compounds_{timestamp}.csv"

            # Get save directory from user
            save_dir = QFileDialog.getExistingDirectory(self, "Select Save Directory")
            if not save_dir:
                return

            file_path = os.path.join(save_dir, file_name)

            # Save to CSV
            selected_df.to_csv(file_path, index=False)

            # Add metadata to the saved group, including the file path
            group_metadata = {
                "file_path": file_path,  # Store the path to the saved CSV
                "group_id": group_id,
                "is_active": is_active,
                "threshold": threshold,
                "compound_type": compound_type,
                "count": len(selected_df),
            }

            # Add to saved groups list
            self.saved_compound_groups.append(group_metadata)

            # Mark the group panel as saved and hide it
            group_panel.markAsSaved()
            group_panel.updateStatus(f"Saved {len(selected_df)} compounds to {os.path.basename(file_path)}")

            # Remove the ruler from the plot
            if is_active and group_id in self.active_rulers:
                ruler_id = self.active_rulers[group_id]
                self.canvas.remove_ruler(ruler_id)
                del self.active_rulers[group_id]
            elif not is_active and group_id in self.inactive_rulers:
                ruler_id = self.inactive_rulers[group_id]
                self.canvas.remove_ruler(ruler_id)
                del self.inactive_rulers[group_id]

            # Enable the "Save All Groups as CSV" button if this is the first saved group
            if len(self.saved_compound_groups) == 1:
                self.save_all_csv_button.setEnabled(True)

            self.statusBar.showMessage(
                f"Saved {len(selected_df)} {compound_type} compounds to {os.path.basename(file_path)}"
            )

        except Exception as e:
            self.statusBar.showMessage(f"Error saving group: {str(e)}")
            QMessageBox.critical(self, "Save Error", f"Failed to save group: {str(e)}")

    def delete_group(self, group_id, is_active):
        """Delete a group panel and its associated ruler"""
        if is_active:
            group_list = self.active_groups
            ruler_dict = self.active_rulers
            layout = self.active_groups_layout
        else:
            group_list = self.inactive_groups
            ruler_dict = self.inactive_rulers
            layout = self.inactive_groups_layout

        # Find the panel to delete
        panel_to_delete = None
        for panel in group_list:
            if panel.group_id == group_id:
                panel_to_delete = panel
                break

        if panel_to_delete:
            # Remove panel from layout and list
            layout.removeWidget(panel_to_delete)
            panel_to_delete.deleteLater()  # Properly delete the widget
            group_list.remove(panel_to_delete)

            # Remove ruler from canvas
            if group_id in ruler_dict:
                ruler_id = ruler_dict[group_id]
                self.canvas.remove_ruler(ruler_id)
                del ruler_dict[group_id]

            # Remove saved data if it was saved
            self.saved_compound_groups = [
                g for g in self.saved_compound_groups if not (
                    g["group_id"] == group_id and g["is_active"] == is_active
                )
            ]

            # If no groups are saved, disable the "Save All Groups as CSV" button
            if not self.saved_compound_groups:
                self.save_all_csv_button.setEnabled(False)
                self.close_window_button.setVisible(False) # Hide close button if no groups are saved

            self.statusBar.showMessage(f"{'Active' if is_active else 'Inactive'} Group {group_id} deleted.")
            self.canvas.update_plot() # Redraw plot to reflect ruler removal

    def save_all_groups_as_csv(self):
        """Dynamically save all current groups directly to a single CSV file"""
        if self.df is None or self.data is None:
            QMessageBox.warning(self, "No Data", "Please load data first.")
            return

        try:
            # Generate filename with timestamp
            base_name = os.path.splitext(os.path.basename(self.input_file))[0] if self.input_file else "compounds"
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            file_name = f"{base_name}_all_groups_{timestamp}.csv"

            # Get save file path from user
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save All Groups as CSV", file_name, "CSV Files (*.csv);;All Files (*)"
            )

            if not file_path:
                return

            combined_data = []

            # 1. Grab data for all Active Groups
            for group_panel in self.active_groups:
                threshold = group_panel.threshold_input.value()
                # Select those with score <= threshold
                selected_indices = self.df[self.score_column] <= threshold
                group_df = self.df.loc[selected_indices].copy()
                
                # Add metadata columns
                group_df["group_id"] = group_panel.group_id
                group_df["group_type"] = "active"
                group_df["threshold_used"] = threshold
                combined_data.append(group_df)

            # 2. Grab data for all Inactive Groups
            for group_panel in self.inactive_groups:
                threshold = group_panel.threshold_input.value()
                # Select those with score >= threshold
                selected_indices = self.df[self.score_column] >= threshold
                group_df = self.df.loc[selected_indices].copy()
                
                # Add metadata columns
                group_df["group_id"] = group_panel.group_id
                group_df["group_type"] = "inactive"
                group_df["threshold_used"] = threshold
                combined_data.append(group_df)

            if not combined_data:
                QMessageBox.warning(self, "No Groups", "There is no group data to save.")
                return

            # Concatenate all DataFrames and save
            final_df = pd.concat(combined_data, ignore_index=True)
            final_df.to_csv(file_path, index=False)

            # Show the "Close Window" button if modal
            self.close_window_button.setVisible(True)

            # Update status
            total_compounds = len(final_df)
            num_groups = len(self.active_groups) + len(self.inactive_groups)
            self.statusBar.showMessage(f"Saved {total_compounds} compounds from {num_groups} groups to {os.path.basename(file_path)}")

            QMessageBox.information(self, "Export Successful", 
                                  f"Successfully exported {total_compounds} compounds from {num_groups} groups to {os.path.basename(file_path)}")

        except Exception as e:
            self.statusBar.showMessage(f"Error exporting groups: {str(e)}")
            QMessageBox.critical(self, "Export Error", f"Failed to export groups: {str(e)}")

    def save_plot(self):
        """Save the current plot as an image"""
        if not hasattr(self, 'canvas') or self.canvas is None:
            return

        # Get save file name from user
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "", "PNG Files (*.png);;JPEG Files (*.jpg);;PDF Files (*.pdf);;All Files (*)"
        )

        if file_name:
            try:
                # Save the figure
                self.canvas.fig.savefig(file_name, dpi=300, bbox_inches='tight')
                self.statusBar.showMessage(f"Plot saved to {file_name}")
                QMessageBox.information(self, "Save Successful", f"Plot saved to {file_name}")
            except Exception as e:
                self.statusBar.showMessage(f"Error saving plot: {str(e)}")
                QMessageBox.critical(self, "Save Error", f"Failed to save plot: {str(e)}")

    def closeEvent(self, event):
        """Handle window close event"""
        if self.modal_mode and self.status_file:
            try:
                # Write cancelled status if not already completed
                if not os.path.exists(self.status_file):
                    with open(self.status_file, 'w') as f:
                        f.write("CANCELLED")
            except:
                pass
        event.accept()


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Compound Distribution Analyzer')
    parser.add_argument('--input', type=str, help='Input CSV file path')
    parser.add_argument('--output', type=str, help='Output CSV file path')
    parser.add_argument('--status', type=str, help='Status file path')
    parser.add_argument('--modal', action='store_true', help='Run in modal mode')
    return parser.parse_args()

# ===== END COMPOUND ANALYZER INTEGRATION =====

