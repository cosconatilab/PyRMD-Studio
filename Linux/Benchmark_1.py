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
# COMPLETE ORIGINAL BENCHMARK CODE FOR FETCHING AND DISPLAYING ChEMBL DATA IN A PYQT5 APPLICATION
# ============================================================================
import subprocess
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QCheckBox, QButtonGroup, QRadioButton, QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel, QLineEdit, QWidget, QComboBox, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget, QFrame, QSplitter, QScrollArea, QGroupBox, QProgressBar, QDialogButtonBox
import configparser
import os
import time
import multiprocessing
import threading
import requests
import json
import sys
import pandas as pd
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor, QPixmap, QIcon
from Fetch_chEMBL import ChEMBLDataFetcherDialog

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

class ChEMBLDataFetcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ChEMBL Data Fetcher")
        self.setGeometry(100, 100, 1200, 800)
        self.setup_modern_style()
        self.init_ui()
        
        self.current_entity_data = None
        self.current_activities_data = []
        self.current_id_type = None
        self.activity_fetcher_thread = None
    
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
        
        button_layout.addWidget(self.save_raw_button)
        button_layout.addWidget(self.save_formatted_button)
        button_layout.addStretch()
        
        button_group.setLayout(button_layout)
        main_layout.addWidget(button_group)
        
        self.setLayout(main_layout)
    
    def update_status(self, message):
        """Helper to update status label."""
        self.status_label.setText(message)
        QtWidgets.QApplication.processEvents()
    
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

class CPUSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CPU Core Selection")
        self.setModal(True)
        self.resize(400, 200)
        
        # Get total CPU cores
        self.total_cores = multiprocessing.cpu_count()
        self.selected_cores = self.total_cores
        
        layout = QVBoxLayout(self)
        
        # Information label
        info_label = QLabel(f"Total CPU cores available: {self.total_cores}")
        info_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(info_label)
        
        # Radio button group for selection type
        self.radio_all_cores = QRadioButton("Use all available cores")
        self.radio_all_cores.setChecked(True)
        self.radio_custom_cores = QRadioButton("Specify number of cores:")
        
        layout.addWidget(self.radio_all_cores)
        layout.addWidget(self.radio_custom_cores)
        
        # Spinbox for custom core selection
        cores_layout = QHBoxLayout()
        self.spinbox_cores = QSpinBox()
        self.spinbox_cores.setMinimum(1)
        self.spinbox_cores.setMaximum(self.total_cores)
        self.spinbox_cores.setValue(self.total_cores)
        self.spinbox_cores.setEnabled(False)
        
        cores_layout.addWidget(QLabel("Number of cores:"))
        cores_layout.addWidget(self.spinbox_cores)
        cores_layout.addStretch()
        
        cores_widget = QWidget()
        cores_widget.setLayout(cores_layout)
        layout.addWidget(cores_widget)
        
        # Connect radio buttons
        self.radio_all_cores.toggled.connect(self._on_radio_toggled)
        self.radio_custom_cores.toggled.connect(self._on_radio_toggled)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Now")
        self.cancel_button = QPushButton("Cancel")
        
        self.run_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.run_button)
        
        layout.addLayout(button_layout)
    
    def _on_radio_toggled(self):
        """Handle radio button toggle"""
        self.spinbox_cores.setEnabled(self.radio_custom_cores.isChecked())
    
    def get_selected_cores(self):
        """Get the number of selected cores"""
        if self.radio_all_cores.isChecked():
            return self.total_cores
        else:
            return self.spinbox_cores.value()

class BenchmarkResultsDialog(QDialog):
    def __init__(self, file_path, selected_module="PyRMD", screening_launcher=None, parent=None):
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
        QTimer.singleShot(0, lambda params=model_params, launch=launcher: launch(params))

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

        # Prefer explicit per-row plot paths stored in CSV
        header_to_column = {}
        for column_index in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(column_index)
            if header_item is not None:
                header_to_column[header_item.text().strip().lower()] = column_index

        csv_plot_paths = []
        for key in ["roc_curve_file", "prc_curve_file", "roc_plot_file", "prc_plot_file"]:
            if key in header_to_column:
                table_column = header_to_column[key]
                if table_column > 0:  # column 0 is the button column
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

            path_in_working_dir = os.path.abspath(candidate_name)
            if os.path.exists(path_in_working_dir) and path_in_working_dir not in existing_paths:
                existing_paths.append(path_in_working_dir)

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
        self.setAlignment(Qt.AlignCenter)

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
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
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
            splitter = QSplitter(Qt.Horizontal)
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

                image_pixmap = QPixmap(plot_path)
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
                placeholder.setAlignment(Qt.AlignCenter)
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

class BenchmarkWorker(QtCore.QThread):
    """Worker thread for running benchmark process"""
    finished = QtCore.pyqtSignal(bool, str)  # success, message
    
    def __init__(self, cores):
        super().__init__()
        self.cores = cores
    
    def run(self):
        try:
            # Set environment variable for number of cores if needed
            env = os.environ.copy()
            env['OMP_NUM_THREADS'] = str(self.cores)
            env['NUMBA_NUM_THREADS'] = str(self.cores)
            
            # Run the launch.sh script
            result = subprocess.run(['bash', 'launch.sh'], 
                                  capture_output=True, 
                                  text=True, 
                                  cwd=os.getcwd(),
                                  env=env)
            
            if result.returncode == 0:
                self.finished.emit(True, "Benchmark process completed successfully!")
            else:
                self.finished.emit(False, f"Benchmark process failed:\n{result.stderr}")
                
        except FileNotFoundError:
            self.finished.emit(False, "launch.sh script not found. Please ensure the script exists in the current directory.")
        except Exception as e:
            self.finished.emit(False, f"Failed to run benchmark: {str(e)}")

class Ui_Benchmark(object):
    def setupUi(self, Benchmark, selected_module="PyRMD"):
        Benchmark.setObjectName("Benchmark")
        self.selected_module = selected_module
        Benchmark.setWindowTitle(f"Benchmarking - {self.selected_module}")
        
        # Initialize file paths and epsilon values
        self.file_path_smi_file = ""
        self.file_path_chembl = ""
        self.decoys_file_path = ""
        self.actives_file_path = ""
        self.inactives_file_path = ""
        self.benchmark_output_directory = ""
        self.active_epsilon_values = []
        self.inactive_epsilon_values = []
        self.benchmark_worker = None
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
        self._benchmark_finalize_timer = QTimer(Benchmark)
        self._benchmark_finalize_timer.setInterval(1000)
        self._benchmark_finalize_timer.timeout.connect(self._poll_benchmark_results_completion)
        
        # Define default values for reset functionality
        self.default_values = {
            'output_file': 'Benchmark_Results.csv',
            'use_chembl': False,
            'fp_type': 'mhfp',
            'fp_size': '1024',
            'fp_radius': '3',
            'activity_threshold': '1001',
            'inactivity_threshold': '39999',
            'n_splits': '5',
            'n_repeats': '3',
            'butina_cutoff': '0.7',
            'beta': '1',
            'alpha': '20',
            'active_single': '0.95',
            'inactive_single': '0.95'
        }
        
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
        self.lineEdit_program_mode.setText("Ligand-Based Virtual Screening (LBVS), Benchmarking")
        self.lineEdit_program_mode.setReadOnly(True)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_program_mode)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_program_mode)
        current_row += 1
        self.all_parameter_widgets.append((self.label_program_mode, "always"))
        self.all_parameter_widgets.append((self.lineEdit_program_mode, "always"))
        
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
        self.lineEdit_output_file.setText(self.default_values['output_file'])
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
        
        self.checkBox_use_chembl = QCheckBox("Use ChEMBL Dataset")
        self.checkBox_use_chembl.setChecked(self.default_values['use_chembl'])
        self.checkBox_use_chembl.setToolTip("Check this box to use the ChEMBL dataset for training.")
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
        
        # ChEMBL ID Fetching Interface
        self.label_chembl_fetch = QtWidgets.QLabel("Fetch from ChEMBL ID:")
        chembl_fetch_layout = QHBoxLayout()
        self.lineEdit_chembl_id = QLineEdit()
        self.lineEdit_chembl_id.setPlaceholderText("Enter ChEMBL ID (e.g., CHEMBL1898, CHEMBL25)")
        self.pushButton_chembl_fetch = QPushButton("Fetch")
        self.pushButton_chembl_fetch.clicked.connect(self.fetch_chembl_data)
        
        # Initially disable the Fetch button
        self.pushButton_chembl_fetch.setEnabled(False)
        
        # Connect text change event to enable/disable Fetch button
        self.lineEdit_chembl_id.textChanged.connect(self._on_chembl_id_text_changed)
        
        # Connect Enter key press to fetch data
        self.lineEdit_chembl_id.returnPressed.connect(self.fetch_chembl_data)
        
        chembl_fetch_layout.addWidget(self.lineEdit_chembl_id)
        chembl_fetch_layout.addWidget(self.pushButton_chembl_fetch)
        chembl_fetch_container = QWidget()
        chembl_fetch_container.setLayout(chembl_fetch_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_chembl_fetch)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, chembl_fetch_container)
        current_row += 1
        self.all_parameter_widgets.append((self.label_chembl_fetch, "beginner"))
        self.all_parameter_widgets.append((chembl_fetch_container, "beginner"))

        self.label_chembl_fetch_summary = QtWidgets.QLabel("No ChEMBL data fetched yet")
        self.label_chembl_fetch_summary.setStyleSheet(
            "background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 6px; "
            "padding: 8px 10px; color: #495057; font-size: 11px;"
        )
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.label_chembl_fetch_summary)
        current_row += 1
        self.all_parameter_widgets.append((self.label_chembl_fetch_summary, "beginner"))
        
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
        self.comboBox_fp_type.setCurrentText(self.default_values['fp_type'])
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_fp_type)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.comboBox_fp_type)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fp_type, "expert"))
        self.all_parameter_widgets.append((self.comboBox_fp_type, "expert"))
        
        self.label_fp_size = QtWidgets.QLabel("Fingerprint Size:")
        self.lineEdit_fp_size = QLineEdit()
        self.lineEdit_fp_size.setText(self.default_values['fp_size'])
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_fp_size)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_fp_size)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fp_size, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_fp_size, "expert"))
        
        self.label_fp_radius = QtWidgets.QLabel("Fingerprint Radius/Iterations:")
        self.lineEdit_fp_radius = QLineEdit()
        self.lineEdit_fp_radius.setText(self.default_values['fp_radius'])
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_fp_radius)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_fp_radius)
        current_row += 1
        self.all_parameter_widgets.append((self.label_fp_radius, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_fp_radius, "expert"))
        # --- START ADDED CODE: Expert Fingerprint Options ---
        
        # Explicit Hydrogens
        self.checkBox_explicit_H = QCheckBox("Explicit Hydrogens")
        self.checkBox_explicit_H.setChecked(True) # Default: True
        self.checkBox_explicit_H.setToolTip("Include explicit hydrogens in the fingerprint.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_explicit_H)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_explicit_H, "expert"))

        # Chirality
        self.checkBox_chirality = QCheckBox("Include Chirality")
        self.checkBox_chirality.setChecked(False) # Default: False
        self.checkBox_chirality.setToolTip("Include chirality in ECFP/MHFP fingerprints.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_chirality)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_chirality, "expert"))

        # Redundancy (ECFP specific)
        self.checkBox_redundancy = QCheckBox("Redundancy (ECFP)")
        self.checkBox_redundancy.setChecked(True) # Default: True
        self.checkBox_redundancy.setToolTip("Include redundancy for ECFP fingerprints.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_redundancy)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_redundancy, "expert"))

        # Features (ECFP specific)
        self.checkBox_features = QCheckBox("Features (ECFP)")
        self.checkBox_features.setChecked(False) # Default: False
        self.checkBox_features.setToolTip("Use features for ECFP fingerprints.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, self.checkBox_features)
        current_row += 1
        self.all_parameter_widgets.append((self.checkBox_features, "expert"))

        # --- END ADDED CODE ---
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
        self.lineEdit_active_single.setText(self.default_values['active_single'])
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
        self.lineEdit_inactive_single.setText(self.default_values['inactive_single'])
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
        self.lineEdit_beta.setText(self.default_values['beta'])
        self.lineEdit_beta.setToolTip("Enter the beta value for statistical calculations.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_beta)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_beta)
        current_row += 1
        self.all_parameter_widgets.append((self.label_beta, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_beta, "expert"))
        
        self.label_alpha = QtWidgets.QLabel("Alpha:")
        self.lineEdit_alpha = QLineEdit()
        self.lineEdit_alpha.setText(self.default_values['alpha'])
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
        self.lineEdit_n_splits.setText(self.default_values['n_splits'])
        self.lineEdit_n_splits.setToolTip("Enter the number of splits for K-Fold cross-validation.")
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.LabelRole, self.label_n_splits)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.FieldRole, self.lineEdit_n_splits)
        current_row += 1
        self.all_parameter_widgets.append((self.label_n_splits, "expert"))
        self.all_parameter_widgets.append((self.lineEdit_n_splits, "expert"))
        
        self.label_n_repeats = QtWidgets.QLabel("N Repeats:")
        self.lineEdit_n_repeats = QLineEdit()
        self.lineEdit_n_repeats.setText(self.default_values['n_repeats'])
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
        self.lineEdit_activity_threshold.setText(self.default_values['activity_threshold'])
        self.lineEdit_activity_threshold.setToolTip("Enter the activity threshold for ChEMBL compounds.")
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
        self.lineEdit_inactivity_threshold.setText(self.default_values['inactivity_threshold'])
        self.lineEdit_inactivity_threshold.setToolTip("Enter the inactivity threshold for ChEMBL compounds.")
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
        
        inhibition_layout.addWidget(QLabel("Inactive <"))
        inhibition_layout.addWidget(self.lineEdit_inhibition_inactive)
        inhibition_layout.addWidget(QLabel("%"))
        inhibition_layout.addStretch() # Adds space to the right to keep it tidy
        # --- MODIFIED LAYOUT ENDS HERE ---

        inhibition_container = QWidget()
        inhibition_container.setLayout(inhibition_layout)
        self.formLayout.setWidget(current_row, QtWidgets.QFormLayout.SpanningRole, inhibition_container)
        current_row += 1

        self.all_parameter_widgets.append((inhibition_container, "inhibition"))
        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        self.pushButton_update_config = QPushButton("Update Configuration")
        self.pushButton_update_config.setToolTip("Update the configuration file with the current settings.")
        self.pushButton_update_config.clicked.connect(self.update_ini_file)
        button_layout.addWidget(self.pushButton_update_config)
        
        self.pushButton_run_benchmark = QPushButton("Run Benchmark")
        self.pushButton_run_benchmark.setToolTip("Run the benchmark process with the current settings.")
        self.pushButton_run_benchmark.clicked.connect(self.run_benchmark_process)
        button_layout.addWidget(self.pushButton_run_benchmark)

        self.pushButton_view_results = QPushButton("Open Results CSV")
        self.pushButton_view_results.setToolTip("Load a pre-calculated benchmark results CSV and view sortable models.")
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
        
        # Initialize UI state WITHOUT showing popups
        self._initialize_ui_silently()

        # Auto-sync configuration whenever user changes inputs
        self._connect_auto_config_update_signals()
        
        self.retranslateUi(Benchmark)
        QtCore.QMetaObject.connectSlotsByName(Benchmark)

    def _connect_auto_config_update_signals(self):
        """Connect widget signals to silently update configuration on user changes."""
        for line_edit in self.centralwidget.findChildren(QLineEdit):
            line_edit.editingFinished.connect(self._update_config_silently)

        for combo_box in self.centralwidget.findChildren(QComboBox):
            combo_box.currentTextChanged.connect(lambda _text: self._update_config_silently())

        for check_box in self.centralwidget.findChildren(QCheckBox):
            check_box.stateChanged.connect(lambda _state: self._update_config_silently())

        for radio_button in self.centralwidget.findChildren(QRadioButton):
            radio_button.toggled.connect(lambda _checked: self._update_config_silently())

    def _initialize_ui_silently(self):
        """Initialize UI state without showing any popups"""
        # Set default fingerprint settings
        self._update_fingerprint_settings()
        
        # Update parameter visibility
        self._update_parameter_visibility()
        
        # Toggle training uploads
        self._toggle_training_uploads()
        
        # Toggle epsilon UI
        self._toggle_active_epsilon_ui()
        self._toggle_inactive_epsilon_ui()
        self._toggle_inhibition_thresholds()

    def _save_epsilon_values_to_files(self):
        """Save epsilon values to text files with two decimal places formatting"""
        try:
            # Get current epsilon values
            active_values = self._get_current_active_epsilon_values()
            inactive_values = self._get_current_inactive_epsilon_values()
            
            # Save active epsilon values to tc_actives.txt
            if active_values:
                with open('tc_actives.txt', 'w') as f:
                    for value in active_values:
                        f.write(f"{value:.2f}\n")
            
            # Save inactive epsilon values to tc_inactives.txt
            if inactive_values:
                with open('tc_inactives.txt', 'w') as f:
                    for value in inactive_values:
                        f.write(f"{value:.2f}\n")
                        
            return True
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to save epsilon values: {str(e)}")
            return False

    def _get_current_active_epsilon_values(self):
        """Get current active epsilon values based on selection"""
        values = []
        
        if self.radio_active_single.isChecked():
            try:
                value = float(self.lineEdit_active_single.text())
                values = [value]
            except ValueError:
                pass
        elif self.radio_active_range.isChecked():
            try:
                min_val = float(self.lineEdit_active_min.text())
                max_val = float(self.lineEdit_active_max.text())
                step = float(self.lineEdit_active_step.text())
                
                if min_val < max_val and step > 0:
                    current = min_val
                    while current <= max_val:
                        values.append(round(current, 3))
                        current += step
            except ValueError:
                pass
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
                pass
        
        # Use stored values if available
        if self.active_epsilon_values:
            values = self.active_epsilon_values
            
        return values

    def _get_current_inactive_epsilon_values(self):
        """Get current inactive epsilon values based on selection"""
        values = []
        
        if self.radio_inactive_single.isChecked():
            try:
                value = float(self.lineEdit_inactive_single.text())
                values = [value]
            except ValueError:
                pass
        elif self.radio_inactive_range.isChecked():
            try:
                min_val = float(self.lineEdit_inactive_min.text())
                max_val = float(self.lineEdit_inactive_max.text())
                step = float(self.lineEdit_inactive_step.text())
                
                if min_val < max_val and step > 0:
                    current = min_val
                    while current <= max_val:
                        values.append(round(current, 3))
                        current += step
            except ValueError:
                pass
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
                pass
        
        # Use stored values if available
        if self.inactive_epsilon_values:
            values = self.inactive_epsilon_values
            
        return values

    def _toggle_training_uploads(self):
        """Toggle visibility of training dataset upload options"""
        use_chembl = self.checkBox_use_chembl.isChecked()
        
        # Show ChEMBL-specific controls only when using ChEMBL
        self.label_chembl_file.setVisible(use_chembl)
        self.lineEdit_chembl_file.parentWidget().setVisible(use_chembl)
        self.label_chembl_fetch.setVisible(use_chembl)
        self.lineEdit_chembl_id.parentWidget().setVisible(use_chembl)
        self.label_chembl_fetch_summary.setVisible(use_chembl)
        
        # Keep active/inactive uploads visible in both modes
        self.label_actives_file.setVisible(True)
        self.lineEdit_actives_file.parentWidget().setVisible(True)
        self.label_inactives_file.setVisible(True)
        self.lineEdit_inactives_file.parentWidget().setVisible(True)

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
        
    def _toggle_inhibition_thresholds(self):
        """Show or hide inhibition threshold fields based on checkbox"""
        enabled = self.checkBox_use_inhibition.isChecked()
        for widget, visibility in self.all_parameter_widgets:
            if visibility == "inhibition":
                widget.setVisible(enabled)


    def _preview_active_epsilon_values(self):
        """Preview and edit active epsilon values, and save to file"""
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
                # Save epsilon values to files
                self._save_epsilon_values_to_files()
                QMessageBox.information(self.centralwidget, "Values Updated", f"Active epsilon values updated: {len(self.active_epsilon_values)} values selected and saved to tc_actives.txt.")

    def _preview_inactive_epsilon_values(self):
        """Preview and edit inactive epsilon values, and save to file"""
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
                # Save epsilon values to files
                self._save_epsilon_values_to_files()
                QMessageBox.information(self.centralwidget, "Values Updated", f"Inactive epsilon values updated: {len(self.inactive_epsilon_values)} values selected and saved to tc_inactives.txt.")

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
            self.benchmark_output_directory = directory
            self.lineEdit_output_dir.setText(directory)

    def _on_chembl_id_text_changed(self, text):
        """Enable/disable Fetch button based on ChEMBL ID input"""
        self.pushButton_chembl_fetch.setEnabled(bool(text.strip()))

    def fetch_chembl_data(self):
        """Open ChEMBL Data Fetcher dialog to fetch data from ChEMBL ID"""
        try:
            # Get the ChEMBL ID from the input field
            chembl_id = self.lineEdit_chembl_id.text().strip()
            
            # Validate that a ChEMBL ID is entered
            if not chembl_id:
                QMessageBox.warning(
                    self.centralwidget,
                    "Input Required",
                    "Please enter a ChEMBL ID before clicking Fetch.\n\nExample: CHEMBL2787 or just 2787"
                )
                return
            
            # Normalize the ChEMBL ID
            normalized_id = normalize_chembl_id(chembl_id)
            
            # Open dialog with the ChEMBL ID pre-filled and auto-execute
            dialog = ChEMBLDataFetcherDialog(self.centralwidget, auto_chembl_id=normalized_id)
            result = dialog.exec_()

            if getattr(dialog, 'fetched_activity_count', 0) > 0:
                entity_name = getattr(dialog, 'fetched_entity_name', '').strip() or "Unknown Target"
                count = dialog.fetched_activity_count
                self.label_chembl_fetch_summary.setText(f"Target: {entity_name} | Activities fetched: {count}")
                self.label_chembl_fetch_summary.setStyleSheet(
                    "background-color: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 6px; "
                    "padding: 8px 10px; color: #2e7d32; font-size: 11px; font-weight: 600;"
                )
            
            if dialog.saved_file_path:
                self.load_chembl_data_file(dialog.saved_file_path)

            if result == QDialog.Rejected and not dialog.saved_file_path and getattr(dialog, 'fetched_activity_count', 0) > 0:
                self.label_chembl_fetch_summary.setText(
                    "Data fetched. Use 'Save Formatted Data' in the ChEMBL dialog to auto-load into this pipeline."
                )
                self.label_chembl_fetch_summary.setStyleSheet(
                    "background-color: #fff8e1; border: 1px solid #ffecb3; border-radius: 6px; "
                    "padding: 8px 10px; color: #8d6e63; font-size: 11px;"
                )
                    
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to open ChEMBL Data Fetcher: {str(e)}")

    def load_chembl_data_file(self, file_path):
        try:
            if file_path and os.path.exists(file_path):
                # Set the ChEMBL file path
                self.file_path_chembl = file_path
                self.lineEdit_chembl_file.setText(file_path)

                self._update_chembl_fetch_summary_from_file(file_path)
                
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

    def _update_chembl_fetch_summary_from_file(self, file_path):
        try:
            data_frame = pd.read_csv(file_path, sep=';', engine='python')
            activity_count = len(data_frame)

            target_name = "Unknown"
            for column_name in ["Target Name", "target_name", "Molecule Name", "molecule_pref_name"]:
                if column_name in data_frame.columns and not data_frame[column_name].dropna().empty:
                    target_name = str(data_frame[column_name].dropna().iloc[0]).strip()
                    if target_name:
                        break

            self.label_chembl_fetch_summary.setText(
                f"Target: {target_name} | Activities fetched: {activity_count}"
            )
            self.label_chembl_fetch_summary.setStyleSheet(
                "background-color: #e3f2fd; border: 1px solid #bbdefb; border-radius: 6px; "
                "padding: 8px 10px; color: #1565c0; font-size: 11px; font-weight: 600;"
            )
        except Exception:
            self.label_chembl_fetch_summary.setText("Target: Unknown | Activities fetched: Unknown")
            self.label_chembl_fetch_summary.setStyleSheet(
                "background-color: #fff8e1; border: 1px solid #ffecb3; border-radius: 6px; "
                "padding: 8px 10px; color: #8d6e63; font-size: 11px;"
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
            # Save epsilon values to files first
            self._save_epsilon_values_to_files()
            
            # Create configuration file
            config = configparser.ConfigParser()
            
            # Add all sections
            config.add_section('MODE')
            config.add_section('TRAINING_DATASETS')
            config.add_section('FINGERPRINTS')
            config.add_section('DECOYS')
            config.add_section('CHEMBL_INHIBITION_THRESHOLDS')
            config.add_section('CHEMBL_ACTIVITY_THRESHOLDS')
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
            
            # Set benchmark_file based on output directory and filename
            output_dir = self.lineEdit_output_dir.text() or '.'
            output_file = self.lineEdit_output_file.text() or 'benchmark_results.csv'
            benchmark_file_path = os.path.join(output_dir, output_file)
            config.set('MODE', 'benchmark_file', benchmark_file_path)
            
            # TRAINING_DATASETS section
            use_chembl = self.checkBox_use_chembl.isChecked()
            config.set('TRAINING_DATASETS', 'use_chembl', str(use_chembl))
            config.set('TRAINING_DATASETS', 'chembl_file', self.lineEdit_chembl_file.text() if use_chembl else '')
            config.set('TRAINING_DATASETS', 'use_actives', str(not use_chembl))
            config.set('TRAINING_DATASETS', 'actives_file', self.lineEdit_actives_file.text() if not use_chembl else '')
            config.set('TRAINING_DATASETS', 'use_inactives', str(not use_chembl))
            config.set('TRAINING_DATASETS', 'inactives_file', self.lineEdit_inactives_file.text() if not use_chembl else '')
            
            # FINGERPRINTS section
            config.set('FINGERPRINTS', 'fp_type', self.comboBox_fp_type.currentText())
            config.set('FINGERPRINTS', 'nbits', self.lineEdit_fp_size.text())
            
            # --- MODIFIED: Read from new checkboxes ---
            config.set('FINGERPRINTS', 'explicit_hydrogens', str(self.checkBox_explicit_H.isChecked()))
            config.set('FINGERPRINTS', 'iterations', self.lineEdit_fp_radius.text())
            config.set('FINGERPRINTS', 'chirality', str(self.checkBox_chirality.isChecked()))
            config.set('FINGERPRINTS', 'redundancy', str(self.checkBox_redundancy.isChecked()))
            config.set('FINGERPRINTS', 'features', str(self.checkBox_features.isChecked()))
            # ------------------------------------------
            
            # DECOYS section
            decoys_file = self.lineEdit_decoys_file.text()
            config.set('DECOYS', 'use_decoys', str(bool(decoys_file)))
            config.set('DECOYS', 'decoys_file', decoys_file)
            config.set('DECOYS', 'sample_number', '1000000')
            
            # CHEMBL ACTIVITY THRESHOLDS
            config.set('CHEMBL_ACTIVITY_THRESHOLDS', 'activity_threshold', self.lineEdit_activity_threshold.text())
            config.set('CHEMBL_ACTIVITY_THRESHOLDS', 'inactivity_threshold', self.lineEdit_inactivity_threshold.text())

            # CHEMBL INHIBITION THRESHOLDS
            use_inhibition = self.checkBox_use_inhibition.isChecked()
            config.set('CHEMBL_INHIBITION_THRESHOLDS', 'chembl_inhibition_rate', str(use_inhibition).lower())

            if use_inhibition:
                config.set('CHEMBL_INHIBITION_THRESHOLDS', 'inhibition_inactivity_threshold', self.lineEdit_inhibition_inactive.text())
                config.set('CHEMBL_INHIBITION_THRESHOLDS', 'inhibition_activity_threshold', '0')
            
            # KFOLD PARAMETERS section
            config.set('KFOLD_PARAMETERS', 'n_splits', self.lineEdit_n_splits.text())
            config.set('KFOLD_PARAMETERS', 'n_repeats', self.lineEdit_n_repeats.text())
            
            # TRAINING PARAMETERS section
            active_val = "XXXX"  # Placeholder - actual values saved to tc_actives.txt
            inactive_val = "YYYY"  # Placeholder - actual values saved to tc_inactives.txt
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_actives', active_val)
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_inactives', inactive_val)
            
            # CLUSTERING section
            butina_cutoff_val = self.lineEdit_bu.text().strip()
            config.set('CLUSTERING', 'butina_cutoff', butina_cutoff_val)
            
            
            # STAT PARAMETERS section
            config.set('STAT_PARAMETERS', 'beta', self.lineEdit_beta.text())
            config.set('STAT_PARAMETERS', 'alpha', self.lineEdit_alpha.text())
            
            # FILTER section
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
            
            QMessageBox.information(self.centralwidget, "Success", "Configuration file updated successfully!")
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to update configuration: {str(e)}")

    def run_benchmark_process(self):
        """Run the benchmark process with CPU selection dialog"""
        try:
            # Ensure latest user-edited values are written before launching benchmark
            if not self._update_config_silently():
                QMessageBox.critical(
                    self.centralwidget,
                    "Configuration Error",
                    "Failed to apply current values to configuration file. Please check inputs and try again."
                )
                return

            # Show CPU selection dialog
            cpu_dialog = CPUSelectionDialog(self.centralwidget)
            if cpu_dialog.exec_() != QDialog.Accepted:
                return  # User cancelled
            
            selected_cores = cpu_dialog.get_selected_cores()

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
            
            # Disable the run button to prevent multiple runs
            self.pushButton_run_benchmark.setEnabled(False)
            self.pushButton_run_benchmark.setText("Running...")
            
            # Create and start worker thread
            self.benchmark_worker = BenchmarkWorker(selected_cores)
            self.benchmark_worker.finished.connect(self._on_benchmark_finished)
            self.benchmark_worker.start()
            
            # Show initial message
            QMessageBox.information(self.centralwidget, "Benchmark Started", 
                                  f"Benchmark process started using {selected_cores} CPU cores.\nThe process is running in the background.")
                
        except Exception as e:
            self.pushButton_run_benchmark.setEnabled(True)
            self.pushButton_run_benchmark.setText("Run Benchmark")
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to start benchmark: {str(e)}")

    def _on_benchmark_finished(self, success, message):
        """Handle benchmark completion"""
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
            QMessageBox.critical(self.centralwidget, "Process Failed", message)
            self._reset_benchmark_completion_state()
        
        # Clean up worker
        if self.benchmark_worker:
            self.benchmark_worker.deleteLater()
            self.benchmark_worker = None

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
                "Process Done",
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

    def _get_benchmark_results_path(self):
        output_dir = self.lineEdit_output_dir.text().strip() or '.'
        output_file = self.lineEdit_output_file.text().strip() or 'benchmark_results.csv'
        return os.path.abspath(os.path.join(output_dir, output_file))

    def _get_expected_benchmark_combinations(self):
        active_values = self._get_current_active_epsilon_values()
        inactive_values = self._get_current_inactive_epsilon_values()

        active_file_count = self._count_non_empty_lines('tc_actives.txt')
        inactive_file_count = self._count_non_empty_lines('tc_inactives.txt')

        if active_file_count > 0:
            active_count = active_file_count
        else:
            active_count = max(1, len(active_values))

        if inactive_file_count > 0:
            inactive_count = inactive_file_count
        else:
            inactive_count = max(1, len(inactive_values))

        return active_count * inactive_count

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

    def _get_results_row_count(self, file_path):
        try:
            if not os.path.exists(file_path):
                return 0

            data_frame = self._read_results_dataframe(file_path)
            return len(data_frame.index)
        except Exception:
            return 0

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

    def _wait_for_benchmark_results_ready(self, target_rows, timeout_seconds=180):
        results_file_path = self._benchmark_results_file_path or self._get_benchmark_results_path()
        start_time = time.time()
        stable_hits = 0
        previous_size = -1
        rows_found = 0

        while (time.time() - start_time) < timeout_seconds:
            if os.path.exists(results_file_path):
                try:
                    current_size = os.path.getsize(results_file_path)
                    if current_size > 0:
                        data_frame = self._read_results_dataframe(results_file_path)
                        rows_found = len(data_frame.index)

                        if rows_found >= target_rows:
                            if current_size == previous_size:
                                stable_hits += 1
                            else:
                                stable_hits = 0

                            previous_size = current_size

                            if stable_hits >= 1:
                                return True, results_file_path, rows_found
                except Exception:
                    pass

            time.sleep(1)

        return False, results_file_path, rows_found

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

    def _launch_screening_from_model_parameters(self, model_params):
        try:
            if self.selected_module == "PyRMD2Dock":
                from Screening_2 import UnifiedTabApplication as ScreeningModule
            else:
                from Screening import UnifiedTabApplication as ScreeningModule

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

    def open_precalculated_results_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self.centralwidget,
            "Open Benchmark Results File",
            self.lineEdit_output_dir.text().strip() or os.getcwd(),
            "CSV Files (*.csv);;All Files (*)"
        )

        if file_path:
            self._show_benchmark_results_window(file_path)

    def load_default_values(self):
        """Load default values into the form and update configuration file"""
        try:
            # Reset GUI elements to default values
            self.lineEdit_output_file.setText(self.default_values['output_file'])
            self.checkBox_use_chembl.setChecked(self.default_values['use_chembl'])
            self.comboBox_fp_type.setCurrentText(self.default_values['fp_type'])
            self.lineEdit_fp_size.setText(self.default_values['fp_size'])
            self.lineEdit_fp_radius.setText(self.default_values['fp_radius'])
            # --- ADDED: Reset new checkboxes ---
            self.checkBox_explicit_H.setChecked(True)
            self.checkBox_chirality.setChecked(False)
            self.checkBox_redundancy.setChecked(True)
            self.checkBox_features.setChecked(False)
            # -----------------------------------
            self.lineEdit_activity_threshold.setText(self.default_values['activity_threshold'])
            self.lineEdit_inactivity_threshold.setText(self.default_values['inactivity_threshold'])
            
            # --- MODIFIED SECTION ---
            # Use specific values here instead of looking up non-existent keys
            self.checkBox_use_inhibition.setChecked(False) 
            self.lineEdit_inhibition_inactive.setText("11")
            # ------------------------

            self.lineEdit_n_splits.setText(self.default_values['n_splits'])
            self.lineEdit_n_repeats.setText(self.default_values['n_repeats'])
            self.lineEdit_beta.setText(self.default_values['beta'])
            self.lineEdit_alpha.setText(self.default_values['alpha'])
            self.lineEdit_active_single.setText(self.default_values['active_single'])
            self.lineEdit_inactive_single.setText(self.default_values['inactive_single'])
            
            # Reset radio buttons to default states
            self.radio_active_single.setChecked(True)
            self.radio_inactive_single.setChecked(True)
            self.radio_fp_balanced.setChecked(True)
            
            # Clear file paths
            self.lineEdit_chembl_file.clear()
            self.lineEdit_actives_file.clear()
            self.lineEdit_inactives_file.clear()
            self.lineEdit_decoys_file.clear()
            self.lineEdit_output_dir.clear()
            
            # Clear range and manual fields
            self.lineEdit_active_min.clear()
            self.lineEdit_active_max.clear()
            self.lineEdit_active_step.clear()
            self.lineEdit_active_manual.clear()
            self.lineEdit_inactive_min.clear()
            self.lineEdit_inactive_max.clear()
            self.lineEdit_inactive_step.clear()
            self.lineEdit_inactive_manual.clear()
            
            # Clear stored epsilon values
            self.active_epsilon_values = []
            self.inactive_epsilon_values = []
            
            # Update fingerprint settings based on default selection
            self._update_fingerprint_settings()
            
            # Update configuration file with defaults (silently)
            self._update_config_silently()
            
            QMessageBox.information(self.centralwidget, "Reset Complete", 
                                  "All values have been reset to defaults and configuration file updated.")
            
        except Exception as e:
            QMessageBox.critical(self.centralwidget, "Error", f"Failed to reset to defaults: {str(e)}")

    def _update_config_silently(self):
        """Update configuration file without showing popup"""
        try:
            # Save epsilon values to files first
            self._save_epsilon_values_to_files()
            
            # Create configuration file
            config = configparser.ConfigParser()
            
            # Add all sections
            config.add_section('MODE')
            config.add_section('TRAINING_DATASETS')
            config.add_section('FINGERPRINTS')
            config.add_section('DECOYS')
            config.add_section('CHEMBL_INHIBITION_THRESHOLDS')
            config.add_section('CHEMBL_ACTIVITY_THRESHOLDS')
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
            
            # Set benchmark_file based on output directory and filename
            output_dir = self.lineEdit_output_dir.text() or '.'
            output_file = self.lineEdit_output_file.text() or 'benchmark_results.csv'
            benchmark_file_path = os.path.join(output_dir, output_file)
            config.set('MODE', 'benchmark_file', benchmark_file_path)
            
            # TRAINING_DATASETS section
            use_chembl = self.checkBox_use_chembl.isChecked()
            config.set('TRAINING_DATASETS', 'use_chembl', str(use_chembl))
            config.set('TRAINING_DATASETS', 'chembl_file', self.lineEdit_chembl_file.text() if use_chembl else '')
            config.set('TRAINING_DATASETS', 'use_actives', str(not use_chembl))
            config.set('TRAINING_DATASETS', 'actives_file', self.lineEdit_actives_file.text() if not use_chembl else '')
            config.set('TRAINING_DATASETS', 'use_inactives', str(not use_chembl))
            config.set('TRAINING_DATASETS', 'inactives_file', self.lineEdit_inactives_file.text() if not use_chembl else '')
            
            # FINGERPRINTS section
            config.set('FINGERPRINTS', 'fp_type', self.comboBox_fp_type.currentText())
            config.set('FINGERPRINTS', 'nbits', self.lineEdit_fp_size.text())
            config.set('FINGERPRINTS', 'explicit_hydrogens', str(self.checkBox_explicit_H.isChecked()))
            config.set('FINGERPRINTS', 'iterations', self.lineEdit_fp_radius.text())
            config.set('FINGERPRINTS', 'chirality', str(self.checkBox_chirality.isChecked()))
            config.set('FINGERPRINTS', 'redundancy', str(self.checkBox_redundancy.isChecked()))
            config.set('FINGERPRINTS', 'features', str(self.checkBox_features.isChecked()))
            
            # DECOYS section
            decoys_file = self.lineEdit_decoys_file.text()
            config.set('DECOYS', 'use_decoys', str(bool(decoys_file)))
            config.set('DECOYS', 'decoys_file', decoys_file)
            config.set('DECOYS', 'sample_number', '1000000')
            
            # CHEMBL ACTIVITY THRESHOLDS
            config.set('CHEMBL_ACTIVITY_THRESHOLDS', 'activity_threshold', self.lineEdit_activity_threshold.text())
            config.set('CHEMBL_ACTIVITY_THRESHOLDS', 'inactivity_threshold', self.lineEdit_inactivity_threshold.text())

            # CHEMBL INHIBITION THRESHOLDS
            use_inhibition = self.checkBox_use_inhibition.isChecked()
            config.set('CHEMBL_INHIBITION_THRESHOLDS', 'chembl_inhibition_rate', str(use_inhibition).lower())

            if use_inhibition:
                config.set('CHEMBL_INHIBITION_THRESHOLDS', 'inhibition_inactivity_threshold', self.lineEdit_inhibition_inactive.text())
                config.set('CHEMBL_INHIBITION_THRESHOLDS', 'inhibition_activity_threshold', '0')
            
            # KFOLD PARAMETERS section
            config.set('KFOLD_PARAMETERS', 'n_splits', self.lineEdit_n_splits.text())
            config.set('KFOLD_PARAMETERS', 'n_repeats', self.lineEdit_n_repeats.text())
            
            # TRAINING PARAMETERS section
            active_val = "XXXX"  # Placeholder - actual values saved to tc_actives.txt
            inactive_val = "YYYY"  # Placeholder - actual values saved to tc_inactives.txt
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_actives', active_val)
            config.set('TRAINING_PARAMETERS', 'epsilon_cutoff_inactives', inactive_val)
            
            # CLUSTERING section
            butina_cutoff_val = self.lineEdit_bu.text().strip()
            config.set('CLUSTERING', 'butina_cutoff', butina_cutoff_val)

            # STAT PARAMETERS section
            config.set('STAT_PARAMETERS', 'beta', self.lineEdit_beta.text())
            config.set('STAT_PARAMETERS', 'alpha', self.lineEdit_alpha.text())
            
            # FILTER section
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

            return True
            
        except Exception as e:
            # Silently fail during background updates, caller may handle return value
            return False

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


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    BenchmarkWindow = QtWidgets.QMainWindow()
    ui = Ui_Benchmark()
    ui.setupUi(BenchmarkWindow)
    BenchmarkWindow.show()
    sys.exit(app.exec_())

