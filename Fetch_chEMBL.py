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
# COMPLETE ORIGINAL CODE FOR FETCHING ChEMBL DATA, INCLUDING COMPOUND/TARGET DETECTION, PAGINATION HANDLING, ERROR MANAGEMENT, AND FORMATTING
# ============================================================================
import requests
import json
import os
import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QMessageBox,
    QFileDialog, QProgressBar, QTableWidget, QTableWidgetItem,
    QTabWidget, QFrame, QSplitter, QScrollArea, QGroupBox,
    QCheckBox, QDialog, QDialogButtonBox, QRadioButton, QButtonGroup
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon

# --- ChEMBL API Handler Functions ---

def detect_chembl_id_type(chembl_id):
    """
    Detect whether a ChEMBL ID is a compound/molecule or target.
    
    Args:
        chembl_id (str): The ChEMBL ID to check
    
    Returns:
        str: 'molecule', 'target', or 'unknown'
    """
    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    
    # First try as molecule
    try:
        response = requests.get(f"{base_url}/molecule/{chembl_id}.json", timeout=10)
        if response.status_code == 200:
            return 'molecule'
    except:
        pass
    
    # Then try as target
    try:
        response = requests.get(f"{base_url}/target/{chembl_id}.json", timeout=10)
        if response.status_code == 200:
            return 'target'
    except:
        pass
    
    return 'unknown'

def get_chembl_compound_data(compound_chembl_id):
    """
    Fetches compound data from the ChEMBL API for a given ChEMBL compound ID.
    
    Args:
        compound_chembl_id (str): The ChEMBL ID of the compound (e.g., "CHEMBL25").
    
    Returns:
        dict or None: A dictionary containing the compound data if found,
                      otherwise None.
    """
    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    molecule_endpoint = f"{base_url}/molecule/{compound_chembl_id}.json"
    
    print(f"Attempting to fetch compound data from: {molecule_endpoint}")
    
    try:
        response = requests.get(molecule_endpoint, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data
        
    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error occurred: {http_err} (Status code: {response.status_code})"
        if response.status_code == 404:
            error_msg += "\nNo compound data found for this ChEMBL ID. Please check if the ID is correct."
        print(error_msg)
        return None
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}. Please check your internet connection.")
        return None
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}. The request took too long.")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred during the request: {req_err}")
        return None
    except json.JSONDecodeError as json_err:
        print(f"Error decoding JSON response: {json_err}. The response might not be valid JSON.")
        if response:
            print(f"Raw response: {response.text}")
        return None

def get_chembl_target_data(target_chembl_id):
    """
    Fetches target data from the ChEMBL API for a given ChEMBL target ID.
    
    Args:
        target_chembl_id (str): The ChEMBL ID of the target (e.g., "CHEMBL1898").
    
    Returns:
        dict or None: A dictionary containing the target data if found,
                      otherwise None.
    """
    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    target_endpoint = f"{base_url}/target/{target_chembl_id}.json"
    
    print(f"Attempting to fetch target data from: {target_endpoint}")
    
    try:
        response = requests.get(target_endpoint, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        return data
        
    except requests.exceptions.HTTPError as http_err:
        error_msg = f"HTTP error occurred: {http_err} (Status code: {response.status_code})"
        if response.status_code == 404:
            error_msg += "\nNo target data found for this ChEMBL ID. Please check if the ID is correct."
        print(error_msg)
        return None
    except Exception as e:
        print(f"Error fetching target data: {e}")
        return None

def fetch_all_activities_for_compound(compound_chembl_id, page_limit=1000, progress_callback=None):
    """
    Fetches all bioactivities for a given ChEMBL compound ID, handling pagination.
    
    Args:
        compound_chembl_id (str): The ChEMBL ID of the compound.
        page_limit (int): The maximum number of results per page (ChEMBL API limit is 1000).
        progress_callback (callable): A function to call with progress updates (current, total).
    
    Returns:
        list: A list of dictionaries, each representing a bioactivity record.
              Returns an empty list if no activities are found or on error.
    """
    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    activities_endpoint = f"{base_url}/activity"
    all_activities = []
    offset = 0
    total_count = 0
    first_request = True
    
    print(f"Fetching activities for compound: {compound_chembl_id}")
    
    while True:
        params = {
            'molecule_chembl_id': compound_chembl_id,
            'limit': page_limit,
            'offset': offset,
            'format': 'json'
        }
        try:
            response = requests.get(activities_endpoint, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if first_request:
                total_count = data.get('page_meta', {}).get('total_count', 0)
                print(f"Total activities expected: {total_count}")
                first_request = False
                if progress_callback:
                    progress_callback(0, total_count)
            
            activities = data.get('activities', [])
            if not activities:
                break
            
            all_activities.extend(activities)
            
            if progress_callback:
                progress_callback(len(all_activities), total_count)
            
            if len(all_activities) >= total_count:
                break
            
            offset += len(activities)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching activities: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Error decoding activities JSON: {e}")
            break
    
    return all_activities

def fetch_all_activities_for_target(target_chembl_id, page_limit=1000, progress_callback=None):
    """
    Fetches all bioactivities for a given ChEMBL target ID, handling pagination.
    
    Args:
        target_chembl_id (str): The ChEMBL ID of the target.
        page_limit (int): The maximum number of results per page (ChEMBL API limit is 1000).
        progress_callback (callable): A function to call with progress updates (current, total).
    
    Returns:
        list: A list of dictionaries, each representing a bioactivity record.
              Returns an empty list if no activities are found or on error.
    """
    base_url = "https://www.ebi.ac.uk/chembl/api/data"
    activities_endpoint = f"{base_url}/activity"
    all_activities = []
    offset = 0
    total_count = 0
    first_request = True
    
    print(f"Fetching activities for target: {target_chembl_id}")
    
    while True:
        params = {
            'target_chembl_id': target_chembl_id,
            'limit': page_limit,
            'offset': offset,
            'format': 'json'
        }
        try:
            response = requests.get(activities_endpoint, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if first_request:
                total_count = data.get('page_meta', {}).get('total_count', 0)
                print(f"Total activities expected: {total_count}")
                first_request = False
                if progress_callback:
                    progress_callback(0, total_count)
            
            activities = data.get('activities', [])
            if not activities:
                break
            
            all_activities.extend(activities)
            
            if progress_callback:
                progress_callback(len(all_activities), total_count)
            
            if len(all_activities) >= total_count:
                break
            
            offset += len(activities)
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching activities: {e}")
            break
        except json.JSONDecodeError as e:
            print(f"Error decoding activities JSON: {e}")
            break
    
    return all_activities

def normalize_chembl_id(input_id):
    """
    Normalizes ChEMBL ID input by adding 'CHEMBL' prefix if only numbers are provided.
    
    Args:
        input_id (str): User input for ChEMBL ID
    
    Returns:
        str: Normalized ChEMBL ID with proper format
    """
    input_id = input_id.strip()
    if input_id.isdigit():
        return f"CHEMBL{input_id}"
    elif input_id.upper().startswith('CHEMBL'):
        return input_id.upper()
    else:
        # Try to extract numbers if format is not standard
        import re
        numbers = re.findall(r'\d+', input_id)
        if numbers:
            return f"CHEMBL{numbers[0]}"
    return input_id.upper()

def format_compound_data_for_display(activities_list, compound_data=None):
    """
    Formats compound bioactivity data into semicolon-separated format with specified headers.
    
    Args:
        activities_list (list): List of bioactivity dictionaries
        compound_data (dict): Compound information dictionary
    
    Returns:
        str: Formatted semicolon-separated string with headers
    """
    headers = [
        "Molecule ChEMBL ID", "Molecule Name", "Molecule Max Phase", "Molecular Weight",
        "#RO5 Violations", "AlogP", "Compound Key", "Smiles", "Standard Type",
        "Standard Relation", "Standard Value", "Standard Units", "pChEMBL Value",
        "Data Validity Comment", "Comment", "Uo Units", "Ligand Efficiency BEI",
        "Ligand Efficiency LE", "Ligand Efficiency LLE", "Ligand Efficiency SEI",
        "Potential Duplicate", "Assay ChEMBL ID", "Assay Description", "Assay Type",
        "BAO Format ID", "BAO Label", "Assay Organism", "Assay Tissue ChEMBL ID",
        "Assay Tissue Name", "Assay Cell Type", "Assay Subcellular Fraction",
        "Target ChEMBL ID", "Target Name", "Target Organism", "Target Type",
        "Document ChEMBL ID", "Source ID", "Source Description", "Document Journal",
        "Document Year", "Cell ChEMBL ID"
    ]
    
    formatted_data = ";".join(headers) + "\n"
    
    for activity in activities_list:
        row_data = []
        
        # Extract data for each header
        for header in headers:
            value = ""
            
            if header == "Molecule ChEMBL ID":
                value = activity.get('molecule_chembl_id', '')
            elif header == "Molecule Name":
                value = activity.get('molecule_pref_name', '')
            elif header == "Molecule Max Phase":
                value = str(activity.get('molecule_max_phase', '')) if activity.get('molecule_max_phase') is not None else ''
            elif header == "Molecular Weight":
                value = str(activity.get('molecular_weight', '')) if activity.get('molecular_weight') is not None else ''
            elif header == "#RO5 Violations":
                value = str(activity.get('num_ro5_violations', '')) if activity.get('num_ro5_violations') is not None else ''
            elif header == "AlogP":
                value = str(activity.get('alogp', '')) if activity.get('alogp') is not None else ''
            elif header == "Compound Key":
                value = activity.get('compound_key', '')
            elif header == "Smiles":
                value = activity.get('canonical_smiles', '')
            elif header == "Standard Type":
                value = activity.get('standard_type', '')
            elif header == "Standard Relation":
                value = activity.get('standard_relation', '')
            elif header == "Standard Value":
                value = str(activity.get('standard_value', '')) if activity.get('standard_value') is not None else ''
            elif header == "Standard Units":
                value = activity.get('standard_units', '')
            elif header == "pChEMBL Value":
                value = str(activity.get('pchembl_value', '')) if activity.get('pchembl_value') is not None else ''
            elif header == "Data Validity Comment":
                value = activity.get('data_validity_comment', '')
            elif header == "Comment":
                value = activity.get('activity_comment', '')
            elif header == "Uo Units":
                value = activity.get('uo_units', '')
            elif header == "Ligand Efficiency BEI":
                value = str(activity.get('ligand_efficiency', {}).get('bei', '')) if activity.get('ligand_efficiency') else ''
            elif header == "Ligand Efficiency LE":
                value = str(activity.get('ligand_efficiency', {}).get('le', '')) if activity.get('ligand_efficiency') else ''
            elif header == "Ligand Efficiency LLE":
                value = str(activity.get('ligand_efficiency', {}).get('lle', '')) if activity.get('ligand_efficiency') else ''
            elif header == "Ligand Efficiency SEI":
                value = str(activity.get('ligand_efficiency', {}).get('sei', '')) if activity.get('ligand_efficiency') else ''
            elif header == "Potential Duplicate":
                value = str(activity.get('potential_duplicate', '')) if activity.get('potential_duplicate') is not None else ''
            elif header == "Assay ChEMBL ID":
                value = activity.get('assay_chembl_id', '')
            elif header == "Assay Description":
                value = activity.get('assay_description', '')
            elif header == "Assay Type":
                value = activity.get('assay_type', '')
            elif header == "BAO Format ID":
                value = activity.get('bao_format', '')
            elif header == "BAO Label":
                value = activity.get('bao_label', '')
            elif header == "Assay Organism":
                value = activity.get('assay_organism', '')
            elif header == "Assay Tissue ChEMBL ID":
                value = activity.get('assay_tissue_chembl_id', '')
            elif header == "Assay Tissue Name":
                value = activity.get('assay_tissue_name', '')
            elif header == "Assay Cell Type":
                value = activity.get('assay_cell_type', '')
            elif header == "Assay Subcellular Fraction":
                value = activity.get('assay_subcellular_fraction', '')
            elif header == "Target ChEMBL ID":
                value = activity.get('target_chembl_id', '')
            elif header == "Target Name":
                value = activity.get('target_pref_name', '')
            elif header == "Target Organism":
                value = activity.get('target_organism', '')
            elif header == "Target Type":
                value = activity.get('target_type', '')
            elif header == "Document ChEMBL ID":
                value = activity.get('document_chembl_id', '')
            elif header == "Source ID":
                value = str(activity.get('src_id', '')) if activity.get('src_id') is not None else ''
            elif header == "Source Description":
                value = activity.get('src_description', '')
            elif header == "Document Journal":
                value = activity.get('document_journal', '')
            elif header == "Document Year":
                value = str(activity.get('document_year', '')) if activity.get('document_year') is not None else ''
            elif header == "Cell ChEMBL ID":
                value = activity.get('cell_chembl_id', '')
            
            # Clean the value and escape semicolons
            value = str(value).replace(';', ',').replace('\n', ' ').replace('\r', ' ')
            row_data.append(value)
        
        formatted_data += ";".join(row_data) + "\n"
    
    return formatted_data

# --- Worker Thread for Long-Running Operations ---

class ActivityFetcherWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, int)
    
    def __init__(self, chembl_id, id_type):
        super().__init__()
        self.chembl_id = chembl_id
        self.id_type = id_type
    
    def run(self):
        try:
            if self.id_type == 'molecule':
                activities = fetch_all_activities_for_compound(
                    self.chembl_id,
                    progress_callback=self.progress.emit
                )
            elif self.id_type == 'target':
                activities = fetch_all_activities_for_target(
                    self.chembl_id,
                    progress_callback=self.progress.emit
                )
            else:
                self.error.emit(f"Unknown ID type: {self.id_type}")
                return
            
            self.finished.emit(activities)
        except Exception as e:
            self.error.emit(f"An unexpected error occurred during activity fetch: {e}")

# --- Custom Dialog for Data Saving Prompt ---

class DataSaveDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Save Raw Data")
        self.setFixedSize(450, 180)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Question label
        question_label = QLabel("Do you wish to save the raw bioactivity data (CSV format) to a file?")
        question_label.setWordWrap(True)
        question_label.setStyleSheet("font-size: 14px; margin: 10px; font-weight: 600;")
        layout.addWidget(question_label)
        
        # Info label
        info_label = QLabel("• Yes: Save unformatted ChEMBL data as CSV\n• No: Continue with formatted data display only")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 12px; margin: 5px 10px; color: #6c757d;")
        layout.addWidget(info_label)
        
        # Button box
        button_box = QDialogButtonBox(QDialogButtonBox.Yes | QDialogButtonBox.No)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

# --- Main PyQt5 Desktop Application Class ---

class ChEMBLDataFetcherDialog(QDialog):
    def __init__(self, parent=None, auto_chembl_id=None):
        super().__init__(parent)
        self.setWindowTitle("ChEMBL Data Fetcher")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_modern_style()
        self.init_ui()
        
        self.current_entity_data = None
        self.current_activities_data = []
        self.current_id_type = None
        self.activity_fetcher_thread = None
        self.saved_file_path = None  # To store the path of the saved file
        self.fetched_entity_name = ""
        self.fetched_activity_count = 0

        if auto_chembl_id:
            self.id_input.setText(auto_chembl_id)
            # Use a QTimer to delay the fetch_data call slightly,
            # allowing the dialog to fully render first.
            QTimer.singleShot(100, self.fetch_data)
    
    def setup_modern_style(self):
        """Apply modern styling to the application."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f8f9fa;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
            }
            
            QLabel {
                color: #2c3e50;
                font-weight: 500;
            }
            
            QLineEdit {
                padding: 12px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                background-color: white;
                font-size: 14px;
                color: #495057;
            }
            
            QLineEdit:focus {
                border-color: #007bff;
                outline: none;
            }
            
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                min-width: 120px;
            }
            
            QPushButton:hover {
                background-color: #0056b3;
            }
            
            QPushButton:pressed {
                background-color: #004085;
            }
            
            QPushButton:disabled {
                background-color: #6c757d;
                color: #adb5bd;
            }
            
            QTextEdit {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                background-color: white;
                padding: 12px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                line-height: 1.4;
            }
            
            QTableWidget {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                background-color: white;
                gridline-color: #dee2e6;
                selection-background-color: #e3f2fd;
            }
            
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976d2;
            }
            
            QHeaderView::section {
                background-color: #f8f9fa;
                color: #495057;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #dee2e6;
                font-weight: 600;
            }
            
            QProgressBar {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                text-align: center;
                background-color: #f8f9fa;
            }
            
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 6px;
            }
            
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                color: #495057;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px 0 8px;
                background-color: #f8f9fa;
            }
            
            QTabWidget::pane {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                background-color: white;
            }
            
            QTabBar::tab {
                background-color: #f8f9fa;
                color: #6c757d;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            
            QTabBar::tab:selected {
                background-color: white;
                color: #007bff;
                border-bottom: 2px solid #007bff;
            }
            
            QTabBar::tab:hover {
                background-color: #e9ecef;
                color: #495057;
            }
        """)
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel("ChEMBL Data Fetcher")
        title_label.setStyleSheet("""
            font-size: 28px;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Fetch bioactivity data for ChEMBL compounds and targets")
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            color: #6c757d;
            margin-bottom: 20px;
        """)
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)
        
        # Input section
        input_group = QGroupBox("ChEMBL ID Input")
        input_layout = QVBoxLayout()
        
        id_layout = QHBoxLayout()
        id_label = QLabel("ChEMBL ID:")
        id_label.setStyleSheet("font-size: 14px; font-weight: 600; margin-right: 10px;")
        
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("Enter ChEMBL ID (e.g., CHEMBL1898, CHEMBL25, or just 1898)")
        self.id_input.returnPressed.connect(self.fetch_data)
        
        id_layout.addWidget(id_label)
        id_layout.addWidget(self.id_input, 1)
        
        input_layout.addLayout(id_layout)
        
        
        
        # Fetch button
        self.fetch_button = QPushButton("Fetch Data")
        self.fetch_button.clicked.connect(self.fetch_data)
        self.fetch_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                font-size: 16px;
                padding: 15px 30px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        input_layout.addWidget(self.fetch_button)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 14px; color: #007bff; font-weight: 600;")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Fetching Data: %p%")
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Results section with tabs - REORDERED: Table View first
        self.results_tabs = QTabWidget()
        
        # Table view tab - FIRST TAB
        self.table_widget = QTableWidget()
        self.results_tabs.addTab(self.table_widget, "Table View")
        
        # Formatted data tab - SECOND TAB
        self.formatted_display = QTextEdit()
        self.formatted_display.setReadOnly(True)
        self.formatted_display.setPlaceholderText("Formatted bioactivity data will appear here...")
        self.results_tabs.addTab(self.formatted_display, "Formatted Data")
        
        # Raw data tab - THIRD TAB
        self.raw_display = QTextEdit()
        self.raw_display.setReadOnly(True)
        self.raw_display.setPlaceholderText("Raw JSON data will appear here...")
        self.results_tabs.addTab(self.raw_display, "Raw Data")
        
        main_layout.addWidget(self.results_tabs, 1)
        
        # Action buttons
        button_group = QGroupBox("Actions")
        button_layout = QHBoxLayout()
        
        self.save_raw_button = QPushButton("Save Raw Data (CSV)")
        self.save_raw_button.clicked.connect(self.save_raw_data)
        self.save_raw_button.setEnabled(False)
        self.save_raw_button.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        
        self.save_formatted_button = QPushButton("Save Formatted Data")
        self.save_formatted_button.clicked.connect(self.save_formatted_data)
        self.save_formatted_button.setEnabled(False)
        self.save_formatted_button.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
            }
            QPushButton:hover {
                background-color: #e0a800;
            }
        """)

        self.load_button = QPushButton("Load Saved Data")
        self.load_button.clicked.connect(self.load_saved_data)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        
        button_layout.addWidget(self.load_button)
        button_layout.addWidget(self.save_raw_button)
        button_layout.addWidget(self.save_formatted_button)
        button_layout.addStretch()
        
        button_group.setLayout(button_layout)
        main_layout.addWidget(button_group)
        
        self.setLayout(main_layout)
    
    def update_status(self, message):
        """Helper to update status label."""
        self.status_label.setText(message)
        QApplication.processEvents()
    
    def fetch_data(self):
        """Main function to fetch ChEMBL data."""
        input_id = self.id_input.text().strip()
        if not input_id:
            QMessageBox.warning(self, "Input Error", "Please enter a ChEMBL ID.")
            return
        
        # Normalize the ChEMBL ID
        chembl_id = normalize_chembl_id(input_id)
        self.id_input.setText(chembl_id)  # Update the input field with normalized ID
        
        self.update_status(f"Detecting ID type for '{chembl_id}'...")
        self.fetch_button.setEnabled(False)
        self.save_raw_button.setEnabled(False)
        self.save_formatted_button.setEnabled(False)
        
        # Clear previous data
        self.current_entity_data = None
        self.current_activities_data = []
        self.current_id_type = None
        self.raw_display.clear()
        self.table_widget.clear()
        self.formatted_display.clear()
        
        # Detect ID type
        id_type = detect_chembl_id_type(chembl_id)
        
        if id_type == 'unknown':
            self.update_status(f"❌ ChEMBL ID '{chembl_id}' not found")
            QMessageBox.critical(self, "Error", f"ChEMBL ID '{chembl_id}' was not found as either a compound or target.\nPlease check the ID and try again.")
            self.fetch_button.setEnabled(True)
            return
        
        self.current_id_type = id_type
        
        if id_type == 'molecule':
            self.update_status(f"✓ Detected as compound. Fetching compound data...")
            entity_data = get_chembl_compound_data(chembl_id)
            entity_name = entity_data.get('pref_name', 'Unknown') if entity_data else 'Unknown'
            # For compounds, show basic info
            status_info = f"✓ Found compound: {entity_name}"
        else:  # target
            self.update_status(f"✓ Detected as target. Fetching target data...")
            entity_data = get_chembl_target_data(chembl_id)
            entity_name = entity_data.get('pref_name', 'Unknown') if entity_data else 'Unknown'
            entity_organism = entity_data.get('organism', 'Unknown') if entity_data else 'Unknown'
            # For targets, show name AND organism
            status_info = f"✓ Found target: {entity_name} ({entity_organism})"
        
        if entity_data:
            self.current_entity_data = entity_data
            self.raw_display.setText(json.dumps(entity_data, indent=2, ensure_ascii=False))
            
            # Now fetch bioactivities
            self.update_status(f"{status_info}. Fetching bioactivities...")
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)
            
            # Start fetching activities in a new thread
            self.activity_fetcher_thread = ActivityFetcherWorker(chembl_id, id_type)
            self.activity_fetcher_thread.finished.connect(self.on_activities_fetched)
            self.activity_fetcher_thread.error.connect(self.on_activities_error)
            self.activity_fetcher_thread.progress.connect(self.update_activity_progress)
            self.activity_fetcher_thread.start()
        else:
            self.update_status(f"❌ Failed to fetch {id_type} data")
            QMessageBox.critical(self, "Error", f"Failed to fetch {id_type} data for '{chembl_id}'.")
            self.fetch_button.setEnabled(True)
    
    def update_activity_progress(self, current, total):
        """Updates the progress bar during activity fetching."""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_bar.setFormat(f"Fetching Activities: {current}/{total} ({percentage}%)")
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Fetching Activities: 0/0 (0%)")
    
    def on_activities_fetched(self, activities_list):
        """Callback when activity fetching is complete."""
        self.progress_bar.setVisible(False)
        self.fetch_button.setEnabled(True)
        
        if activities_list:
            self.current_activities_data = activities_list
            
            entity_name = self.current_entity_data.get('pref_name', 'Unknown') if self.current_entity_data else 'Unknown'
            if self.current_id_type == 'target':
                entity_organism = self.current_entity_data.get('organism', 'Unknown') if self.current_entity_data else 'Unknown'
                self.update_status(f"✓ Found {len(activities_list)} bioactivities for {entity_name} ({entity_organism})")
            else:
                self.update_status(f"✓ Found {len(activities_list)} bioactivities for {entity_name}")

            self.fetched_entity_name = entity_name
            self.fetched_activity_count = len(activities_list)
            
            # Ask user if they want to save raw data
            self.prompt_save_raw_data()
            
            # Always display formatted data
            self.display_formatted_data()
            
            QMessageBox.information(self, "Success", f"Fetched {len(activities_list)} bioactivities!")
        else:
            self.update_status("❌ No bioactivities found")
            QMessageBox.information(self, "No Activities", "No bioactivities were found for the specified ID.")
    
    def on_activities_error(self, error_message):
        """Callback for errors during activity fetching."""
        self.progress_bar.setVisible(False)
        self.fetch_button.setEnabled(True)
        self.current_activities_data = []
        self.update_status(f"❌ Error fetching activities")
        QMessageBox.critical(self, "Error", f"An error occurred while fetching bioactivities: {error_message}")
    
    def prompt_save_raw_data(self):
        """Prompt user to save raw data."""
        dialog = DataSaveDialog(self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            self.save_raw_data()
    
    def display_formatted_data(self):
        """Display formatted compound data."""
        if not self.current_activities_data:
            return
        
        # Format data for display
        formatted_text = format_compound_data_for_display(
            self.current_activities_data, 
            self.current_entity_data
        )
        
        self.formatted_display.setText(formatted_text)
        self.save_formatted_button.setEnabled(True)
        
        # Also populate table view
        self.populate_table_view(formatted_text)
    
    def populate_table_view(self, formatted_text):
        """Populate the table widget with formatted data."""
        lines = formatted_text.strip().split('\n')
        if len(lines) < 2:
            return
        
        headers = lines[0].split(';')
        data_lines = lines[1:]
        
        self.table_widget.setRowCount(len(data_lines))
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        
        for row, line in enumerate(data_lines):
            values = line.split(';')
            for col, value in enumerate(values):
                if col < len(headers):
                    item = QTableWidgetItem(value)
                    self.table_widget.setItem(row, col, item)
        
        # Resize columns to content
        self.table_widget.resizeColumnsToContents()
    
    def save_raw_data(self):
        """Save raw CSV data to file (unformatted ChEMBL data)."""
        if not self.current_activities_data:
            QMessageBox.warning(self, "No Data", "No data to save.")
            return
        
        entity_id = self.current_entity_data.get('molecule_chembl_id', 'unknown') if self.current_entity_data else 'unknown'
        if not entity_id or entity_id == 'unknown':
            entity_id = self.current_entity_data.get('target_chembl_id', 'unknown') if self.current_entity_data else 'unknown'
        
        default_filename = f"{entity_id}_raw_bioactivities.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Raw Bioactivity Data (CSV)",
            os.path.join(os.getcwd(), default_filename),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            try:
                # Convert raw activities to DataFrame and save as CSV
                activities_df = pd.DataFrame(self.current_activities_data)
                activities_df.to_csv(file_path, index=False, encoding='utf-8')
                QMessageBox.information(self, "Success", f"Raw bioactivity data saved to:\n{file_path}")
                self.save_raw_button.setEnabled(True)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save raw data:\n{str(e)}")
    
    def save_formatted_data(self):
        """Save formatted data to file."""
        if not self.current_activities_data:
            QMessageBox.warning(self, "No Data", "No formatted data to save.")
            return
        
        entity_id = self.current_entity_data.get('molecule_chembl_id', 'unknown') if self.current_entity_data else 'unknown'
        if not entity_id or entity_id == 'unknown':
            entity_id = self.current_entity_data.get('target_chembl_id', 'unknown') if self.current_entity_data else 'unknown'
        
        default_filename = f"{entity_id}_formatted_data.csv"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Formatted Data",
            os.path.join(os.getcwd(), default_filename),
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                formatted_text = self.formatted_display.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted_text)
                self.saved_file_path = file_path
                QMessageBox.information(self, "Success", f"Formatted data saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save formatted data:\n{str(e)}")

    def load_saved_data(self):
        """Load a previously saved ChEMBL data file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load ChEMBL Data File",
            os.getcwd(),
            "CSV Files (*.csv);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            # Signal to parent that a file should be loaded
            self.saved_file_path = file_path
            self.accept()  # Close dialog and return Accepted

# --- Main Application Execution ---

if __name__ == "__main__":
    try:
        import requests
        import pandas as pd
        from PyQt5 import QtWidgets, QtCore
    except ImportError as e:
        print(f"Error: Required library not found - {e}")
        print("Please install them using pip:")
        print("pip install requests PyQt5 pandas")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("ChEMBL Data Fetcher")
    app.setApplicationVersion("2.2")
    app.setOrganizationName("ChEMBL Tools")
    
    window = ChEMBLDataFetcherDialog()
    window.show()
    
    sys.exit(app.exec_())

