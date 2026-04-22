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
# COMPLETE ORIGINAL CODE FOR COMPOUND ANALYZER MODAL
# ============================================================================
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


def main():
    """Main function"""
    # Parse arguments
    args = parse_arguments()

    # Create application
    app = QApplication(sys.argv)

    # Create main window
    window = CompoundAnalyzer(
        input_file=args.input,
        output_file=args.output,
        status_file=args.status,
        modal_mode=args.modal
    )

    # Show window
    window.show()

    # Run application
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


