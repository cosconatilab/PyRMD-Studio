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
# COMPLETE ORIGINAL HOMEPAGE.PY
# ============================================================================
# -*- coding: utf-8 -*-

import sys
import subprocess
import os

# --- FIX 1: Suppress MESA/ZINK/GLX errors ---
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

# --- FIX 2: Suppress GTK/Qt Logging noise ---
os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty, QTimer, QRect, QParallelAnimationGroup, QSequentialAnimationGroup, QPoint
from PyQt5.QtWidgets import QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QPushButton, QDialog, QVBoxLayout, QLabel, QHBoxLayout, QMessageBox, QLineEdit
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QCursor
import random
import math
import webbrowser
import warnings

# Suppress Python warnings
warnings.filterwarnings("ignore")

# ------------------- Citation Dialog -------------------
class CitationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("How to Cite")
        self.setFixedSize(450, 300)

        layout = QVBoxLayout()

        # First citation
        citation1 = """Amendola, Giorgio, and Sandro Cosconati.
        "PyRMD: a new fully automated AI-powered ligand-based virtual screening tool."
        Journal of Chemical Information and Modeling
        61.8 (2021): 3835-3845."""

        layout.addWidget(QLabel("<b>Publication 1:</b>"))
        self.add_citation_block(layout, citation1, "https://pubs.acs.org/doi/full/10.1021/acs.jcim.1c00653")

        # Second citation
        citation2 = """Roggia, Michele, et al.
        "Streamlining large chemical library docking with artificial intelligence: the PyRMD2Dock approach."
        Journal of chemical information and modeling
        64.7 (2023): 2143-2149."""

        layout.addWidget(QLabel("<b>Publication 2:</b>"))
        self.add_citation_block(layout, citation2, "https://pubs.acs.org/doi/full/10.1021/acs.jcim.3c00647")

        self.setLayout(layout)

    def add_citation_block(self, layout, citation_text, link):
        citation_label = QLabel(citation_text)
        citation_label.setWordWrap(True)
        layout.addWidget(citation_label)

        btn_layout = QHBoxLayout()

        copy_btn = QPushButton("Copy Citation")
        copy_btn.clicked.connect(lambda: self.copy_to_clipboard(citation_text))
        btn_layout.addWidget(copy_btn)

        layout.addLayout(btn_layout)

    def copy_to_clipboard(self, text):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(text)
        QtWidgets.QMessageBox.information(self, "Copied", "Citation copied to clipboard!")

    def safe_open_url(self, url):
        """
        Opens URL handling both WSL and Native Ubuntu seamlessly.
        """
        try:
            # 1. Detect WSL (Windows Subsystem for Linux)
            is_wsl = False
            if sys.platform.startswith('linux'):
                try:
                    if 'microsoft' in os.uname().release.lower():
                        is_wsl = True
                except:
                    pass

            # --- CASE A: WSL (Open Windows Browser) ---
            if is_wsl:
                try:
                    # Try using 'wslview' (part of wslu utility)
                    subprocess.Popen(['wslview', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except FileNotFoundError:
                    # Fallback to direct Windows command
                    subprocess.Popen(['cmd.exe', '/C', 'start', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return

            # --- CASE B: Native Linux (Ubuntu/Debian) ---
            if sys.platform.startswith('linux'):
                # We use xdg-open but redirect stderr to DEVNULL to silence Snap warnings
                subprocess.Popen(['xdg-open', url], 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
            
            # --- CASE C: macOS ---
            elif sys.platform == 'darwin': 
                subprocess.Popen(['open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # --- CASE D: Windows Native ---
            elif sys.platform == 'win32': 
                os.startfile(url)
            
            else:
                webbrowser.open(url)

        except Exception:
            # Fallback if everything else fails
            try:
                webbrowser.open(url)
            except:
                msg = QMessageBox(self)
                msg.setWindowTitle("Link")
                msg.setText("Browser could not be opened. Link:")
                line_edit = QLineEdit(url)
                line_edit.setReadOnly(True)
                msg.layout().addWidget(line_edit)
                msg.exec_()


# ------------------- Celebration Particle -------------------
class CelebrationParticle:
    def __init__(self, x, y, color, particle_type="confetti"):
        self.x = x
        self.y = y
        self.start_x = x
        self.start_y = y
        self.color = color
        self.particle_type = particle_type
        self.velocity_x = random.uniform(-3, 3)
        self.velocity_y = random.uniform(-8, -3)
        self.gravity = 0.9
        self.rotation = random.uniform(0, 360)
        self.rotation_speed = random.uniform(-10, 10)
        self.life = 1.0
        self.fade_speed = random.uniform(0.0002, 0.0005)
        self.size = random.uniform(3, 8)

    def update(self):
        self.velocity_y += self.gravity
        self.x += self.velocity_x
        self.y += self.velocity_y
        self.rotation += self.rotation_speed
        self.life -= self.fade_speed
        return self.life > 0


class CelebrationLogoLabel(QtWidgets.QLabel):
    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.particles = []
        self.celebration_timer = QTimer()
        self.celebration_timer.timeout.connect(self.update_celebration)
        self.burst_timer = QTimer()
        self.burst_timer.timeout.connect(self.create_burst)
        self.remaining_bursts = 0
        self.original_geometry = None

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and event.modifiers() == QtCore.Qt.ControlModifier:
            if QtCore.QFile.exists("logo_2.png"):
                self.setPixmap(QtGui.QPixmap("logo_2.png"))
            self.start_celebration_animation()
        super().mousePressEvent(event)

    def start_celebration_animation(self):
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
        self.celebration_timer.stop()
        self.burst_timer.stop()
        self.particles.clear()
        self.remaining_bursts = 6
        self.burst_timer.start(100)
        self.celebration_timer.start(16)

    def create_burst(self):
        if self.remaining_bursts <= 0:
            self.burst_timer.stop()
            return
        self.remaining_bursts -= 1
        center = self.rect().center()
        logo_center_x = center.x()
        logo_center_y = center.y()
        confetti_colors = [
            QColor(255, 193, 7), QColor(233, 30, 99), QColor(156, 39, 176),
            QColor(63, 81, 181), QColor(0, 188, 212), QColor(76, 175, 80),
            QColor(255, 87, 34), QColor(255, 235, 59), QColor(255, 152, 0),
            QColor(96, 125, 139), QColor(255, 64, 129)
        ]
        for i in range(40):
            angle = (i / 40) * 2 * math.pi + random.uniform(-0.3, 0.3)
            distance = random.uniform(40, 70)
            x = logo_center_x + math.cos(angle) * distance
            y = logo_center_y + math.sin(angle) * distance
            color = random.choice(confetti_colors)
            particle_type = "ribbon" if i % 20 == 0 else "confetti"
            self.particles.append(CelebrationParticle(x, y, color, particle_type))
        self.update()

    def update_celebration(self):
        self.particles = [p for p in self.particles if p.update()]
        if not self.particles and self.remaining_bursts <= 0:
            self.celebration_timer.stop()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.particles:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            for particle in self.particles:
                color = QColor(particle.color)
                color.setAlphaF(particle.life)
                painter.save()
                painter.translate(int(particle.x), int(particle.y))
                painter.rotate(particle.rotation)
                size = int(particle.size)
                if particle.particle_type == "ribbon":
                    painter.setPen(QPen(color, 2))
                    painter.drawLine(-size, 0, size, 0)
                    painter.drawLine(0, -size // 2, 0, size // 2)
                else:
                    painter.setBrush(QBrush(color))
                    painter.setPen(QPen(color))
                    painter.drawEllipse(-size // 2, -size // 2, size, size)
                painter.restore()

    def stop_celebration(self):
        self.burst_timer.stop()
        self.celebration_timer.stop()
        self.cleanup_celebration()

    def cleanup_celebration(self):
        self.burst_timer.stop()
        self.celebration_timer.stop()
        self.particles.clear()
        self.setStyleSheet("")
        if self.original_geometry:
            self.setGeometry(self.original_geometry)
        self.update()


class FlipButton(QtWidgets.QPushButton):
    def __init__(self, text, flip_text, parent=None):
        super().__init__(text, parent)
        self.original_text = text
        self.flip_text = flip_text
        self.is_flipped = False
        self.hover_timer = QTimer()
        self.hover_timer.setSingleShot(True)
        self.hover_timer.timeout.connect(self.flip_button)
        self.flip_animation = QPropertyAnimation(self, b"geometry")
        self.flip_animation.setDuration(1000)
        self.flip_animation.setEasingCurve(QEasingCurve.OutBack)

    def enterEvent(self, event):
        super().enterEvent(event)
        if not self.is_flipped:
            self.hover_timer.start(1000)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.hover_timer.stop()
        if self.is_flipped:
            self.flip_back()

    def flip_button(self):
        if not self.is_flipped:
            self.is_flipped = True
            self.setText(self.flip_text)
            self.setStyleSheet(self.styleSheet() + """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #28a745, stop:0.5 #20c997, stop:1 #28a745) !important;
                    border: 2px solid #1e7e34 !important;
                    color: white !important;
                    font-weight: bold !important;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 #218838, stop:0.5 #1abc9c, stop:1 #218838) !important;
                }
            """)

    def flip_back(self):
        if self.is_flipped:
            self.is_flipped = False
            self.setText(self.original_text)
            if hasattr(self.parent(), 'button_style_sheet'):
                self.setStyleSheet(self.parent().button_style_sheet)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.setMinimumSize(QtCore.QSize(800, 600))

        self.current_colors = {
            'background': "#F4F6F8",
            'foreground': "#212529",
            'primary': "#007BFF",
            'accent': "#6C757D",
            'button_text': "#FFFFFF",
            'input_bg': "#FFFFFF",
            'input_text': "#495057"
        }

        self.apply_color_scheme(MainWindow)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_layout = QtWidgets.QVBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        self.main_layout.setSpacing(25)
        self.main_layout.setAlignment(QtCore.Qt.AlignTop)

        self.selected_module = None

        # --- Header Layout for Citation Button ---
        header_layout = QHBoxLayout()
        header_layout.addStretch() 
        
        self.cite_button = QPushButton("How to Cite", self.centralwidget)
        self.cite_button.setCursor(QCursor(QtCore.Qt.PointingHandCursor))
        self.cite_button.setStyleSheet("font-size: 12px; color: #007BFF; background: transparent; border: none; font-weight: bold;")
        self.cite_button.setFixedWidth(100)
        self.cite_button.clicked.connect(self.show_citation)
        
        header_layout.addWidget(self.cite_button)
        self.main_layout.addLayout(header_layout)
        # ----------------------------------------

        # Enhanced logo
        self.label_logo = CelebrationLogoLabel(self.centralwidget)
        if QtCore.QFile.exists("pyrmd_logo.png"):
            self.label_logo.setPixmap(QtGui.QPixmap("pyrmd_logo.png"))
        else:
            self.label_logo.setText("PyRMD Studio")
            self.label_logo.setStyleSheet("font-size: 40px; font-weight: bold; color: #007BFF;")

        self.label_logo.setScaledContents(True)
        self.label_logo.setFixedSize(500, 200)
        self.label_logo.setAlignment(QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(self.label_logo, 0, QtCore.Qt.AlignCenter)
        self.main_layout.addSpacerItem(QtWidgets.QSpacerItem(20, 15, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))

        self.label_title = QtWidgets.QLabel(self.centralwidget)
        font_title = QtGui.QFont("Arial", 22, QtGui.QFont.Bold)
        self.label_title.setFont(font_title)
        self.label_title.setStyleSheet(f"color: {self.current_colors['foreground']};")
        self.label_title.setAlignment(QtCore.Qt.AlignCenter)
        self.label_title.setWordWrap(True)
        self.main_layout.addWidget(self.label_title, 0, QtCore.Qt.AlignCenter)
        self.main_layout.addSpacerItem(QtWidgets.QSpacerItem(20, 25, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Fixed))

        self.update_button_styles()
        self.font_button = QtGui.QFont("Arial", 14, QtGui.QFont.Bold)
        self.font_back_button = QtGui.QFont("Arial", 10, QtGui.QFont.Bold)

        self.module_buttons_layout = QtWidgets.QHBoxLayout()
        self.module_buttons_layout.setSpacing(25)
        self.module_buttons_layout.setAlignment(QtCore.Qt.AlignCenter)

        self.pushButton_PyRMD = FlipButton("PyRMD", "LBVS", self.centralwidget)
        self.pushButton_PyRMD.setFont(self.font_button)
        self.pushButton_PyRMD.setStyleSheet(self.button_style_sheet)
        self.pushButton_PyRMD.setToolTip("Ligand-based virtual screening")
        self.module_buttons_layout.addWidget(self.pushButton_PyRMD)

        self.pushButton_PyRMD2Dock = FlipButton("PyRMD2Dock", "SBVS", self.centralwidget)
        self.pushButton_PyRMD2Dock.setFont(self.font_button)
        self.pushButton_PyRMD2Dock.setStyleSheet(self.button_style_sheet)
        self.pushButton_PyRMD2Dock.setToolTip("Structure-based virtual screening")
        self.module_buttons_layout.addWidget(self.pushButton_PyRMD2Dock)
        self.main_layout.addLayout(self.module_buttons_layout)

        self.task_buttons_layout = QtWidgets.QHBoxLayout()
        self.task_buttons_layout.setSpacing(25)
        self.task_buttons_layout.setAlignment(QtCore.Qt.AlignCenter)

        self.pushButton_Benchmark = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_Benchmark.setFont(self.font_button)
        self.pushButton_Benchmark.setStyleSheet(self.button_style_sheet)
        self.pushButton_Benchmark.setToolTip("Start benchmarking tasks")
        self.task_buttons_layout.addWidget(self.pushButton_Benchmark)

        self.pushButton_Screening = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_Screening.setFont(self.font_button)
        self.pushButton_Screening.setStyleSheet(self.button_style_sheet)
        self.pushButton_Screening.setToolTip("Start screening tasks")
        self.task_buttons_layout.addWidget(self.pushButton_Screening)
        self.main_layout.addLayout(self.task_buttons_layout)

        self.pushButton_Benchmark.setVisible(False)
        self.pushButton_Screening.setVisible(False)

        self.navigation_layout = QtWidgets.QHBoxLayout()
        self.navigation_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.pushButton_Back = QtWidgets.QPushButton(self.centralwidget)
        self.pushButton_Back.setFont(self.font_back_button)
        self.pushButton_Back.setStyleSheet(self.back_button_style_sheet)
        self.pushButton_Back.setVisible(False)
        self.navigation_layout.addWidget(self.pushButton_Back)
        self.main_layout.addLayout(self.navigation_layout)
        self.main_layout.addSpacerItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.setup_connections()
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def show_citation(self):
        dlg = CitationDialog()
        dlg.exec_()

    def apply_color_scheme(self, MainWindow):
        MainWindow.setStyleSheet(f"""
            QMainWindow {{
                background-color: {self.current_colors['background']};
                color: {self.current_colors['foreground']};
            }}
            QWidget {{
                background-color: {self.current_colors['background']};
                color: {self.current_colors['foreground']};
            }}
        """)

    def update_button_styles(self):
        self.button_style_sheet = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.current_colors['primary']}, stop:1 #0056b3);
                border: 2px solid {self.current_colors['primary']};
                border-radius: 12px;
                color: {self.current_colors['button_text']};
                font-weight: bold;
                padding: 12px 24px;
                text-align: center;
                min-width: 140px;
                min-height: 45px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0056b3, stop:1 {self.current_colors['primary']});
                border: 2px solid #0056b3;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #004085, stop:1 #0056b3);
                border: 2px solid #004085;
            }}
        """

        self.back_button_style_sheet = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.current_colors['accent']}, stop:1 #5a6268);
                border: 2px solid {self.current_colors['accent']};
                border-radius: 8px;
                color: {self.current_colors['button_text']};
                font-weight: bold;
                padding: 8px 16px;
                text-align: center;
                min-width: 80px;
                min-height: 35px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #5a6268, stop:1 {self.current_colors['accent']});
                border: 2px solid #5a6268;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #495057, stop:1 #5a6268);
                border: 2px solid #495057;
            }}
        """

    def setup_connections(self):
        self.pushButton_PyRMD.clicked.connect(lambda: self.show_task_selection("PyRMD"))
        self.pushButton_PyRMD2Dock.clicked.connect(lambda: self.show_task_selection("PyRMD2Dock"))
        self.pushButton_Benchmark.clicked.connect(self.show_benchmark_window)
        self.pushButton_Screening.clicked.connect(self.show_screening_window)
        self.pushButton_Back.clicked.connect(self.go_back_to_module_selection)

    def show_task_selection(self, module_name):
        self.selected_module = module_name
        self.label_title.setText(f"{module_name}")
        self.label_title.setAlignment(QtCore.Qt.AlignCenter)
        self.pushButton_PyRMD.setVisible(False)
        self.pushButton_PyRMD2Dock.setVisible(False)
        self.pushButton_Benchmark.setVisible(True)
        self.pushButton_Screening.setVisible(True)
        self.pushButton_Back.setVisible(True)

    def go_back_to_module_selection(self):
        self.selected_module = None
        self.label_title.setText("Select Module")
        self.label_title.setAlignment(QtCore.Qt.AlignCenter)
        self.pushButton_PyRMD.setVisible(True)
        self.pushButton_PyRMD2Dock.setVisible(True)
        self.pushButton_Benchmark.setVisible(False)
        self.pushButton_Screening.setVisible(False)
        self.pushButton_Back.setVisible(False)

    def show_benchmark_window(self):
        if not self.selected_module:
            QtWidgets.QMessageBox.warning(self.centralwidget, "Module Not Selected", "Please select PyRMD or PyRMD2Dock first.")
            return
        if self.selected_module == "PyRMD":
            from Benchmark_1 import Ui_Benchmark as BenchmarkModule
        elif self.selected_module == "PyRMD2Dock":
            from Benchmark_2 import Ui_Benchmark as BenchmarkModule
        else: return
        self.benchmark_window_instance = QtWidgets.QMainWindow()
        self.ui_benchmark = BenchmarkModule()
        self.ui_benchmark.set_color_palette(
            self.current_colors['background'],
            self.current_colors['foreground'],
            self.current_colors['primary'],
            self.current_colors['accent'],
            self.current_colors['button_text'],
            self.current_colors['input_bg'],
            self.current_colors['input_text']
        )
        self.ui_benchmark.setupUi(self.benchmark_window_instance, self.selected_module)
        self.benchmark_window_instance.show()

    def show_screening_window(self):
        if not self.selected_module:
            QtWidgets.QMessageBox.warning(self.centralwidget, "Module Not Selected", "Please select PyRMD or PyRMD2Dock first.")
            return
        if self.selected_module == "PyRMD":
            from Screening import UnifiedTabApplication as ScreeningModule
        elif self.selected_module == "PyRMD2Dock":
            from Screening_2 import UnifiedTabApplication as ScreeningModule
        else: return
        self.screening_window_instance = ScreeningModule()
        self.screening_window_instance.show()

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "PyRMD Studio"))
        self.label_title.setText(_translate("MainWindow", "Select Module"))
        self.pushButton_PyRMD.setText(_translate("MainWindow", "PyRMD"))
        self.pushButton_PyRMD2Dock.setText(_translate("MainWindow", "PyRMD2Dock"))
        self.pushButton_Benchmark.setText(_translate("MainWindow", "Benchmark"))
        self.pushButton_Screening.setText(_translate("MainWindow", "Screening"))
        self.pushButton_Back.setText(_translate("MainWindow", "< Back"))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())