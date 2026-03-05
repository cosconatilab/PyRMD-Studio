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
# COMPLETE ORIGINAL CODE FOR RMD ANALYSIS MODULE WITH ENHANCED INTERACTIVITY AND STATISTICS
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


if __name__ == "__main__":
    main()

