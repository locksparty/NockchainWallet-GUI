#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nockchain Wallet Qt Interface v0.1.1 (config.json support)
Interface graphique pour le wallet Nockchain
"""

import sys
import subprocess
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
import re
import json

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QFileDialog,
    QMessageBox, QTabWidget, QGroupBox, QRadioButton, QCheckBox,
    QTableWidget, QTableWidgetItem, QStatusBar, QComboBox,
    QSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPalette, QColor

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config global dynamic from JSON
CONFIG_FILE = Path(__file__).parent / "config.json"

def load_config():
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config_data = json.load(f)
                merged = {**default_config, **config_data}
                return merged
    except Exception as e:
        logger.error(f"Erreur lecture config.json: {e}")
    return default_config.copy()

# Configuration Functions
# (Continued with the original content...)
