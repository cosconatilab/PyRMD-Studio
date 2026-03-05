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
# COMPLETE ORIGINAL CODE FOR DOCK_PREP.PY
# ============================================================================
import pandas as pd
import os
import sys
import gc
import psutil
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import tempfile
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox,
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
    QTabWidget, QFrame, QSplitter, QScrollArea, QGroupBox,
    QCheckBox, QDialog, QDialogButtonBox, QRadioButton, QButtonGroup,
    QGridLayout, QSpinBox, QHeaderView, QComboBox, QFormLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QMimeData
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon, QDragEnterEvent, QDropEvent

class FinalColumnSelectionDialog(QDialog):
    """Final column selection dialog with perfect dropdown sizing and visibility"""
    def __init__(self, columns, required_selections, file_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Select Columns - {file_type.title()} File")
        self.setMinimumSize(650, 450)
        self.columns = ["- Please Select -"] + columns
        self.required_selections = required_selections
        self.file_type = file_type
        self.selected_columns = {}
        self.comboboxes = {}
        self.init_ui()
        
    def init_ui(self):
        # Clean professional style - absolutely no dashed borders
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(25)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title - clean, no borders
        title = QLabel(f"Column Selection - {self.file_type.title()} File")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2c3e50; border: none; background: transparent;")
        layout.addWidget(title)
        
        # Instructions - clean, no borders
        instructions = QLabel("Please select the corresponding columns from your CSV file using the dropdowns below:")
        instructions.setStyleSheet("color: #34495e; font-size: 12pt; border: none; background: transparent; padding: 0;")
        layout.addWidget(instructions)
        
        # Form layout for dropdowns
        form_layout = QFormLayout()
        form_layout.setSpacing(25)
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignLeft)
        
        # Create dropdown for each required selection
        for selection in self.required_selections:
            if selection == "docking_score":
                label_text = "Docking Score Column:"
            elif selection == "ligand_title":
                label_text = "Ligand Title Column:"
            elif selection == "smiles_string":
                label_text = "SMILES String Column:"
            else:
                label_text = selection.replace("_", " ").title() + ":"
            
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #2c3e50; border: none; background: transparent;")
            
            combo = QComboBox()
            combo.addItems(self.columns)
            combo.setStyleSheet("""
                QComboBox {
                    padding: 12px;
                    border: 1px solid #d0d0d0;
                    border-radius: 4px;
                    background-color: white;
                    font-size: 11pt;
                    min-height: 25px;
                    color: #2c3e50;
                }
                QComboBox:hover {
                    border-color: #3498db;
                    background-color: #f8f9fa;
                }
                QComboBox:focus {
                    border-color: #3498db;
                    outline: none;
                }
                QComboBox::drop-down {
                    subcontrol-origin: padding;
                    subcontrol-position: top right;
                    width: 25px;
                    border-left-width: 1px;
                    border-left-color: #d0d0d0;
                    border-left-style: solid;
                    border-top-right-radius: 3px;
                    border-bottom-right-radius: 3px;
                    background-color: #f8f9fa;
                }
                QComboBox::down-arrow {
                    image: none;
                    border: none;
                    width: 0;
                    height: 0;
                    border-left: 5px solid transparent;
                    border-right: 5px solid transparent;
                    border-top: 5px solid #7f8c8d;
                }
                QComboBox QAbstractItemView {
                    border: 1px solid #d0d0d0;
                    background-color: white;
                    selection-background-color: #e3f2fd;
                    selection-color: #1976d2;
                    outline: none;
                    max-height: 200px;
                    min-width: 200px;
                }
                QComboBox QAbstractItemView::item {
                    padding: 8px 12px;
                    border: none;
                    color: #2c3e50;
                    background-color: white;
                }
                QComboBox QAbstractItemView::item:selected {
                    background-color: #e3f2fd;
                    color: #1976d2;
                }
                QComboBox QAbstractItemView::item:hover {
                    background-color: #f5f5f5;
                    color: #2c3e50;
                }
            """)
            combo.setMaxVisibleItems(8)
            
            self.comboboxes[selection] = combo
            form_layout.addRow(label, combo)
            
        layout.addLayout(form_layout)
        
        hint_label = QLabel("💡 Hint: Click on each dropdown to select the corresponding column from your CSV file.")
        hint_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                font-style: italic;
                margin-top: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
            }
        """)
        layout.addWidget(hint_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.setStyleSheet("""
            QDialogButtonBox { margin-top: 25px; }
            QDialogButtonBox QPushButton {
                background-color: #3498db; color: white; border: none;
                padding: 12px 24px; border-radius: 4px; font-weight: bold;
                font-size: 11pt; min-width: 100px;
            }
            QDialogButtonBox QPushButton:hover { background-color: #2980b9; }
            QDialogButtonBox QPushButton:pressed { background-color: #21618c; }
            QDialogButtonBox QPushButton[text="Cancel"] { background-color: #95a5a6; }
            QDialogButtonBox QPushButton[text="Cancel"]:hover { background-color: #7f8c8d; }
        """)
        
        button_box.accepted.connect(self.on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def on_accept(self):
        missing_selections = []
        for selection, combo in self.comboboxes.items():
            if combo.currentIndex() == 0:
                if selection == "docking_score":
                    missing_selections.append("Docking Score Column")
                elif selection == "ligand_title":
                    missing_selections.append("Ligand Title Column")
                elif selection == "smiles_string":
                    missing_selections.append("SMILES String Column")
                else:
                    missing_selections.append(selection.replace("_", " ").title())
            else:
                self.selected_columns[selection] = combo.currentText()
        
        if missing_selections:
            missing_text = ", ".join(missing_selections)
            QMessageBox.warning(
                self, "Selection Required", 
                f"Please select columns for: {missing_text}\n\nUse the dropdowns to choose the appropriate columns from your CSV file."
            )
            return
            
        self.accept()

class PerfectFileUploadWidget(QFrame):
    file_uploaded = pyqtSignal(str, str, dict)
    
    def __init__(self, file_type, description, required_selections):
        super().__init__()
        self.file_type = file_type
        self.description = description
        self.required_selections = required_selections
        self.file_path = ""
        self.selected_columns = {}
        self.init_ui()
        
    def init_ui(self):
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #e0e0e0; border-radius: 8px;
                background-color: #fafafa; margin: 5px;
            }
            QFrame:hover { border: 2px solid #3498db; background-color: #f0f8ff; }
            QLabel { border: none; background: transparent; }
        """)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        
        self.status_label = QLabel("📁")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 24px; color: #7f8c8d;")
        layout.addWidget(self.status_label)
        
        self.desc_label = QLabel(f"Drop {self.description} here\nor click to browse")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setStyleSheet("color: #7f8c8d; font-weight: bold;")
        layout.addWidget(self.desc_label)
        
        self.file_label = QLabel("")
        self.file_label.setAlignment(Qt.AlignCenter)
        self.file_label.setStyleSheet("color: #27ae60; font-size: 10px;")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)
        
        self.setLayout(layout)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if len(urls) == 1 and urls[0].toLocalFile().endswith(".csv"):
                event.acceptProposedAction()
            else:
                event.ignore()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files and files[0].endswith(".csv"):
            self.handle_file_selection(files[0])
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.browse_file()
            
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select {self.description}", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.handle_file_selection(file_path)
            
    def handle_file_selection(self, file_path):
        try:
            df = pd.read_csv(file_path, nrows=1)
            columns = df.columns.tolist()
            
            dialog = FinalColumnSelectionDialog(columns, self.required_selections, self.file_type, self)
            if dialog.exec_() == QDialog.Accepted:
                self.selected_columns = dialog.selected_columns
                self.set_file(file_path)
            else:
                self.clear_file()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error reading CSV file: {str(e)}")
            self.clear_file()
            
    def set_file(self, file_path):
        self.file_path = file_path
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        self.file_label.setText(f"✓ {file_name}\n({file_size:.1f} MB)")
        self.status_label.setText("✅")
        self.desc_label.setText(f"{self.description} loaded")
        self.setStyleSheet("""
            QFrame { border: 2px solid #27ae60; border-radius: 8px; background-color: #d5f4e6; margin: 5px; }
            QLabel { border: none; background: transparent; }
        """)
        self.file_uploaded.emit(file_path, self.file_type, self.selected_columns)
        
    def clear_file(self):
        self.file_path = ""
        self.selected_columns = {}
        self.file_label.setText("")
        self.status_label.setText("📁")
        self.desc_label.setText(f"Drop {self.description} here\nor click to browse")
        self.setStyleSheet("""
            QFrame { border: 2px solid #e0e0e0; border-radius: 8px; background-color: #fafafa; margin: 5px; }
            QFrame:hover { border: 2px solid #3498db; background-color: #f0f8ff; }
            QLabel { border: none; background: transparent; }
        """)

class OptimizedCSVMergerWorker(QThread):
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    memory_updated = pyqtSignal(str)
    cpu_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, docking_file, smiles_file, output_file, docking_cols, smiles_cols, chunk_size=100000):
        super().__init__()
        self.docking_file = docking_file
        self.smiles_file = smiles_file
        self.output_file = output_file
        self.docking_cols = docking_cols
        self.smiles_cols = smiles_cols
        self.chunk_size = chunk_size
        self.should_stop = False
        
    def stop(self):
        self.should_stop = True
        
    def get_system_stats(self):
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = psutil.cpu_percent(interval=0.1)
        return memory_mb, cpu_percent
        
    def run(self):
        try:
            initial_memory, _ = self.get_system_stats()
            cpu_count = mp.cpu_count()
            self.memory_updated.emit(f"Initial memory: {initial_memory:.1f} MB")
            self.cpu_updated.emit(f"Available Cores: {cpu_count}")
            
            self.status_updated.emit("Loading SMILES data with vectorized operations...")
            self.progress_updated.emit(5)
            
            smiles_lookup_series, smiles_rows = self.load_smiles_data_optimized()
            if self.should_stop: return
                
            self.progress_updated.emit(30)
            success, summary = self.process_docking_file_optimized(smiles_lookup_series, smiles_rows)
                
            if success and not self.should_stop:
                self.progress_updated.emit(100)
                self.status_updated.emit("Merge completed successfully!")
                self.finished.emit(True, summary)
            
        except Exception as e:
            self.status_updated.emit("Merge failed!")
            self.finished.emit(False, f"Error during merge: {str(e)}")
                    
    def load_smiles_data_optimized(self):
        self.status_updated.emit("Loading SMILES data with vectorized operations...")
        ligand_col = self.smiles_cols["ligand_title"]
        smiles_col = self.smiles_cols["smiles_string"]
        
        smiles_data_list = []
        total_rows = 0
        chunk_count = 0
        
        for chunk in pd.read_csv(self.smiles_file, chunksize=self.chunk_size):
            if self.should_stop: return pd.Series(), total_rows
                
            chunk[ligand_col] = chunk[ligand_col].astype(str)
            chunk_subset = chunk[[ligand_col, smiles_col]].copy()
            smiles_data_list.append(chunk_subset)
            
            total_rows += len(chunk)
            chunk_count += 1
            if chunk_count % 5 == 0:
                self.status_updated.emit(f"Loaded {total_rows:,} SMILES entries...")
                
            del chunk
            gc.collect()
        
        if smiles_data_list:
            combined_smiles_df = pd.concat(smiles_data_list, ignore_index=True)
            combined_smiles_df = combined_smiles_df.drop_duplicates(subset=[ligand_col])
            smiles_lookup_series = combined_smiles_df.set_index(ligand_col)[smiles_col]
            del smiles_data_list
            del combined_smiles_df
            gc.collect()
        else:
            smiles_lookup_series = pd.Series()
        
        self.status_updated.emit(f"SMILES lookup optimized: {len(smiles_lookup_series):,} unique entries")
        return smiles_lookup_series, total_rows
        
    def process_docking_file_optimized(self, smiles_lookup_series, smiles_rows):
        self.status_updated.emit("Processing docking data with vectorized operations...")
        docking_ligand_col = self.docking_cols["ligand_title"]
        
        docking_size = os.path.getsize(self.docking_file) / (1024 * 1024)
        processed_chunks = []
        total_rows = 0
        matched_rows = 0
        chunk_count = 0
        
        for chunk in pd.read_csv(self.docking_file, chunksize=self.chunk_size):
            if self.should_stop: return False, "Merge stopped by user"
                
            chunk_count += 1
            chunk[docking_ligand_col] = chunk[docking_ligand_col].astype(str)
            chunk["smiles"] = chunk[docking_ligand_col].map(smiles_lookup_series).fillna("")
            
            chunk_matches = (chunk["smiles"] != "").sum()
            matched_rows += chunk_matches
            
            if "Zinc" not in chunk.columns:
                chunk["Zinc"] = ""
            
            processed_chunks.append(chunk)
            total_rows += len(chunk)
            
            progress = 30 + int((total_rows / max(total_rows, 1)) * 60)
            self.progress_updated.emit(min(progress, 90))
            self.status_updated.emit(f"Processed {total_rows:,} rows, {matched_rows:,} matches")
            
            memory, cpu = self.get_system_stats()
            self.memory_updated.emit(f"Memory: {memory:.1f} MB")
            self.cpu_updated.emit(f"CPU: {cpu:.1f}%")
            gc.collect()
            
        self.status_updated.emit("Combining results with vectorized operations...")
        
        if processed_chunks:
            final_df = pd.concat(processed_chunks, ignore_index=True)
            final_columns = list(final_df.columns)
            if "smiles" in final_columns:
                final_columns.remove("smiles")
                final_columns.append("smiles")
            final_df = final_df[final_columns]
            final_df.to_csv(self.output_file, index=False)
            del processed_chunks
            del final_df
            gc.collect()
        
        mismatched_rows = total_rows - matched_rows
        match_rate = (matched_rows / total_rows) * 100 if total_rows > 0 else 0
        output_size = os.path.getsize(self.output_file) / (1024 * 1024) if os.path.exists(self.output_file) else 0
        
        summary = f"""Perfect Merge Summary:
• Docking file: {docking_size:.1f} MB ({total_rows:,} rows)
• SMILES file: ({smiles_rows:,} entries)
• Output file: {output_size:.1f} MB
• Matched rows: {matched_rows:,}
• Mismatched rows: {mismatched_rows:,}
• Match rate: {match_rate:.1f}%
• Output saved to: {self.output_file}"""
        return True, summary

class FinalPerfectCSVMergerGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.docking_file_path = ""
        self.smiles_file_path = ""
        self.docking_cols = {}
        self.smiles_cols = {}
        self.output_file_path = ""
        self.worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("CSV Merger")
        self.setGeometry(100, 100, 1200, 950)
        
        self.setStyleSheet("""
            QWidget { background-color: #ffffff; font-family: 'Segoe UI', Arial, sans-serif; font-size: 10pt; }
            QGroupBox { font-weight: bold; border: 1px solid #d0d0d0; border-radius: 6px; margin-top: 1ex; padding-top: 15px; background-color: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px 0 8px; color: #2c3e50; background-color: white; }
            QPushButton { background-color: #3498db; border: none; color: white; padding: 10px 20px; border-radius: 4px; font-weight: bold; font-size: 11pt; }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #21618c; }
            QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }
            QLineEdit { padding: 8px; border: 1px solid #d0d0d0; border-radius: 4px; background-color: white; }
            QLineEdit:focus { border-color: #3498db; }
            QTextEdit { border: 1px solid #d0d0d0; border-radius: 4px; background-color: white; padding: 8px; }
            QProgressBar { border: 1px solid #d0d0d0; border-radius: 4px; text-align: center; background-color: white; height: 25px; }
            QProgressBar::chunk { background-color: #27ae60; border-radius: 2px; }
            QLabel { color: #2c3e50; border: none; background: transparent; }
        """)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10) # Reduced from 25 to tighten the gaps
        main_layout.setContentsMargins(20, 15, 20, 20) # Reduced margins
        
        header_layout = QVBoxLayout()
        title_label = QLabel("")
        title_font = QFont()
        title_font.setPointSize(30)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; margin-bottom: 8px;")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("⚡ Merge your docking score with the smiles")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #27ae60; font-size: 12pt; margin-bottom: 25px;")
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)
        
        upload_group = QGroupBox("File Upload & Column Selection")
        upload_layout = QGridLayout()
        upload_layout.setSpacing(20)
        
        docking_label = QLabel("1. Docking Scores File:")
        docking_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12pt;")
        upload_layout.addWidget(docking_label, 0, 0)
        
        self.docking_upload = PerfectFileUploadWidget("docking", "Docking Scores CSV", ["docking_score", "ligand_title"])
        self.docking_upload.file_uploaded.connect(self.on_file_uploaded)
        upload_layout.addWidget(self.docking_upload, 1, 0)
        
        smiles_label = QLabel("2. SMILES File:")
        smiles_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 12pt;")
        upload_layout.addWidget(smiles_label, 0, 1)
        
        self.smiles_upload = PerfectFileUploadWidget("smiles", "SMILES CSV", ["smiles_string", "ligand_title"])
        self.smiles_upload.file_uploaded.connect(self.on_file_uploaded)
        upload_layout.addWidget(self.smiles_upload, 1, 1)
        
        upload_group.setLayout(upload_layout)
        main_layout.addWidget(upload_group)
        
        output_group = QGroupBox("Output Configuration")
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output File:"))
        self.output_file_edit = QLineEdit("docking_with_smiles.csv")
        output_layout.addWidget(self.output_file_edit)
        self.browse_output_btn = QPushButton("Browse")
        self.browse_output_btn.clicked.connect(self.browse_output_file)
        output_layout.addWidget(self.browse_output_btn)
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.merge_btn = QPushButton("🚀 Merge")
        self.merge_btn.clicked.connect(self.start_merge)
        self.merge_btn.setEnabled(False)
        self.merge_btn.setStyleSheet("QPushButton { background-color: #27ae60; padding: 15px 30px; font-size: 14pt; } QPushButton:hover { background-color: #229954; } QPushButton:pressed { background-color: #1e8449; }")
        button_layout.addWidget(self.merge_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self.stop_merge)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("🗑️ Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)
        
        button_layout.addStretch()
        main_layout.addLayout(button_layout)
        
        progress_group = QGroupBox("Progress & System Monitoring")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready for Merged Docking Scores and SMILES csv File...")
        self.status_label.setStyleSheet("color: #7f8c8d; font-size: 11pt;")
        progress_layout.addWidget(self.status_label)
        
        system_layout = QHBoxLayout()
        self.memory_label = QLabel("")
        self.memory_label.setStyleSheet("color: #8e44ad; font-size: 10pt;")
        system_layout.addWidget(self.memory_label)
        
        self.cpu_label = QLabel("")
        self.cpu_label.setStyleSheet("color: #e67e22; font-size: 10pt;")
        system_layout.addWidget(self.cpu_label)
        
        system_layout.addStretch()
        progress_layout.addLayout(system_layout)
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # --- PROPERLY PLACED RESULTS & PREVIEW TABLE SECTION ---
        results_group = QGroupBox("Results & Data Preview")
        
        # Tell the group box to aggressively expand vertically
        results_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setMaximumHeight(90) # Reduced from 150 so it doesn't steal space from the table
        self.results_text.setPlaceholderText("Merge results will appear here...")
        results_layout.addWidget(self.results_text)
        
        self.preview_table = QTableWidget()
        self.preview_table.setVisible(False)
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Ensure the table expands to fill all available space
        self.preview_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        self.preview_table.setStyleSheet("""
            QTableWidget { border: 1px solid #d0d0d0; border-radius: 4px; background-color: white; margin-top: 5px; }
            QHeaderView::section { background-color: #e3f2fd; padding: 6px; border: 1px solid #d0d0d0; font-weight: bold; color: #2c3e50; }
        """)
        results_layout.addWidget(self.preview_table)
        
        results_group.setLayout(results_layout)
        main_layout.addWidget(results_group)
        
        # Tell the main layout to give ALL leftover vertical space to the results_group
        main_layout.setStretchFactor(results_group, 1)
        # -------------------------------------------------------
        
        self.setLayout(main_layout)
        
    def show_csv_preview(self):
        try:
            preview_df = pd.read_csv(self.output_file_path, nrows=100)
            self.preview_table.setRowCount(len(preview_df.index))
            self.preview_table.setColumnCount(len(preview_df.columns))
            self.preview_table.setHorizontalHeaderLabels(preview_df.columns)
            
            for i in range(len(preview_df.index)):
                for j in range(len(preview_df.columns)):
                    item = QTableWidgetItem(str(preview_df.iat[i, j]))
                    self.preview_table.setItem(i, j, item)
            
            self.preview_table.resizeColumnsToContents()
            self.preview_table.setVisible(True)
            self.results_text.append("\n📊 Showing preview of the first 100 rows below.")
        except Exception as e:
            self.results_text.append(f"\n❌ Could not load preview: {str(e)}")
            
    def on_file_uploaded(self, file_path, file_type, selected_columns):
        if file_type == "docking":
            self.docking_file_path = file_path
            self.docking_cols = selected_columns
        elif file_type == "smiles":
            self.smiles_file_path = file_path
            self.smiles_cols = selected_columns
        self.check_ready_to_merge()
        
    def browse_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Merged File As", "docking_with_smiles.csv", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            self.output_file_path = file_path
            self.output_file_edit.setText(file_path)
            
    def check_ready_to_merge(self):
        ready = bool(self.docking_file_path and self.smiles_file_path and self.docking_cols and self.smiles_cols)
        self.merge_btn.setEnabled(ready)
        
        if ready:
            self.status_label.setText("✅ Ready for perfect merge with visible dropdown selections!")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 11pt; font-weight: bold;")
        else:
            missing = []
            if not self.docking_file_path: missing.append("docking scores")
            if not self.smiles_file_path: missing.append("SMILES")
            self.status_label.setText(f"⏳ Please upload {' and '.join(missing)} file(s) and select columns...")
            self.status_label.setStyleSheet("color: #f39c12; font-size: 11pt;")
            
    def clear_all(self):
        if self.worker and self.worker.isRunning():
            self.stop_merge()
            
        self.docking_file_path = ""
        self.smiles_file_path = ""
        self.docking_cols = {}
        self.smiles_cols = {}
        
        self.docking_upload.clear_file()
        self.smiles_upload.clear_file()
        self.output_file_edit.setText("docking_with_smiles.csv")
        self.results_text.clear()
        
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        self.preview_table.setVisible(False)
        
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.memory_label.setText("")
        self.cpu_label.setText("")
        self.check_ready_to_merge()
        
    def start_merge(self):
        if not all([self.docking_file_path, self.smiles_file_path, self.docking_cols, self.smiles_cols]):
            QMessageBox.warning(self, "Warning", "Please upload all required files and select columns.")
            return
            
        output_file = self.output_file_edit.text().strip()
        if not output_file: output_file = "docking_with_smiles.csv"
        if not os.path.isabs(output_file): output_file = os.path.join(os.getcwd(), output_file)
        self.output_file_path = output_file
        
        self.merge_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.clear_btn.setEnabled(False)
        self.docking_upload.setEnabled(False)
        self.smiles_upload.setEnabled(False)
        self.browse_output_btn.setEnabled(False)
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.results_text.clear()
        self.memory_label.setText("")
        self.cpu_label.setText("")
        
        chunk_size = 100000
        
        self.worker = OptimizedCSVMergerWorker(
            self.docking_file_path, self.smiles_file_path, self.output_file_path,
            self.docking_cols, self.smiles_cols, chunk_size
        )
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.memory_updated.connect(self.memory_label.setText)
        self.worker.cpu_updated.connect(self.cpu_label.setText)
        self.worker.finished.connect(self.merge_finished)
        self.worker.start()
        
    def stop_merge(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
            if self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
            
            self.status_label.setText("❌ Perfect merge stopped by user")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11pt; font-weight: bold;")
            
            self.merge_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.clear_btn.setEnabled(True)
            self.docking_upload.setEnabled(True)
            self.smiles_upload.setEnabled(True)
            self.browse_output_btn.setEnabled(True)
            
    def merge_finished(self, success, message):
        self.merge_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.clear_btn.setEnabled(True)
        self.docking_upload.setEnabled(True)
        self.smiles_upload.setEnabled(True)
        self.browse_output_btn.setEnabled(True)
        
        if success:
            self.results_text.setPlainText(message)
            self.status_label.setText("✅ Perfect merge completed successfully!")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 11pt; font-weight: bold;")
            
            self.show_csv_preview()
            
            QMessageBox.information(self, "Success", "Files merged successfully!\n\nCheck the Results section for details.")
        else:
            self.results_text.setPlainText(f"❌ Error: {message}")
            self.status_label.setText("❌ Perfect merge failed!")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11pt; font-weight: bold;")
            QMessageBox.critical(self, "Error", message)
            
        QTimer.singleShot(3000, lambda: self.progress_bar.setVisible(False))

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Perfect Multi-Core CSV Merger")
    app.setApplicationVersion("5.1")
    app.setOrganizationName("CSV Tools")
    
    window = FinalPerfectCSVMergerGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()