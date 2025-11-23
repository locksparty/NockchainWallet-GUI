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

default_config = {
    'wallet_binary': 'nockchain-wallet',
    'wallet_path': '',
    'wallet_imported': False,
    'client_type': 'public',
    'public_server': 'https://nockchain-api.zorp.io',
    'private_port': '50051'
}

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

def save_config():
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info("Configuration sauvegardée.")
    except Exception as e:
        logger.error(f"Erreur sauvegarde config.json: {e}")

config = load_config()

class WalletOutputParser:
    """Parse les sorties du binaire nockchain-wallet"""
    @staticmethod
    def parse_balance(output: str) -> Optional[Dict[str, Any]]:
        try:
            match = re.search(r'Balance:\s*(\d[\d,]*)\s*nicks?', output, re.IGNORECASE)
            if match:
                balance_str = match.group(1).replace(',', '')
                balance = int(balance_str)
                return {
                    'balance': balance,
                    'formatted': f"{balance:,} nicks"
                }
            return None
        except Exception as e:
            logger.error(f"Erreur parse balance: {e}")
            return None
    @staticmethod
    def parse_wallet_version(output: str) -> Optional[str]:
        try:
            match = re.search(r'Wallet Version:\s*(.+)', output)
            if match:
                return match.group(1).strip()
            return None
        except Exception as e:
            logger.error(f"Erreur parse version: {e}")
            return None
    @staticmethod
    def parse_height(output: str) -> Optional[int]:
        try:
            match = re.search(r'at height\s*([\d.,]+)', output, re.IGNORECASE)
            if match:
                height_str = match.group(1).replace(',', '').replace('.', '')
                return int(height_str)
            return None
        except Exception as e:
            logger.error(f"Erreur parse height: {e}")
            return None
    @staticmethod
    def parse_number_of_notes(output: str) -> Optional[int]:
        try:
            match = re.search(r'Number of Notes:\s*(\d+)', output, re.IGNORECASE)
            if match:
                return int(match.group(1))
            return None
        except Exception as e:
            logger.error(f"Erreur parse notes count: {e}")
            return None
    @staticmethod
    def parse_block_hash(output: str) -> Optional[str]:
        try:
            match = re.search(r'from block\s+([A-Za-z0-9]+)', output)
            if match:
                return match.group(1)
            return None
        except Exception as e:
            logger.error(f"Erreur parse block hash: {e}")
            return None
    @staticmethod
    def parse_notes(output: str) -> list:
        notes = []
        try:
            lines = output.split('\n')
            for line in lines:
                if re.search(r'[0-9a-zA-Z]{40,}', line):
                    notes.append(line.strip())
            return notes
        except Exception as e:
            logger.error(f"Erreur parse notes: {e}")
            return []
    @staticmethod
    def extract_success_message(output: str) -> Optional[str]:
        try:
            if "Command executed successfully" in output:
                return "✓ Commande exécutée avec succès"
            if "successfully" in output.lower():
                return "✓ Opération réussie"
            return None
        except:
            return None
    @staticmethod
    def extract_error(stderr: str) -> str:
        try:
            lines = stderr.split('\n')
            error_lines = []
            skip_patterns = [
                '[0m', '[32m', '[33m', 
                'trace', 'debug',
                'kernel::boot',
                'NockApp boot',
                'save interval'
            ]
            for line in lines:
                line = line.strip()
                if line and not any(pattern in line.lower() for pattern in skip_patterns):
                    if not line.startswith('--'):
                        error_lines.append(line)
            return '\n'.join(error_lines) if error_lines else stderr
        except:
            return stderr
    @staticmethod
    def clean_output(output: str) -> str:
        try:
            lines = output.split('\n')
            clean_lines = []
            skip_patterns = [
                'kernel::boot',
                'NockApp boot cli',
                'build-hash',
                'nockapp: Nockapp save interval',
                'Command requires syncing',
                'Connected to public',
                'Received balance update'
            ]
            for line in lines:
                if line.strip() and not any(pattern in line for pattern in skip_patterns):
                    cleaned = re.sub(r'^I \(\d+:\d+:\d+\)\s*', '', line)
                    cleaned = re.sub(r'^\[.*?\]\s*', '', cleaned)
                    if cleaned.strip():
                        clean_lines.append(cleaned.strip())
            return '\n'.join(clean_lines)
        except:
            return output

class LogArea(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(200)
        font = QFont("Courier", 10)
        self.setFont(font)
    def append_log(self, message: str, log_type: str = "info"):
        colors = {
            "info": "#FFFFFF",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "command": "#2196F3"
        }
        color = colors.get(log_type, "#FFFFFF")
        self.append(f'<span style="color: {color};">{message}</span>')

class NockchainWalletGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.parser = WalletOutputParser()
        self.init_ui()
        self._check_binary()

    def init_ui(self):
        self.setWindowTitle("Nockchain Wallet Qt Interface v0.1.1")
        self.setGeometry(100, 100, 1000, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        title = QLabel("🔗 Nockchain Wallet v0.1.1")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        main_layout.addWidget(title)
        wallet_group = self._create_wallet_section()
        main_layout.addWidget(wallet_group)
        tabs = QTabWidget()
        tabs.addTab(self._create_balance_tab(), "💰 Balance")
        tabs.addTab(self._create_notes_tab(), "📝 Notes")
        tabs.addTab(self._create_gas_tab(), "⛽ Gas")
        tabs.addTab(self._create_params_tab(), "⚙️ Paramètres")
        main_layout.addWidget(tabs)
        log_label = QLabel("📋 Logs")
        log_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        main_layout.addWidget(log_label)
        self.log_area = LogArea()
        main_layout.addWidget(self.log_area)
        self.statusBar().showMessage("Prêt")
        self.log_area.append_log("Interface Nockchain Wallet v0.1.1 initialisée", "success")

    def _create_wallet_section(self) -> QGroupBox:
        group = QGroupBox("💼 Wallet")
        layout = QVBoxLayout()
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("Chemin:"))
        self.wallet_path_label = QLabel("Aucun wallet chargé")
        self.wallet_path_label.setStyleSheet("color: #FF9800;")
        path_layout.addWidget(self.wallet_path_label)
        path_layout.addStretch()
        layout.addLayout(path_layout)
        buttons_layout = QHBoxLayout()
        btn_import = QPushButton("📥 Importer")
        btn_import.clicked.connect(self._import_wallet)
        buttons_layout.addWidget(btn_import)
        btn_export = QPushButton("📤 Exporter")
        btn_export.clicked.connect(self._export_wallet)
        buttons_layout.addWidget(btn_export)
        layout.addLayout(buttons_layout)
        group.setLayout(layout)
        return group

    def _create_balance_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        balance_group = QGroupBox("Solde actuel")
        balance_layout = QVBoxLayout()
        self.balance_label = QLabel("-- nicks")
        self.balance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.balance_label.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        self.balance_label.setStyleSheet("color: #4CAF50;")
        balance_layout.addWidget(self.balance_label)
        btn_refresh = QPushButton("🔄 Rafraîchir")
        btn_refresh.clicked.connect(self._refresh_balance)
        balance_layout.addWidget(btn_refresh)
        balance_group.setLayout(balance_layout)
        layout.addWidget(balance_group)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_notes_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        options_layout = QHBoxLayout()
        self.watch_only_notes_cb = QCheckBox("Inclure notes watch-only")
        options_layout.addWidget(self.watch_only_notes_cb)
        btn_load_notes = QPushButton("🔄 Charger")
        btn_load_notes.clicked.connect(self._load_notes)
        options_layout.addWidget(btn_load_notes)
        options_layout.addStretch()
        layout.addLayout(options_layout)
        self.notes_table = QTableWidget()
        self.notes_table.setColumnCount(1)
        self.notes_table.setHorizontalHeaderLabels(["Note"])
        self.notes_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.notes_table)
        widget.setLayout(layout)
        return widget

    def _create_gas_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        gas_group = QGroupBox("⛽ Gestion du Gas")
        gas_layout = QVBoxLayout()
        gas_layout.addWidget(QLabel("Fonctionnalités Gas à venir..."))
        gas_group.setLayout(gas_layout)
        layout.addWidget(gas_group)
        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_params_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        binary_group = QGroupBox("Binaire nockchain-wallet")
        binary_layout = QHBoxLayout()
        binary_layout.addWidget(QLabel("Chemin:"))
        self.binary_path_input = QLineEdit(config['wallet_binary'])
        binary_layout.addWidget(self.binary_path_input)
        btn_browse = QPushButton("📂 Parcourir")
        btn_browse.clicked.connect(self._browse_binary)
        binary_layout.addWidget(btn_browse)
        binary_group.setLayout(binary_layout)
        layout.addWidget(binary_group)

        client_group = QGroupBox("Type de client")
        client_layout = QVBoxLayout()
        self.public_client_rb = QRadioButton("Client Public")
        self.public_client_rb.setChecked(config.get('client_type', 'public') == 'public')
        self.public_client_rb.toggled.connect(self._on_client_type_changed)
        client_layout.addWidget(self.public_client_rb)

        public_server_layout = QHBoxLayout()
        public_server_layout.addWidget(QLabel("Serveur:"))
        self.public_server_input = QLineEdit(config['public_server'])
        public_server_layout.addWidget(self.public_server_input)
        client_layout.addLayout(public_server_layout)

        self.private_client_rb = QRadioButton("Client Privé")
        self.private_client_rb.setChecked(config.get('client_type', 'public') == 'private')
        client_layout.addWidget(self.private_client_rb)

        private_port_layout = QHBoxLayout()
        private_port_layout.addWidget(QLabel("Port:"))
        self.private_port_input = QLineEdit(config['private_port'])
        self.private_port_input.setEnabled(config.get('client_type', 'public') == 'private')
        private_port_layout.addWidget(self.private_port_input)
        client_layout.addLayout(private_port_layout)

        client_group.setLayout(client_layout)
        layout.addWidget(client_group)

        btn_save = QPushButton("💾 Sauvegarder les paramètres")
        btn_save.clicked.connect(self._save_params)
        layout.addWidget(btn_save)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _build_base_command(self) -> list:
        cmd = [config['wallet_binary']]
        if config['client_type'] == 'public':
            cmd.extend(['--client', 'public'])
            if config['public_server'] and config['public_server'] != 'https://nockchain-api.zorp.io':
                cmd.extend(['--public-grpc-server-addr', config['public_server']])
        else:
            cmd.extend(['--client', 'private'])
            if config['private_port'] and config['private_port'] != '50051':
                cmd.extend(['--private-grpc-server-port', config['private_port']])
        return cmd

    def _check_binary(self):
        try:
            result = subprocess.run(
                [config['wallet_binary'], '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.log_area.append_log(f"✓ Binaire trouvé: {config['wallet_binary']}", "success")
            else:
                self.log_area.append_log(f"⚠ Binaire non fonctionnel", "warning")
        except FileNotFoundError:
            self.log_area.append_log(f"✗ Binaire non trouvé: {config['wallet_binary']}", "error")
            QMessageBox.warning(
                self,
                "Binaire manquant",
                f"Le binaire '{config['wallet_binary']}' est introuvable.\n"
                "Veuillez le configurer dans l'onglet Paramètres."
            )
        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")

    def _import_wallet(self):
        source_file, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner le fichier à importer",
            str(Path.home() / "Desktop"),
            "Wallet Files (*.export *.jam *.dat);;All Files (*)"
        )
        if not source_file:
            return
        try:
            self.log_area.append_log(f"📥 Import depuis: {Path(source_file).name}", "info")
            cmd = self._build_base_command()
            cmd.append('import-keys')
            cmd.extend(['--file', source_file])
            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                success_msg = self.parser.extract_success_message(result.stdout)
                if success_msg:
                    self.log_area.append_log(success_msg, "success")
                else:
                    self.log_area.append_log("✓ Import réussi", "success")
                default_wallet = Path.home() / ".nockchain" / "wallet.dat"
                time.sleep(0.5)
                if default_wallet.exists():
                    config['wallet_path'] = str(default_wallet)
                    config['wallet_imported'] = True
                    save_config()
                    self.wallet_path_label.setText(str(default_wallet))
                    self.wallet_path_label.setStyleSheet("color: #4CAF50;")
                    self.statusBar().showMessage(f"Wallet: {default_wallet.name}")
                    self.log_area.append_log(f"✓ Wallet trouvé: {default_wallet}", "success")
                    self._refresh_balance()
                    self._load_notes()
                else:
                    alt_wallet = Path.home() / "wallet.wallet"
                    if alt_wallet.exists():
                        config['wallet_path'] = str(alt_wallet)
                        config['wallet_imported'] = True
                        save_config()
                        self.wallet_path_label.setText(str(alt_wallet))
                        self.wallet_path_label.setStyleSheet("color: #4CAF50;")
                        self.statusBar().showMessage(f"Wallet: {alt_wallet.name}")
                        self.log_area.append_log(f"✓ Wallet trouvé: {alt_wallet}", "success")
                        self._refresh_balance()
                        self._load_notes()
                    else:
                        config['wallet_imported'] = True
                        save_config()
                        self.wallet_path_label.setText("Wallet par défaut")
                        self.wallet_path_label.setStyleSheet("color: #4CAF50;")
                        self.log_area.append_log("✓ Utilisation du wallet par défaut", "success")
                        self._refresh_balance()
                        self._load_notes()
                QMessageBox.information(self, "Succès", f"Import réussi depuis {Path(source_file).name}")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")
                QMessageBox.critical(self, "Erreur", f"Échec de l'import:\n{error}")
        except subprocess.TimeoutExpired:
            self.log_area.append_log("✗ Timeout lors de l'import", "error")
        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur import wallet: {e}")

    def _export_wallet(self):
        if not config['wallet_imported']:
            QMessageBox.warning(self, "Attention", "Veuillez importer un wallet d'abord")
            return
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer l'export",
            str(Path.home() / "Desktop" / "wallet_export.export"),
            "Export Files (*.export);;All Files (*)"
        )
        if not output_file:
            return
        try:
            cmd = self._build_base_command()
            cmd.append('export-keys')
            cmd.extend(['--output', output_file])
            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                self.log_area.append_log(f"✓ Export réussi: {Path(output_file).name}", "success")
                QMessageBox.information(self, "Succès", f"Wallet exporté vers:\n{output_file}")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")
                QMessageBox.critical(self, "Erreur", f"Échec de l'export:\n{error}")
        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur export wallet: {e}")

    def _refresh_balance(self):
        if not config['wallet_imported']:
            self.log_area.append_log("⚠ Veuillez importer un wallet d'abord", "warning")
            return
        try:
            cmd = self._build_base_command()
            cmd.append('show-balance')
            self.log_area.append_log(f"$ {' '.join(cmd)}", "command")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                output = result.stdout
                balance_info = self.parser.parse_balance(output)
                wallet_version = self.parser.parse_wallet_version(output)
                height = self.parser.parse_height(output)
                num_notes = self.parser.parse_number_of_notes(output)
                block_hash = self.parser.parse_block_hash(output)
                if balance_info:
                    self.balance_label.setText(balance_info['formatted'])
                    self.log_area.append_log(f"💰 Balance: {balance_info['formatted']}", "success")
                    if num_notes is not None:
                        self.log_area.append_log(f"📝 Nombre de notes: {num_notes}", "info")
                    if wallet_version:
                        self.log_area.append_log(f"📦 Version wallet: {wallet_version}", "info")
                    if height:
                        self.log_area.append_log(f"📊 Hauteur: {height:,}", "info")
                    if block_hash:
                        short_hash = f"{block_hash[:8]}...{block_hash[-8:]}"
                        self.log_area.append_log(f"🔗 Bloc: {short_hash}", "info")
                    success_msg = self.parser.extract_success_message(output)
                    if success_msg:
                        self.log_area.append_log(success_msg, "success")
                else:
                    self.log_area.append_log("⚠ Impossible de parser le solde", "warning")
                    clean = self.parser.clean_output(output)
                    self.log_area.append_log(clean, "info")
            else:
                error = self.parser.extract_error(result.stderr)
                self.log_area.append_log(f"✗ Erreur: {error}", "error")
        except subprocess.TimeoutExpired:
            self.log_area.append_log("✗ Timeout lors de la récupération du solde", "error")
        except Exception as e:
            self.log_area.append_log(f"✗ Erreur: {str(e)}", "error")
            logger.error(f"Erreur refresh balance: {e}")

    def _create_notes_tab(self) -> QWidget:
        """Crée l'onglet Notes"""
       widget = QWidget()
    layout = QVBoxLayout()
    
    options_layout = QHBoxLayout()
    self.watch_only_notes_cb = QCheckBox("Inclure notes watch-only")
    options_layout.addWidget(self.watch_only_notes_cb)
    
    btn_load_notes = QPushButton("🔄 Charger")
    btn_load_notes.clicked.connect(self._load_notes)
    options_layout.addWidget(btn_load_notes)
    options_layout.addStretch()
    layout.addLayout(options_layout)
    
    self.notes_table = QTableWidget()
    self.notes_table.setColumnCount(4)
    self.notes_table.setHorizontalHeaderLabels(["☑", "Note ID", "Montant", "Conf."])
    
        # Tailles de colonnes
        self.notes_table.setColumnWidth(0, 40)   # Checkbox
        self.notes_table.setColumnWidth(2, 150)  # Montant
        self.notes_table.setColumnWidth(3, 80)   # Confirmations
    
        header = self.notes_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Note ID stretch
    
        layout.addWidget(self.notes_table)
    
        widget.setLayout(layout)
    return widget

    def _on_client_type_changed(self):
        if self.public_client_rb.isChecked():
            self.public_server_input.setEnabled(True)
            self.private_port_input.setEnabled(False)
        else:
            self.public_server_input.setEnabled(False)
            self.private_port_input.setEnabled(True)

    def _browse_binary(self):
        binary_file, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner le binaire nockchain-wallet",
            str(Path.home()),
            "All Files (*)"
        )
        if binary_file:
            self.binary_path_input.setText(binary_file)

    def _save_params(self):
        config['wallet_binary'] = self.binary_path_input.text()
        config['client_type'] = 'public' if self.public_client_rb.isChecked() else 'private'
        config['public_server'] = self.public_server_input.text()
        config['private_port'] = self.private_port_input.text()
        save_config()
        self.log_area.append_log("✓ Paramètres sauvegardés", "success")
        QMessageBox.information(self, "Succès", "Paramètres sauvegardés")
        self._check_binary()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(palette)
    window = NockchainWalletGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
